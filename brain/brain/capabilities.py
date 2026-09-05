"""Optional dependency boundaries; probing never loads an embedding model."""
from __future__ import annotations

from importlib import import_module
from importlib.util import find_spec

DOCUMENT_MODULES = {
    "pdf": ("pypdfium2", "pypdf"),
    "docx": ("mammoth", "markdownify"),
    "xlsx": ("openpyxl",),
    "html": ("markdownify",),
}


def require(module: str, extra: str = "documents"):
    try:
        return import_module(module)
    except (ImportError, OSError) as exc:
        raise ValueError(
            f"{module} is unavailable; install the '{extra}' capability with "
            f'python -m pip install ".[{extra}]" from the repository, '
            "or reinstall the full desktop application."
        ) from exc


def require_document_modules(kind: str) -> None:
    """Cheap parent-side check; native parsers still load inside the worker."""
    for module in DOCUMENT_MODULES[kind]:
        try:
            if find_spec(module) is None:
                raise ImportError(module)
        except (ImportError, ValueError) as exc:
            raise ValueError(
                f"{kind} requires documents support; install it with "
                'python -m pip install ".[documents]" from the repository.'
            ) from exc


def _available(modules: tuple[str, ...]) -> bool:
    try:
        for module in modules:
            import_module(module)
        return True
    except (ImportError, OSError):
        return False


def capabilities() -> dict:
    return {
        "documents": {kind: _available(modules) for kind, modules in DOCUMENT_MODULES.items()},
        "semantic_dependencies": _available(("sqlite_vec", "fastembed")),
        "semantic_model": "not probed (dependency availability is not model readiness)",
    }


def require_full() -> None:
    for modules in DOCUMENT_MODULES.values():
        for module in modules:
            require(module)
    for module in ("sqlite_vec", "fastembed"):
        require(module, "semantic")
