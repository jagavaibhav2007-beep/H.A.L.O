"""Production imports must have an explicitly declared distribution owner."""
import ast
import importlib.metadata
from pathlib import Path
import re
import sys
import tomllib


def normalized(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def main():
    root = Path(__file__).resolve().parents[2]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    requirements = project["dependencies"] + [
        requirement for group in project["optional-dependencies"].values()
        for requirement in group
    ]
    declared = {normalized(re.match(r"[\w.-]+", item)[0]) for item in requirements}
    modules = set()
    for package in ("brain/brain", "voice/voice", "halo"):
        for path in (root / package).rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    modules.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    modules.add(node.module.split(".")[0])
                elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                      and node.func.id == "require" and node.args
                      and isinstance(node.args[0], ast.Constant)
                      and isinstance(node.args[0].value, str)):
                    modules.add(node.args[0].value.split(".")[0])
    owners = importlib.metadata.packages_distributions()
    for module in sorted(modules - sys.stdlib_module_names - {"brain", "voice", "halo"}):
        assert declared.intersection(normalized(name) for name in owners.get(module, [])), (
            f"Undeclared or missing import {module}; run this check with the full profile"
        )
    print("[dependencies] production static/lazy imports have declared distribution owners: OK")


if __name__ == "__main__":
    main()
