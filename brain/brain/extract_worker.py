"""Bounded PDF boundary shared by reads, digests and artifact verification.

No parser runs in the parent, no result temporary files are created. Windows
workers start suspended so job ownership and memory limits precede execution.
"""
from __future__ import annotations

import asyncio
import functools
import json
import os
import signal
import subprocess
import sys
import threading
import time
from contextlib import suppress
from pathlib import Path

PDF_MEMORY_BYTES = 512 * 1024 * 1024
PDF_OUTPUT_BYTES = 1024 * 1024
PDF_PAGE_CAP = 100
PDF_INPUT_BYTES = 64 * 1024 * 1024
_WIRE_BYTES = PDF_OUTPUT_BYTES * 6 + 4096
_POLL_SECONDS = .025


def run_pdf(path: Path, *, mode="text", timeout=60.0, cancelled=None):
    """Synchronous bounded API. Async callers use run_cancellable below."""
    from brain.capabilities import require_document_modules
    require_document_modules("pdf")
    from brain.commanding import _ProcessJob, _resume_process
    from brain.task_runtime import TaskStopped

    target = path.resolve()
    if target.stat().st_size > PDF_INPUT_BYTES:
        raise ValueError(f"{target.name}: refusing to read more than 64MB")
    if mode not in ("text", "pages"):
        raise ValueError("unknown PDF operation")
    if cancelled is not None and cancelled.is_set():
        raise TaskStopped()
    deadline = time.monotonic() + timeout
    if timeout <= 0:
        raise TimeoutError(f"could not extract {target.name}: exceeded {timeout:g}s deadline")
    # Frozen entry points dispatch --pdf-worker before Brain/Voice startup.
    command = [sys.executable, "--pdf-worker"] if getattr(sys, "frozen", False) else [sys.executable, "-I", str(Path(__file__).resolve())]
    process = subprocess.Popen(
        command + [str(target), mode], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        creationflags=(0x08000000 | 0x00000004) if os.name == "nt" else 0,
        start_new_session=os.name != "nt",
    )
    job, reader = None, None
    chunks = []
    try:
        job = _ProcessJob(process.pid, memory_bytes=PDF_MEMORY_BYTES)
        _resume_process(process.pid)

        def drain():
            # No pickle or attacker-provided allocation size. A partial frame
            # cannot block the parent's deadline/cancellation loop.
            chunks.append(process.stdout.read(_WIRE_BYTES + 1))

        reader = threading.Thread(target=drain, name="halo-pdf-output", daemon=True)
        reader.start()
        while True:
            if cancelled is not None and cancelled.is_set():
                raise TaskStopped()
            if chunks and len(chunks[0]) > _WIRE_BYTES:
                raise ValueError(f"{target.name}: PDF worker output limit exceeded")
            if process.poll() is not None:
                break
            if time.monotonic() >= deadline:
                raise TimeoutError(f"could not extract {target.name}: exceeded {timeout:g}s deadline")
            time.sleep(_POLL_SECONDS)
        # Kill descendants before waiting for inherited stdout to close.
        if job:
            job.close()
        if os.name != "nt":
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
        reader.join(.5)
        if reader.is_alive() or process.returncode != 0 or not chunks:
            raise ValueError(f"{target.name}: PDF worker exited without a result (memory limit or parser crash)")
        if len(chunks[0]) > _WIRE_BYTES:
            raise ValueError(f"{target.name}: PDF worker output limit exceeded")
        try:
            result = json.loads(chunks[0])
            if result["status"] != "ok":
                raise ValueError(f"could not extract {target.name}: {result['error']}")
            value = result["value"]
            if mode == "text" and (not isinstance(value, str) or len(value.encode("utf-8")) > PDF_OUTPUT_BYTES):
                raise ValueError("PDF worker output limit exceeded")
            if mode == "pages" and (type(value) is not int or not 0 < value <= PDF_PAGE_CAP):
                raise ValueError("PDF page verification limit exceeded")
            return value
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError(f"{target.name}: invalid PDF worker result") from exc
    finally:
        if job:
            job.close()
        if os.name != "nt":
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
        if process.poll() is None:
            process.kill()
        process.wait(timeout=1)
        if reader:
            reader.join(.5)
        process.stdout.close()


async def run_cancellable(fn, *args, cancelled=None, **kwargs):
    """Cancel a blocking owner, then wait for its finally to reap the tree."""
    from brain.task_runtime import TaskStopped
    stop = threading.Event()
    if cancelled is not None and cancelled.is_set():
        raise TaskStopped()
    pending = asyncio.get_running_loop().run_in_executor(None, functools.partial(fn, *args, cancelled=stop, **kwargs))
    try:
        while not pending.done():
            if cancelled is not None and cancelled.is_set():
                stop.set()
            await asyncio.sleep(_POLL_SECONDS)
        value = await asyncio.shield(pending)
        if stop.is_set():
            raise TaskStopped()
        return value
    finally:
        stop.set()
        # Repeated cancellation must not abandon the cleanup owner.
        while not pending.done():
            try:
                await asyncio.shield(pending)
            except asyncio.CancelledError:
                continue
            except BaseException:
                break
        if pending.done() and not pending.cancelled():
            pending.exception()


async def extract_pdf_isolated(path: Path, cancelled=None, timeout=60.0) -> str:
    try:
        return await run_cancellable(run_pdf, path, cancelled=cancelled, timeout=timeout)
    except TimeoutError as exc:
        raise ValueError(str(exc)) from exc


def worker_main(arguments=None):
    """Internal source/frozen entry; imports parsers only after limits."""
    if os.name != "nt":
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (PDF_MEMORY_BYTES, PDF_MEMORY_BYTES))
        resource.setrlimit(resource.RLIMIT_CPU, (60, 60))

    if os.name != "nt":
        parent_pid = os.getppid()

        def parent_closed():
            while os.getppid() == parent_pid:
                time.sleep(.1)
            os.killpg(os.getpgrp(), signal.SIGKILL)

        threading.Thread(target=parent_closed, daemon=True).start()
    try:
        path, mode = arguments if arguments is not None else sys.argv[1:]
        delay = float(os.environ.get("HALO_EXTRACT_STUB_DELAY", "0"))
        if mode == "pages" and os.environ.get("HALO_TEST_PDF_VERIFY_BLOCK") == "1":
            delay = 30
        if delay > 0:
            time.sleep(delay)
        if not getattr(sys, "frozen", False):
            sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from brain.extract import _extract_pdf, _pdf_pages
        target = Path(path)
        if target.stat().st_size > PDF_INPUT_BYTES:
            raise ValueError("refusing to read more than 64MB")
        value = _extract_pdf(target) if mode == "text" else _pdf_pages(target)
        if isinstance(value, str) and len(value.encode("utf-8")) > PDF_OUTPUT_BYTES:
            raise ValueError("PDF output limit exceeded")
        result = {"status": "ok", "value": value}
    except BaseException as exc:
        result = {"status": "error", "error": f"{type(exc).__name__}: {str(exc)[:1000]}"}
    sys.stdout.write(json.dumps(result, ensure_ascii=True))
    sys.stdout.flush()


if __name__ == "__main__":
    worker_main()
