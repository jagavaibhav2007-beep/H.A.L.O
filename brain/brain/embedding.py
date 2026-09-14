"""Pinned, optional embedding assets. No model import/download during startup."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile

MODEL_NAME = "BAAI/bge-small-en-v1.5"
MODEL_REPO = "qdrant/bge-small-en-v1.5-onnx-q"
MODEL_REVISION = "52398278842ec682c6f32300af41344b1c0b0bb2"
MODEL_SHA256 = "51f1bd0addd6e859e42c2c8021a5e5461385bb676a649f4b269aa445449f2431"
MODEL_FILE = "model_optimized.onnx"
MODEL_FILES = (MODEL_FILE, "config.json", "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json")


def downloads_allowed() -> bool:
    return not (
        os.environ.get("HALO_SEMANTIC", "").lower() in ("off", "offline")
        or os.environ.get("HALO_SEMANTIC_OFFLINE") == "1"
        or os.environ.get("HF_HUB_OFFLINE") == "1"
    )


def cache_dir() -> Path:
    if os.environ.get("HALO_MODEL_CACHE"):
        return Path(os.environ["HALO_MODEL_CACHE"]).expanduser().resolve()
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Halo" / "models"


def verify_model(path: Path) -> Path:
    if any(not (path / name).is_file() for name in MODEL_FILES):
        raise ValueError("pinned embedding snapshot is incomplete; lexical retrieval remains available")
    with (path / MODEL_FILE).open("rb") as handle:
        if hashlib.file_digest(handle, "sha256").hexdigest() != MODEL_SHA256:
            raise ValueError("embedding model checksum mismatch; refusing unverified model bytes")
    return path


def model_path() -> Path:
    from huggingface_hub import snapshot_download
    kwargs = dict(repo_id=MODEL_REPO, revision=MODEL_REVISION, allow_patterns=list(MODEL_FILES))
    # Reuse an exact legacy FastEmbed snapshot without deleting/moving caches.
    for cache in (cache_dir(), Path(tempfile.gettempdir()) / "fastembed_cache"):
        try:
            return verify_model(Path(snapshot_download(**kwargs, cache_dir=str(cache), local_files_only=True)))
        except FileNotFoundError:
            pass
        except Exception as exc:
            # Cache absence is expected; checksum/incomplete-content failures
            # must never be silently accepted or replaced by a moving revision.
            from huggingface_hub.errors import LocalEntryNotFoundError
            if not isinstance(exc, LocalEntryNotFoundError):
                raise
    if not downloads_allowed():
        raise ValueError("pinned embedding model is not cached; offline lexical retrieval is active")
    return verify_model(Path(snapshot_download(**kwargs, cache_dir=str(cache_dir()), local_files_only=False)))


def load_model():
    from fastembed import TextEmbedding
    return TextEmbedding(
        model_name=MODEL_NAME, specific_model_path=str(model_path()), local_files_only=True,
    )
