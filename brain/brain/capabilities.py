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


def _available(modules: tuple[str, ...], verify_imports: bool) -> bool:
    try:
        for module in modules:
            if verify_imports:
                import_module(module)
            elif find_spec(module) is None:
                return False
        return True
    except (ImportError, OSError, ValueError):
        return False


def capabilities(*, verify_imports: bool = False) -> dict:
    return {
        "documents": {kind: _available(modules, verify_imports) for kind, modules in DOCUMENT_MODULES.items()},
        "semantic_dependencies": _available(("sqlite_vec", "fastembed"), verify_imports),
        "semantic_model": "not probed (dependency availability is not model readiness)",
    }


def runtime_frame() -> dict:
    from brain import store
    installed = capabilities()
    retrieval = store.retrieval_status()
    return {
        "voice_input": False, "task_controls": True,
        "skill_controls": False, "demo_scenarios": False,
        **{f"docs_{kind}": value for kind, value in installed["documents"].items()},
        "memory_retrieval": retrieval["mode"],
        "semantic_model_ready": retrieval["model_ready"],
        "semantic_downloads_allowed": retrieval["model_downloads_allowed"],
    }


def require_full() -> None:
    for modules in DOCUMENT_MODULES.values():
        for module in modules:
            require(module)
    for module in ("sqlite_vec", "fastembed"):
        require(module, "semantic")
