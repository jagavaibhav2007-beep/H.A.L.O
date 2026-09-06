"""Check an installed core/full wheel from an unrelated path with no PYTHONPATH.

Run using an environment with websockets, passing the target Python explicitly.
Only a temporary LOCALAPPDATA is touched. No model or API key is used.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
from pathlib import Path
import subprocess
import tempfile
import time
import uuid
from unittest.mock import patch

from websockets.asyncio.client import connect
from brain.commanding import _ProcessJob, _resume_process


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
        # Allow the initial snapshot to finish instead of closing midway.
        while frame["type"] != "snapshot_complete":
            frame = json.loads(await asyncio.wait_for(ws.recv(), 10))


def check_frozen_workers(executable, root, env):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    from brain.extract_worker import run_pdf, extract_pdf_isolated
    writer = PdfWriter()
    page = writer.add_blank_page(width=200, height=200)
    font = writer._add_object(DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    }))
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): font}),
    })
    content = DecodedStreamObject()
    content.set_data(b"BT /F1 12 Tf 10 100 Td (Frozen PDF works) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(content)
    path = root / "worker fixture.pdf"
    writer.write(path)
    async def cancel_worker():
        with patch.dict(os.environ, {"HALO_EXTRACT_STUB_DELAY": "30"}):
            task = asyncio.create_task(extract_pdf_isolated(path))
            await asyncio.sleep(.25)
            start = time.monotonic()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            else:
                raise AssertionError("frozen PDF worker ignored cancellation")
            assert time.monotonic() - start < 2
    # Exercise the production worker boundary with the copied frozen runtime.
    with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", str(executable)), patch.dict(os.environ, {"TEMP": str(root), "TMP": str(root)}):
        assert "Frozen PDF works" in run_pdf(path)
        assert run_pdf(path, mode="pages") == 1
        asyncio.run(cancel_worker())
    result = subprocess.run(
        [str(executable), "--external-command", str(Path(os.environ["SystemRoot"]) / "System32" / "cmd.exe"),
         "/d", "/c", "echo external-helper&exit /b 7"],
        cwd=root, env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 7 and "external-helper" in result.stdout, (result.returncode, result.stdout, result.stderr)
    print("[frozen] PDF text/pages, cancellation and external-command output/exit status PASS", flush=True)


def main():
    sys.stdout.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser()
    runtime = parser.add_mutually_exclusive_group(required=True)
    runtime.add_argument("--python", type=Path)
    runtime.add_argument("--executable", type=Path)
    parser.add_argument("--profile", required=True, choices=("core", "full"))
    args = parser.parse_args()
    python = str(args.python.resolve()) if args.python else None
    with ProfileDirectory(prefix="Halo profile café ") as folder:
        root = Path(folder)
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME")}
        env.update(LOCALAPPDATA=folder, TEMP=folder, TMP=folder, HF_HUB_OFFLINE="1", HALO_LLM_STUB="1", HALO_EXTRACT_STUB="1")
        if args.executable:
            executable = root / "Halo backend café.exe"
            shutil.copy2(args.executable.resolve(), executable)
            command = [str(executable)]
            env["PATH"] = str(Path(os.environ["SystemRoot"]) / "System32")
        else:
            command = [python, "-I", "-m", "halo"]
        report = subprocess.run(command + ["diagnostics"], cwd=root, env=env, capture_output=True, text=True, check=True, timeout=30)
        caps = json.loads(report.stdout)
        expected = args.profile == "full"
        assert all(value == expected for value in caps["documents"].values()), caps
        assert caps["semantic_dependencies"] == expected, caps
        if args.executable:
            check_frozen_workers(executable, root, env)
        for mode in ("brain", "voice"):
            subprocess.run(command + [mode, "--help"], cwd=root, env=env, capture_output=True, check=True, timeout=10)
        # -m compatibility must resolve the installed packages, not this tree.
        if python:
            subprocess.run([python, "-I", "-c", "import brain.server, voice.__main__"], cwd=root, env=env, check=True, timeout=20)
        processes = []
        jobs = {}
        with (root / "brain.log").open("w", encoding="utf-8") as brain_log, (root / "voice.log").open("w", encoding="utf-8") as voice_log:
            def spawn(mode, log):
                child = subprocess.Popen(
                    command + [mode], cwd=root, env=env, stdout=log, stderr=log,
                    creationflags=(0x08000000 | 0x00000004) if os.name == "nt" else 0,
                )
                processes.append(child)
                jobs[child.pid] = _ProcessJob(child.pid)
                _resume_process(child.pid)
                return child
            def brain():
                return spawn("brain", brain_log)
            try:
                first = brain()
                session_path = root / "Halo" / "session.json"
                session = wait_session(session_path, first)
                asyncio.run(authenticate(session))
                voice = spawn("voice", voice_log)
                def wait_voice(count):
                    # A cold one-file restart can miss two connection attempts,
                    # reaching the existing 30-second reconnect rung.
                    deadline = time.monotonic() + 45
                    while time.monotonic() < deadline:
                        assert voice.poll() is None, "Voice exited"
                        if (root / "voice.log").read_text(encoding="utf-8", errors="replace").count("authentication acknowledged") >= count:
                            return
                        time.sleep(.05)
                    raise AssertionError(f"Voice did not authenticate {count} time(s)")
                wait_voice(1)
                first.kill()
                first.wait(timeout=5)
                jobs[first.pid].close()  # generation exit must reap interpreter descendants
                second = brain()
                fresh = wait_session(session_path, second, session["token"])
                asyncio.run(authenticate(fresh))
                wait_voice(2)
            except BaseException:
                brain_log.flush()
                voice_log.flush()
                print((root / "brain.log").read_text(encoding="utf-8", errors="replace"))
                print((root / "voice.log").read_text(encoding="utf-8", errors="replace"))
                raise
            finally:
                for process in reversed(processes):
                    if process.pid in jobs:
                        jobs[process.pid].close()
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=5)
    print(f"[profile] {args.profile}: installed imports, diagnostics, Brain auth, Voice and restart reconnect PASS")


if __name__ == "__main__":
    main()
