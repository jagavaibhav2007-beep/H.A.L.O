"""Core imports and actionable missing-format errors with extras unavailable."""
import importlib.abc
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

OPTIONAL = {'pypdf', 'pypdfium2', 'mammoth', 'openpyxl', 'markdownify', 'fastembed', 'sqlite_vec'}


class MissingExtras(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in OPTIONAL:
            raise ModuleNotFoundError(fullname)


def without_extras():
    sys.meta_path.insert(0, MissingExtras())
    with tempfile.TemporaryDirectory() as folder:
        os.environ['LOCALAPPDATA'] = folder
        from brain import extract, server, store
        from brain.capabilities import capabilities, runtime_frame
        from brain.ipc.contract import parse_ipc_message
        path = Path(folder) / 'plain.txt'
        path.write_text('core text works', encoding='utf-8')
        assert extract.extract_text(path) == 'core text works'
        conn = store.connect(Path(folder) / 'core.db')
        belief, _ = store.add_candidate_belief('local preference', 'preference', 'user')
        assert store.get_belief(belief)['text'] == 'local preference'
        assert not capabilities()['semantic_dependencies']
        assert 'memory_retrieval' not in runtime_frame(), (
            'startup diagnostics must not invent a last-retrieval mode before the first search'
        )
        assert store.search_beliefs('preference')[0]['belief_id'] == belief
        runtime = runtime_frame()
        assert runtime['memory_retrieval'] == 'lexical'
        assert runtime['semantic_model_ready'] is False
        assert all(runtime['docs_' + kind] is False for kind in ('pdf', 'docx', 'xlsx', 'html'))
        parse_ipc_message({'type': 'capabilities_state', 'id': 'test', 'ts': '2026-09-09T00:00:00Z', **runtime})
        for suffix in ('.pdf', '.docx', '.xlsx', '.html'):
            path = Path(folder) / ('missing' + suffix)
            path.write_bytes(b'placeholder')
            try:
                extract.extract_text(path)
            except ValueError as exc:
                assert 'documents' in str(exc) and 'install' in str(exc), str(exc)
            else:
                raise AssertionError(f'{suffix} accepted without its parser')
        store.close()
    print('[capabilities] core imports/SQLite/text work and missing formats explain installation: OK')


if __name__ == '__main__':
    if '--child' in sys.argv:
        without_extras()
    else:
        subprocess.run([sys.executable, __file__, '--child'], check=True)
