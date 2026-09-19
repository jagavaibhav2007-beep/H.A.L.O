"""Generate the CycloneDX inventory for model assets and built executables."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "brain"))

from brain import embedding


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--backend", type=Path)
    args = parser.parse_args()
    components = [{
        "type": "machine-learning-model",
        "bom-ref": f"pkg:huggingface/{embedding.MODEL_REPO}@{embedding.MODEL_REVISION}",
        "name": embedding.MODEL_NAME,
        "version": embedding.MODEL_REVISION,
        "hashes": [{"alg": "SHA-256", "content": embedding.MODEL_SHA256}],
        "externalReferences": [{
            "type": "distribution",
            "url": f"https://huggingface.co/{embedding.MODEL_REPO}/tree/{embedding.MODEL_REVISION}",
        }],
        "properties": [
            {"name": "halo:model-file", "value": embedding.MODEL_FILE},
            {"name": "halo:upstream-license-declarations", "value": "repository: Apache-2.0; FastEmbed registry: MIT; resolve before redistribution"},
            {"name": "halo:bundled", "value": "false"},
        ],
    }]
    if args.backend:
        backend = args.backend.resolve(strict=True)
        components.append({
            "type": "application",
            "bom-ref": "halo-backend.exe",
            "name": backend.name,
            "version": "0.1.0",
            "hashes": [{"alg": "SHA-256", "content": _sha256(backend)}],
        })
    bom = {
        "bomFormat": "CycloneDX", "specVersion": "1.6", "version": 1,
        "metadata": {"component": {"type": "application", "name": "H.A.L.O. release assets", "version": "0.1.0"}},
        "components": components,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(bom, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
