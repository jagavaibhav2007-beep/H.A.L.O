"""Launcher preflight, shared by PowerShell and native source supervision."""
import importlib
import sys

CORE_MODULES = (
    "websockets", "httpx", "keyring", "langgraph", "langgraph.checkpoint.sqlite", "aiosqlite",
)


def main():
    if sys.version_info < (3, 11):
        print("Python 3.11 or later is required", file=sys.stderr)
        return 1
    modules = sys.argv[1:] or CORE_MODULES
    failed = []
    for module in modules:
        try:
            importlib.import_module(module)
        except Exception as exc:
            failed.append(f"{module}: {type(exc).__name__}: {exc}")
    if failed:
        print("Required Python packages could not load: " + "; ".join(failed), file=sys.stderr)
        print("Install the repository's locked dependencies into .venv (see DEVELOPMENT.md).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
