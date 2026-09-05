"""Hostile worker fixture for the real subprocess owner (never production)."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

path = Path(sys.argv[1])
mode = path.stem
if mode == 'memory':
    try:
        data = bytearray(768 * 1024 * 1024)
        sys.stdout.write(json.dumps({'status': 'ok', 'value': 'allocation escaped'}))
    except MemoryError:
        sys.stdout.write(json.dumps({'status': 'error', 'error': 'memory limit enforced'}))
elif mode == 'output':
    sys.stdout.write('x' * (8 * 1024 * 1024))
elif mode == 'crash':
    os._exit(7)
elif mode in ('tree', 'tree_success'):
    sentinel = path.with_suffix('.survived')
    child = subprocess.Popen([sys.executable, '-c', f'import time; from pathlib import Path; time.sleep(1); Path({str(sentinel)!r}).write_text("alive")'])
    path.with_suffix('.ready').write_text(str(child.pid))
    if mode == 'tree':
        time.sleep(30)
    else:
        sys.stdout.write(json.dumps({'status': 'ok', 'value': 'done'}))
elif mode == 'partial':
    sys.stdout.write('{"status":"ok", "value":"')
    sys.stdout.flush()
    time.sleep(30)
else:
    time.sleep(30)
