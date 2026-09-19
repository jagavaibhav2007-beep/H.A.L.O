"""SQLite-owned lexical index and deferred invalidation of optional vectors."""
from __future__ import annotations

import re
import sqlite3
import unicodedata


def migrate(conn: sqlite3.Connection, version: int) -> None:
    # No executescript: it implicitly commits and would separate DDL/backfill
    # from the version marker. FTS5 and trigger creation are transactional.
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS belief_map (rowid INTEGER PRIMARY KEY, belief_id TEXT UNIQUE NOT NULL)")
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS belief_fts USING fts5(belief_id UNINDEXED, text, tokenize='unicode61')")
        conn.execute("CREATE TABLE IF NOT EXISTS belief_vec_stale (rowid INTEGER PRIMARY KEY)")
        conn.execute("DELETE FROM belief_fts")
        conn.execute("""
            INSERT INTO belief_fts(rowid, belief_id, text)
            SELECT rowid, belief_id, text FROM belief WHERE status='active' AND invalid_at IS NULL
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS belief_fts_insert AFTER INSERT ON belief
            WHEN new.status='active' AND new.invalid_at IS NULL BEGIN
                INSERT INTO belief_fts(rowid, belief_id, text) VALUES (new.rowid, new.belief_id, new.text);
            END
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS belief_fts_update AFTER UPDATE OF text, status, invalid_at ON belief BEGIN
                DELETE FROM belief_fts WHERE rowid=old.rowid;
                INSERT INTO belief_fts(rowid, belief_id, text)
                    SELECT new.rowid, new.belief_id, new.text
                    WHERE new.status='active' AND new.invalid_at IS NULL;
                INSERT OR IGNORE INTO belief_vec_stale(rowid)
                    SELECT rowid FROM belief_map WHERE belief_id=old.belief_id
                    AND (old.text IS NOT new.text OR new.status!='active' OR new.invalid_at IS NOT NULL);
            END
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS belief_fts_delete AFTER DELETE ON belief BEGIN
                DELETE FROM belief_fts WHERE rowid=old.rowid;
                INSERT OR IGNORE INTO belief_vec_stale(rowid)
                    SELECT rowid FROM belief_map WHERE belief_id=old.belief_id;
            END
        """)
        conn.execute(f"PRAGMA user_version={version}")
        conn.commit()
    except BaseException:
        conn.rollback()
        raise


def reconcile_vectors(conn: sqlite3.Connection) -> None:
    """Call only with vec0 loaded. Never rebuild/delete unchanged embeddings."""
    conn.execute("""
        INSERT OR IGNORE INTO belief_vec_stale(rowid)
        SELECT m.rowid FROM belief_map m LEFT JOIN belief b USING(belief_id)
        WHERE b.belief_id IS NULL OR b.status!='active' OR b.invalid_at IS NOT NULL
    """)
    conn.execute("""
        DELETE FROM belief_vec WHERE rowid IN (SELECT rowid FROM belief_vec_stale)
        OR rowid NOT IN (SELECT rowid FROM belief_map)
    """)
    conn.execute("DELETE FROM belief_map WHERE rowid IN (SELECT rowid FROM belief_vec_stale)")
    conn.execute("DELETE FROM belief_vec_stale")


def query(text: str) -> str:
    """Bounded literal terms/quoted phrases; never expose raw FTS operators."""
    text = unicodedata.normalize("NFC", text)
    parts = []
    for phrase, word in re.findall(r'"([^"]+)"|([^\W_]+)', text[:4096], flags=re.UNICODE):
        words = re.findall(r"[^\W_]+", phrase or word, flags=re.UNICODE)[:32]
        if words:
            literal = '"' + " ".join(words).replace('"', '""') + '"'
            if literal not in parts:
                parts.append(literal)
        if len(parts) >= 64:
            break
    return " OR ".join(parts)
