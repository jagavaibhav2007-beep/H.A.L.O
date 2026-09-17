"""Generate a reproducible CycloneDX JSON inventory from locked Cargo metadata."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess


def component_ref(package: dict) -> str:
    """Return a stable reference that never embeds a checkout path."""
    return f"pkg:cargo/{package['name']}@{package['version']}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = subprocess.run(
        ["cargo", "metadata", "--locked", "--format-version", "1", "--manifest-path", str(args.manifest)],
        check=True, capture_output=True, text=True, encoding="utf-8",
    )
    metadata = json.loads(result.stdout)
    packages = {package["id"]: package for package in metadata["packages"]}
    references = {
        package_id: component_ref(package)
        for package_id, package in packages.items()
    }
    nodes = metadata["resolve"]["nodes"] if metadata.get("resolve") else []
    components = []
    for package_id in sorted(packages):
        package = packages[package_id]
        component = {
            "type": "library",
            "bom-ref": references[package_id],
            "name": package["name"],
            "version": package["version"],
        }
        if package.get("license"):
            component["licenses"] = [{"expression": package["license"]}]
        if package.get("repository"):
            component["externalReferences"] = [{"type": "vcs", "url": package["repository"]}]
        components.append(component)
    bom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "version": 1,
        "metadata": {"component": {"type": "application", "name": "H.A.L.O. desktop", "version": "0.1.0"}},
        "components": components,
        "dependencies": [
            {
                "ref": references[node["id"]],
                "dependsOn": sorted(references[item] for item in node.get("dependencies", [])),
            }
            for node in sorted(nodes, key=lambda item: item["id"])
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(bom, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
