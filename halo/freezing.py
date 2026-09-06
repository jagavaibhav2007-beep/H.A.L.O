"""Keep PyInstaller's process-global DLL search changes out of external tools.

Only the short-lived helper resets DLL lookup, never the concurrent Brain.
The parent owns the helper and its descendants in the existing command Job.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def external_argv(argv: list[str], env: dict[str, str]) -> list[str]:
    if not getattr(sys, "frozen", False):
        return argv
    # Preserve the bootloader's own state unchanged so this same-executable
    # child reuses the parent's extraction directory. Do not accept caller
    # overrides of these reserved keys or invent their values.
    for key in list(env):
        if key.startswith("_PYI_") or key == "PYINSTALLER_RESET_ENVIRONMENT":
            del env[key]
    env.update((key, value) for key, value in os.environ.items() if key.startswith("_PYI_"))
    return [sys.executable, "--external-command", *argv]


def external_environment(env: dict[str, str]) -> dict[str, str]:
    result = {key: value for key, value in env.items() if not key.startswith("_PYI_")}
    if getattr(sys, "_MEIPASS", None):
        bundled = Path(sys._MEIPASS).resolve()
        result["PATH"] = os.pathsep.join(
            item for item in result.get("PATH", "").split(os.pathsep)
            if item and not Path(item).resolve().is_relative_to(bundled)
        )
    if "LD_LIBRARY_PATH_ORIG" in result:
        result["LD_LIBRARY_PATH"] = result.pop("LD_LIBRARY_PATH_ORIG")
    elif getattr(sys, "frozen", False):
        result.pop("LD_LIBRARY_PATH", None)
    return result


def run_external(argv: list[str]) -> int:
    if not argv:
        raise SystemExit("external-command requires an executable")
    if os.name == "nt" and getattr(sys, "frozen", False):
        import ctypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.SetDllDirectoryW.argtypes = (ctypes.c_wchar_p,)
        kernel.SetDllDirectoryW.restype = ctypes.c_int
        if not kernel.SetDllDirectoryW(None):
            raise ctypes.WinError(ctypes.get_last_error())
    return subprocess.call(
        argv, env=external_environment(dict(os.environ)),
        stdin=sys.stdin if sys.stdin is not None else subprocess.DEVNULL,
        stdout=sys.stdout if sys.stdout is not None else subprocess.DEVNULL,
        stderr=sys.stderr if sys.stderr is not None else subprocess.DEVNULL,
        creationflags=0x08000000 if os.name == "nt" else 0,
    )
