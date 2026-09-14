"""Pinned model integrity and offline policy without downloading weights."""
import hashlib
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import embedding
from huggingface_hub.errors import LocalEntryNotFoundError


def main():
    calls = []
    def missing(**kwargs):
        calls.append(kwargs)
        raise LocalEntryNotFoundError("not cached")
    with patch.dict(os.environ, {"HALO_SEMANTIC": "offline"}), patch("huggingface_hub.snapshot_download", missing):
        try:
            embedding.model_path()
        except ValueError as exc:
            assert "offline" in str(exc)
        else:
            raise AssertionError("uncached offline model unexpectedly loaded")
    assert calls and all(call["local_files_only"] for call in calls)
    assert all(call["revision"] == embedding.MODEL_REVISION for call in calls)
    assert len(embedding.MODEL_REVISION) == 40
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        for name in embedding.MODEL_FILES:
            (root / name).write_bytes(b"fixture")
        with patch.object(embedding, "MODEL_SHA256", hashlib.sha256(b"fixture").hexdigest()):
            assert embedding.verify_model(root) == root
            # A verified cached snapshot works offline; it must never ask the
            # Hub for network access even if downloads are normally allowed.
            def cached(**kwargs):
                assert kwargs["local_files_only"] is True
                return str(root)
            with patch.dict(os.environ, {"HALO_SEMANTIC_OFFLINE": "1"}), patch("huggingface_hub.snapshot_download", cached):
                assert embedding.model_path() == root
            (root / "tokenizer.json").unlink()
            try:
                embedding.verify_model(root)
            except ValueError as exc:
                assert "incomplete" in str(exc)
            else:
                raise AssertionError("snapshot without tokenizer accepted")
            (root / "tokenizer.json").write_bytes(b"fixture")
            (root / embedding.MODEL_FILE).write_bytes(b"tampered")
            try:
                embedding.verify_model(root)
            except ValueError as exc:
                assert "checksum" in str(exc)
            else:
                raise AssertionError("tampered model accepted")
            with patch("huggingface_hub.snapshot_download", cached):
                try:
                    embedding.model_path()
                except ValueError as exc:
                    assert "checksum" in str(exc)
                else:
                    raise AssertionError("corrupt cache silently fell back to another model")
    print("[embedding] immutable revision, cached-only offline calls and tamper rejection: OK")


if __name__ == "__main__":
    main()
