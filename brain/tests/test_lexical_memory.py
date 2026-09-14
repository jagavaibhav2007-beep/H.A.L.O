"""Offline lexical relevance, transactional migration, and vector profile cycles."""
from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import store


def add(text):
    return store.add_candidate_belief(text, "preference", "user")[0]


def lexical(root):
    with patch.dict(os.environ, {"HALO_SEMANTIC": "off"}), patch.object(store, "_embed", return_value=None):
        conn = store.connect(root / "lexical.db")
        assert store.search_beliefs("empty") == []
        relevant = add("I use pnpm for JavaScript package management")
        cafe = add("Meet at the café in Zürich")
        tokyo = add("工作 东京")
        phrase = add("New York is my project location")
        add("York has a new railway station")
        for n in range(15):
            add(f"unrelated recent event {n}")
        assert store.search_beliefs("pnpm", k=1)[0]["belief_id"] == relevant
        assert store.search_beliefs("cafe Zürich", k=1)[0]["belief_id"] == cafe
        assert store.search_beliefs("东京", k=1)[0]["belief_id"] == tokyo
        assert store.search_beliefs('"New York"', k=1)[0]["belief_id"] == phrase
        assert store.search_beliefs("unfindableword", k=1)
        assert store.retrieval_status()["mode"] == "recency", "semantic-off must not label unmatched recency as lexical relevance"
        for query in ("", "!!", '"', "OR NOT * : ( )", 'pnpm" OR 1=1 --', "pnpm " * 20000):
            assert len(store.search_beliefs(query, k=3)) <= 3
        assert store.search_beliefs("pnpm", k=0) == []
        assert store.search_beliefs("pnpm", k=-1) == []
        store.update_belief(relevant, "I now use uv for Python environments")
        ids = {row[0] for row in conn.execute("SELECT belief_id FROM belief_fts WHERE belief_fts MATCH 'pnpm'")}
        assert relevant not in ids
        assert store.search_beliefs("uv", k=1)[0]["belief_id"] == relevant
        store.set_belief_status(relevant, "archived")
        assert not conn.execute("SELECT 1 FROM belief_fts WHERE belief_id=?", (relevant,)).fetchone()
        store.restore_belief(relevant)
        assert store.search_beliefs("uv", k=1)[0]["belief_id"] == relevant
        new, replaced = store.add_candidate_belief("I prefer rye for Python environments", "preference", "user", supersede_id=relevant)
        assert replaced
        assert not conn.execute("SELECT 1 FROM belief_fts WHERE belief_id=?", (relevant,)).fetchone()
        store.set_belief_status(new, "archived")
        store.purge_belief(new)
        assert not conn.execute("SELECT 1 FROM belief_fts WHERE belief_id=?", (new,)).fetchone()
        store.close()
        store.connect(root / "lexical.db")
        assert store.search_beliefs("cafe", k=1)[0]["belief_id"] == cafe
        assert store.retrieval_status()["mode"] == "lexical"
        store.close()
    print("[memory] lexical relevance, Unicode, phrases, hostile queries and live-set CRUD: OK")


def migration(root):
    path = root / "migration.db"
    # Model the actual v5 belief/map layout without depending on v6 creation.
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE belief (belief_id TEXT PRIMARY KEY, text TEXT NOT NULL, status TEXT,
                             invalid_at TEXT, last_used_at TEXT, salience REAL);
        CREATE TABLE belief_map (rowid INTEGER PRIMARY KEY, belief_id TEXT UNIQUE NOT NULL);
        INSERT INTO belief VALUES ('old', 'legacy lexical fact', 'active', NULL, '2026', .6);
        PRAGMA user_version=5;
    """)
    def fail_trigger(action, arg1, arg2, db, trigger):
        return sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_CREATE_TRIGGER and arg1 == "belief_fts_update" else sqlite3.SQLITE_OK
    conn.set_authorizer(fail_trigger)
    try:
        store._run_migrations(conn)
    except sqlite3.DatabaseError:
        pass
    else:
        raise AssertionError("migration failure injection was not reached")
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 5
    assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name='belief_fts'").fetchone()
    assert conn.execute("SELECT text FROM belief").fetchone()[0] == "legacy lexical fact"
    conn.set_authorizer(None)
    store._run_migrations(conn)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == store.SCHEMA_VERSION
    assert conn.execute("SELECT belief_id FROM belief_fts WHERE belief_fts MATCH 'legacy'").fetchone()[0] == "old"
    conn.close()
    print("[memory] v5 migration rolls back DDL/backfill/version together and retries: OK")


def vector_cycle(root):
    path = root / "vectors.db"
    axis = [0.] * store.EMBED_DIM
    axis[0] = 1.
    with patch.object(store, "_embed", return_value=axis):
        conn = store.connect(path)
        assert store._vec_ok, "full-profile gate must exercise real sqlite-vec"
        keep = add("preserve this embedding")
        changed = add("old text before offline edit")
        removed = add("will be purged offline")
        saved = bytes(conn.execute("SELECT embedding FROM belief_vec JOIN belief_map USING(rowid) WHERE belief_id=?", (keep,)).fetchone()[0])
        store.close()
    with patch.dict(os.environ, {"HALO_SEMANTIC": "off"}), patch.object(store, "_embed", return_value=None):
        conn = store.connect(path)
        assert not store._vec_ok
        store.update_belief(changed, "changed while semantic disabled")
        store.set_belief_status(removed, "archived")
        store.purge_belief(removed)
        store.close()
    with patch.object(store, "_embed", return_value=axis):
        conn = store.connect(path)
        current = bytes(conn.execute("SELECT embedding FROM belief_vec JOIN belief_map USING(rowid) WHERE belief_id=?", (keep,)).fetchone()[0])
        assert current == saved, "profile toggle destroyed an unchanged embedding"
        assert not conn.execute("SELECT 1 FROM belief_map WHERE belief_id IN (?,?)", (changed, removed)).fetchone()
        assert conn.execute("SELECT COUNT(*) FROM belief_vec").fetchone()[0] == 1
        assert store.search_beliefs("preserve", k=1)[0]["belief_id"] == keep
        assert store.reindex_beliefs() == 1
        assert conn.execute("SELECT COUNT(*) FROM belief_vec").fetchone()[0] == 2
        assert store.reindex_beliefs() == 0
        assert bytes(conn.execute("SELECT embedding FROM belief_vec JOIN belief_map USING(rowid) WHERE belief_id=?", (keep,)).fetchone()[0]) == saved
        store.close()
    print("[memory] semantic off/edit/purge/on preserves valid bytes and removes stale/orphan vectors: OK")


def reindex_recovery(root):
    # Catches lost per-row commits, stale text writeback and a one-batch-only
    # rebuild. Only embedding inference is stubbed; SQLite/vec0 stay real.
    conn = store.connect(root / "reindex.db")
    assert store._vec_ok
    axis = [1.] + [0.] * (store.EMBED_DIM - 1)
    with patch.object(store, "_embed", return_value=None):
        ids = [add(f"rebuild preference {n}") for n in range(66)]
    with patch.object(store, "_embed", side_effect=[axis, None]):
        try:
            store.reindex_beliefs()
        except ValueError as exc:
            assert "completed entries are retained" in str(exc)
        else:
            raise AssertionError("unavailable model did not stop rebuild")
    store.close()
    conn = store.connect(root / "reindex.db")
    assert conn.execute("SELECT COUNT(*) FROM belief_vec").fetchone()[0] == 1
    saved = bytes(conn.execute("SELECT embedding FROM belief_vec").fetchone()[0])

    def edit_during_embedding(text):
        if text == "rebuild preference 1":
            with patch.object(store, "_embed", return_value=None):
                store.update_belief(ids[1], "edited while inference ran")
        return axis

    with patch.object(store, "_embed", side_effect=edit_during_embedding):
        assert store.reindex_beliefs() == 64
    assert not conn.execute("SELECT 1 FROM belief_map WHERE belief_id=?", (ids[1],)).fetchone()
    assert store.get_belief(ids[1])["text"] == "edited while inference ran"
    with patch.object(store, "_embed", return_value=axis):
        assert store.reindex_beliefs() == 1
        assert store.reindex_beliefs() == 0
    assert conn.execute("SELECT COUNT(*) FROM belief_vec").fetchone()[0] == 66
    assert bytes(conn.execute("SELECT embedding FROM belief_vec JOIN belief_map USING(rowid) WHERE belief_id=?", (ids[0],)).fetchone()[0]) == saved
    store.close()
    print("[memory] rebuild commits survive restart, spans batches and skips concurrently edited text: OK")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        try:
            lexical(root)
            migration(root)
            vector_cycle(root)
            reindex_recovery(root)
        finally:
            store.close()
