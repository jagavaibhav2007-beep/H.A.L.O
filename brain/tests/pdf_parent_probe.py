"""Exercise worker ownership when its actual Python parent exits or crashes."""
import asyncio
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import extract_worker

target, mode = Path(sys.argv[1]), sys.argv[2]
real_spawn = subprocess.Popen


def spawn(command, *args, **kwargs):
    command = list(command)
    command[2] = str(Path(__file__).with_name('pdf_worker_probe.py'))
    return real_spawn(command, *args, **kwargs)


extract_worker.subprocess.Popen = spawn
target.with_suffix('.host').write_text(str(os.getpid()))


async def main():
    pending = asyncio.create_task(extract_worker.extract_pdf_isolated(target))
    if mode == 'shutdown':
        while not target.with_suffix('.ready').exists():
            await asyncio.sleep(.025)
        return  # asyncio.run must cancel the live task and finish its cleanup
    await pending


asyncio.run(main())
