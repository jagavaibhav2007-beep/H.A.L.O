"""One installed command, with lazy imports for each process mode."""
from __future__ import annotations

import argparse
import json
import multiprocessing
import sys


def main() -> None:
    multiprocessing.freeze_support()
    mode = sys.argv[1] if len(sys.argv) > 1 else None
    if mode == "--external-command":
        from halo.freezing import run_external
        raise SystemExit(run_external(sys.argv[2:]))
    if mode == "--pdf-worker":
        from brain.extract_worker import worker_main
        sys.argv.pop(1)
        worker_main()
        return
    parser = argparse.ArgumentParser(prog="halo")
    modes = parser.add_subparsers(dest="mode", required=True)
    modes.add_parser("brain", help="start the authenticated Brain").add_argument("--mock", action="store_true")
    modes.add_parser("voice", help="start the reconnecting Voice sidecar")
    modes.add_parser("diagnostics", help="report installed capabilities without model downloads")
    modes.add_parser("memory-reindex", help="rebuild missing local embeddings (may download the pinned model)").add_argument("--all", action="store_true")
    args = parser.parse_args()
    mode = args.mode
    sys.argv.pop(1)
    if mode == "brain":
        from brain.server import main as run
    elif mode == "voice":
        from voice.__main__ import main as run
    elif mode == "diagnostics":
        from brain.capabilities import capabilities
        print(json.dumps(capabilities(verify_imports=True), indent=2))
        return
    elif mode == "memory-reindex":
        from brain import store
        try:
            print(json.dumps({"indexed": store.reindex_beliefs(all_beliefs=args.all)}))
        finally:
            store.close()
        return
    else:
        raise SystemExit(f"unknown Halo mode: {mode}; use halo --help")
    run()
