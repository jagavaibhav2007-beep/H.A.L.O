"""Frozen boot entry. Dispatch multiprocessing before importing worker code."""
import multiprocessing
import sys

if __name__ == "__main__":
    multiprocessing.freeze_support()
    for stream in (sys.stdout, sys.stderr):
        if stream is not None:
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    from halo.cli import main
    main()
