"""Check an installed core/full wheel from an unrelated path with no PYTHONPATH.

Run using an environment with websockets, passing the target Python explicitly.
Only a temporary LOCALAPPDATA is touched. No model or API key is used.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import uuid

from websockets.asyncio.client import connect


class ProfileDirectory(tempfile.TemporaryDirectory):
    def cleanup(self):
        # Windows can briefly retain a redirected handle after process.wait()
        # (or an antivirus scan). Retry only sharing/permission failures, bounded;
        # never hide a persistent cleanup error or declare success before cleanup.
        deadline = time.monotonic() + 3
        while True:
            try:
                return super().cleanup()
            except PermissionError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(.05)


def wait_session(path, process, previous=None):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError(f"Brain exited early: {process.returncode}")
        try:
            session = json.loads(path.read_text(encoding="utf-8"))
            if session.get("token") != previous:
                return session
        except (OSError, ValueError):
            pass
        time.sleep(.05)
    raise AssertionError("Brain did not publish a fresh session")


async def authenticate(session):
    async with connect(f"ws://127.0.0.1:{session['port']}") as ws:
        await ws.send(json.dumps({
            "type": "hello", "id": str(uuid.uuid4()), "ts": "2026-09-05T00:00:00Z",
            "token": session["token"], "role": "ui",
        }))
        frame = json.loads(await asyncio.wait_for(ws.recv(), 5))
        assert frame["type"] == "hello_ack", frame


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", required=True, type=Path)
    parser.add_argument("--profile", required=True, choices=("core", "full"))
    args = parser.parse_args()
    python = str(args.python.resolve())
    with ProfileDirectory(prefix="Halo profile café ") as folder:
        root = Path(folder)
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME")}
        env.update(LOCALAPPDATA=folder, HF_HUB_OFFLINE="1", HALO_LLM_STUB="1", HALO_EXTRACT_STUB="1")
        command = [python, "-I", "-m", "halo"]
        report = subprocess.run(command + ["diagnostics"], cwd=root, env=env, capture_output=True, text=True, check=True, timeout=30)
        caps = json.loads(report.stdout)
        expected = args.profile == "full"
        assert all(value == expected for value in caps["documents"].values()), caps
        assert caps["semantic_dependencies"] == expected, caps
        for mode in ("brain", "voice"):
            subprocess.run(command + [mode, "--help"], cwd=root, env=env, capture_output=True, check=True, timeout=10)
        # -m compatibility must resolve the installed packages, not this tree.
        subprocess.run([python, "-I", "-c", "import brain.server, voice.__main__"], cwd=root, env=env, check=True, timeout=20)
        processes = []
        with (root / "brain.log").open("w", encoding="utf-8") as brain_log, (root / "voice.log").open("w", encoding="utf-8") as voice_log:
            def brain():
                child = subprocess.Popen(command + ["brain"], cwd=root, env=env, stdout=brain_log, stderr=brain_log)
                processes.append(child)
                return child
            try:
                first = brain()
                session_path = root / "Halo" / "session.json"
                session = wait_session(session_path, first)
                asyncio.run(authenticate(session))
                voice = subprocess.Popen(command + ["voice"], cwd=root, env=env, stdout=voice_log, stderr=voice_log)
                processes.append(voice)
                def wait_voice(count):
                    deadline = time.monotonic() + 15
                    while time.monotonic() < deadline:
                        assert voice.poll() is None, "Voice exited"
                        if (root / "voice.log").read_text(encoding="utf-8").count("authentication acknowledged") >= count:
                            return
                        time.sleep(.05)
                    raise AssertionError(f"Voice did not authenticate {count} time(s)")
                wait_voice(1)
                first.kill()
                first.wait(timeout=5)
                second = brain()
                fresh = wait_session(session_path, second, session["token"])
                asyncio.run(authenticate(fresh))
                wait_voice(2)
            except BaseException:
                brain_log.flush()
                voice_log.flush()
                print((root / "brain.log").read_text(encoding="utf-8"))
                print((root / "voice.log").read_text(encoding="utf-8"))
                raise
            finally:
                for process in reversed(processes):
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=5)
    print(f"[profile] {args.profile}: installed imports, diagnostics, Brain auth, Voice and restart reconnect PASS")


if __name__ == "__main__":
    main()
