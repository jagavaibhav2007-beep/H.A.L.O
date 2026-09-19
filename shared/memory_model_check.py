"""Opt-in real-model relevance check; no user database or model-cache mutation.

Uses a repository-local ignored cache. Downloads require --allow-download;
without it, absent assets produce UNAVAILABLE (exit 2), not a passing verdict.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "brain"))

CORPUS = (
    "I use uv to manage Python dependencies and virtual environments.",
    "I cycle to the office instead of driving a car.",
    "My preferred programming language is Rust for native desktop software.",
    "I drink decaffeinated coffee in the evening.",
    "My next holiday destination is Tokyo in Japan.",
    "Project meetings happen on Friday afternoons.",
    "The kitchen walls are painted blue.",
    "The backup archive lives on an external hard drive.",
)
LEXICAL = (("uv Python", 0), ("Tokyo Japan", 4), ('"Friday afternoons"', 5))
SEMANTIC = (("How do I commute to work?", 1), ("Which language do I code desktop apps in?", 2), ("Where am I planning to travel?", 4))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-download", action="store_true")
    args = parser.parse_args()
    os.environ["HALO_MODEL_CACHE"] = str(ROOT / ".tmp" / "embedding-model-check")
    os.environ["HF_HUB_OFFLINE"] = "0" if args.allow_download else "1"
    os.environ["HALO_SEMANTIC_OFFLINE"] = "0" if args.allow_download else "1"
    os.environ["HALO_SEMANTIC"] = "off"
    from brain import embedding, store

    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="halo-model-check-") as folder:
        path = Path(folder) / "memory.db"
        try:
            store.connect(path)
            ids = [store.add_candidate_belief(text, "preference", "user")[0] for text in CORPUS]
            for query, expected in LEXICAL:
                rows = store.search_beliefs(query, k=1)
                assert rows[0]["belief_id"] == ids[expected], (query, rows)
                assert store.retrieval_status()["mode"] == "lexical"
            store.close()
            os.environ.pop("HALO_SEMANTIC")
            store.connect(path)
            try:
                indexed = store.reindex_beliefs()
            except ValueError as exc:
                print(json.dumps({"verdict": "UNAVAILABLE", "reason": str(exc), "lexical_queries_passed": len(LEXICAL)}))
                return 2
            assert indexed == len(CORPUS), indexed
            rankings = []
            for query, expected in SEMANTIC:
                rows = store.search_beliefs(query, k=3)
                ranking = [ids.index(row["belief_id"]) for row in rows]
                assert expected in ranking, (query, ranking)
                assert store.retrieval_status()["mode"] == "semantic"
                rankings.append({"query": query, "corpus_indices": ranking, "expected": expected})
            assert store.retrieval_status()["model_ready"]
            print(json.dumps({
                "verdict": "PASS", "revision": embedding.MODEL_REVISION,
                "weights_sha256": embedding.MODEL_SHA256, "dimensions": store.EMBED_DIM,
                "lexical_queries_passed": len(LEXICAL), "semantic_top3": rankings,
                "elapsed_seconds": round(time.monotonic() - started, 2),
            }, indent=2))
            return 0
        finally:
            store.close()


if __name__ == "__main__":
    raise SystemExit(main())
