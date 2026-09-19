"""Reject known disallowed licenses and report unknown metadata as unknown."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

DISALLOWED = ("AGPL-", "GPL-3.0-only", "SSPL-")
LOCAL_PATH = re.compile(
    r"(?:file:/+|(?<![A-Za-z0-9+.-])[A-Za-z]:[\\/]|/(?:home|Users)/)",
    re.IGNORECASE,
)
URL_CREDENTIAL = re.compile(r"[a-z][a-z0-9+.-]*://[^/@\s]+:[^/@\s]+@", re.IGNORECASE)


def license_text(component: dict) -> str:
    values = []
    for item in component.get("licenses", []):
        if "expression" in item:
            values.append(item["expression"])
        elif "license" in item:
            values.append(item["license"].get("id") or item["license"].get("name") or "")
    return " OR ".join(filter(None, values))


def scan_boms(directory: Path) -> tuple[list[str], list[str], list[str], list[str]]:
    unknown, disallowed, local_paths, credentials = [], [], [], []
    for path in sorted(directory.glob("*.cdx.json")):
        raw = path.read_text(encoding="utf-8-sig")
        if LOCAL_PATH.search(raw):
            local_paths.append(path.name)
        if URL_CREDENTIAL.search(raw):
            credentials.append(path.name)
        bom = json.loads(raw)
        for component in bom.get("components", []):
            identity = f"{component.get('name', '<unnamed>')}@{component.get('version', '<unknown>')}"
            declared = license_text(component)
            if not declared:
                unknown.append(f"{path.name}: {identity}")
            if any(token in declared for token in DISALLOWED):
                disallowed.append(f"{path.name}: {identity}: {declared}")
    return unknown, disallowed, local_paths, credentials


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    unknown, disallowed, local_paths, credentials = scan_boms(args.directory)
    if unknown:
        print("License metadata unknown (requires review; never treated as permissive):")
        print("\n".join(f"- {item}" for item in unknown))
    if disallowed:
        raise SystemExit("Disallowed dependency license declarations:\n" + "\n".join(disallowed))
    if local_paths:
        raise SystemExit("SBOM contains a local developer path: " + ", ".join(local_paths))
    if credentials:
        raise SystemExit("SBOM contains URL credentials: " + ", ".join(credentials))
    print(f"[license-policy] {len(unknown)} unknown declarations reported; no disallowed declaration found")


if __name__ == "__main__":
    main()
