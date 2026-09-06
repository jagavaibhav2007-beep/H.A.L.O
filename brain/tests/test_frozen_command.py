"""Frozen commands keep argv intact and sanitize only in a child process."""
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

from halo.freezing import external_argv, external_environment


def main():
    argv = ["C:/tool with spaces/tool.exe", "a b", "c;d"]
    env = {"PATH": "kept", "_PYI_APPLICATION_HOME_DIR": "untrusted", "VALUE": "keep"}
    assert external_argv(argv, env) == argv
    with patch.object(sys, "frozen", True, create=True), patch.dict(os.environ, {
        "_PYI_APPLICATION_HOME_DIR": "trusted-runtime",
    }):
        wrapped = external_argv(argv, env)
        assert wrapped == [sys.executable, "--external-command", *argv]
        assert env["_PYI_APPLICATION_HOME_DIR"] == "trusted-runtime"
        assert env["VALUE"] == "keep"
    with patch.object(sys, "_MEIPASS", str(Path("bundled").resolve()), create=True):
        cleaned = external_environment({
            "PATH": os.pathsep.join([str(Path("bundled").resolve()), str(Path("bundled/sub").resolve()), "keep"]),
            "_PYI_APPLICATION_HOME_DIR": "private", "VALUE": "keep",
        })
        assert cleaned["PATH"] == "keep"
        assert "_PYI_APPLICATION_HOME_DIR" not in cleaned
        assert cleaned["VALUE"] == "keep"
    result = subprocess.run(
        [sys.executable, "-m", "halo", "--external-command", sys.executable, "-c",
         "import json,sys; print(json.dumps(sys.argv[1:])); sys.exit(7)", "a b", "c;d"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 7, result
    assert json.loads(result.stdout) == ["a b", "c;d"], result.stdout
    print("[frozen commands] argv, environment isolation and exit status: OK")


if __name__ == "__main__":
    main()
