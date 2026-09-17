"""Behavior checks for the dependency-governance helpers."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from cargo_sbom import component_ref
from check_sbom_policy import scan_boms


def main() -> None:
    ref = component_ref({"name": "ui", "version": "0.1.0"})
    assert ref == "pkg:cargo/ui@0.1.0"
    assert "file:" not in ref and "Users" not in ref

    with tempfile.TemporaryDirectory(prefix="halo-sbom-check-") as raw:
        directory = Path(raw)
        bom = {
            "components": [
                {"name": "unknown", "version": "1"},
                {"name": "blocked", "version": "2", "licenses": [{"expression": "AGPL-3.0-only"}]},
            ],
            "metadata": {
                "checkout": "file:///C:/Users/developer/project",
                "source": "https://user:password@example.invalid/repo",
            },
        }
        (directory / "fixture.cdx.json").write_text(json.dumps(bom), encoding="utf-8")
        unknown, disallowed, local_paths, credentials = scan_boms(directory)
        assert unknown == ["fixture.cdx.json: unknown@1"]
        assert disallowed == ["fixture.cdx.json: blocked@2: AGPL-3.0-only"]
        assert local_paths == ["fixture.cdx.json"]
        assert credentials == ["fixture.cdx.json"]
    print("[supply-chain] stable refs and policy guards passed")


if __name__ == "__main__":
    main()
