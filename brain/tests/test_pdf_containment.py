"""Real subprocess containment checks; plain assertions, no external fixtures."""
from __future__ import annotations

import asyncio
import inspect
import os
import sys
import tempfile
import time
import subprocess
import socket
import signal
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
from brain import extract, extract_worker, gate, commanding
from brain.tools import files


def text_pdf(path: Path, pages: int = 1, text: str = "Hello PDF", encrypted=False):
    writer = PdfWriter()
    font = writer._add_object(DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    }))
    for i in range(pages):
        page = writer.add_blank_page(width=max(200, len(text) * 12), height=200)
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 10 100 Td ({text} page {i + 1}) Tj ET".encode())
        page[NameObject("/Contents")] = writer._add_object(stream)
    if encrypted:
        writer.encrypt("not-the-password")
    writer.write(path)


def check_public_entry_isolated(root):
    path = root / "normal.pdf"
    text_pdf(path)
    with patch.object(extract.pdfium, "PdfDocument", side_effect=ValueError("parent parser reached")), patch.object(extract, "PdfReader", side_effect=ValueError("parent parser reached")):
        assert "Hello PDF" in extract.extract_text(path)
        assert "Hello PDF" in files._file_read({"path": str(path)})
    print("[pdf] public extraction and direct file_read never parse in the parent: OK")


async def check_registered_read_cancellation(root):
    path = root / "slow.pdf"
    text_pdf(path)
    fn = gate.TOOLS["file_read"]["fn"]
    assert inspect.iscoroutinefunction(fn), "registered PDF read must propagate asyncio cancellation"
    with patch.dict(os.environ, {"HALO_EXTRACT_STUB_DELAY": "30"}):
        running = asyncio.create_task(fn({"path": str(path)}))
        await asyncio.sleep(.25)
        start = time.monotonic()
        running.cancel()
        try:
            await running
            raise AssertionError("cancelled read returned")
        except asyncio.CancelledError:
            pass
        assert time.monotonic() - start < 2
    print("[pdf] registered file_read cancels within two seconds: OK")


def check_real_pdf_edges(root):
    path = root / 'many pages.pdf'
    text_pdf(path, pages=101)
    text = extract.extract_text(path)
    assert 'page 100' in text and 'page 101' not in text
    assert 'truncated at 100 pages of 101 total' in text
    page = files._file_read({'path': str(path), 'offset': 3, 'limit': 1})
    assert 'page 2' in page and 'showing lines 3-3' in page, page
    encrypted = root / 'encrypted.pdf'
    text_pdf(encrypted, encrypted=True)
    malformed = root / 'malformed.pdf'
    malformed.write_bytes(b'%PDF-1.4\nnot a pdf\n%%EOF')
    blank = root / 'blank.pdf'
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.write(blank)
    huge = root / 'huge-page.pdf'
    # PDFium itself clips a single text object to 32767 characters, so use
    # multiple real pages to cross the extraction output bound.
    text_pdf(huge, pages=40, text='A' * 32000)
    for target, expected in [(encrypted, 'encrypted'), (malformed, 'parse'), (blank, 'no extractable text'), (huge, 'output limit')]:
        try:
            extract.extract_text(target)
            raise AssertionError(f'{target.name} unexpectedly succeeded')
        except ValueError as exc:
            assert expected in str(exc), str(exc)
    try:
        commanding._pdf_pages(path, None)
        raise AssertionError('oversized page count verified')
    except ValueError as exc:
        assert 'page verification limit' in str(exc)
    print('[pdf] real malformed/encrypted/textless/huge-output PDFs, page cap and read pagination: OK')


def check_fallback_and_external_docx(root):
    pdf = root / 'fallback.pdf'
    text_pdf(pdf)
    with patch.object(extract.pdfium, 'PdfDocument', side_effect=ValueError('PDFium rejected fixture')):
        assert 'Hello PDF' in extract._extract_pdf(pdf)
    docx = root / 'external.docx'
    parts = {
        '[Content_Types].xml': b'''<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>''',
        '_rels/.rels': b'''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="main" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>''',
    }
    parts['word/document.xml'] = b'''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><w:body><w:p><w:r><w:t>Local text</w:t><w:drawing><wp:inline><a:graphic><a:graphicData><pic:pic><pic:blipFill><a:blip r:link="remote"/></pic:blipFill></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p></w:body></w:document>'''
    parts['word/_rels/document.xml.rels'] = b'''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="remote" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" TargetMode="External" Target="http://127.0.0.1:9/never-fetch.png"/></Relationships>'''
    with zipfile.ZipFile(docx, 'w') as archive:
        for name, data in parts.items():
            archive.writestr(name, data)
    connections = []

    def forbid_network(*args, **kwargs):
        connections.append(args)
        raise AssertionError('document parser attempted network access')

    with patch.object(socket.socket, 'connect', forbid_network):
        assert 'Local text' in extract.extract_text(docx)
    assert connections == [], 'external DOCX relationship fetched remote content'
    print('[pdf/docx] pypdf fallback retains text; external DOCX image never connects: OK')


async def check_worker_failures_and_trees(root):
    original = subprocess.Popen
    owned = []

    def spawn(command, *args, **kwargs):
        command = list(command)
        command[2] = str(Path(__file__).with_name('pdf_worker_probe.py'))
        proc = original(command, *args, **kwargs)
        owned.append(proc)
        return proc

    with patch.object(extract_worker.subprocess, 'Popen', spawn):
        for mode, expected in [('memory', 'memory limit'), ('output', 'output limit'), ('crash', 'worker exited'), ('partial', 'deadline')]:
            path = root / f'{mode}.pdf'
            path.write_bytes(b'%PDF')
            try:
                await extract_worker.extract_pdf_isolated(path, timeout=5 if mode == 'memory' else 1)
                raise AssertionError(f'{mode} worker succeeded')
            except ValueError as exc:
                assert expected in str(exc), str(exc)
        for mode in ['tree', 'tree_success']:
            path = root / f'{mode}.pdf'
            path.write_bytes(b'%PDF')
            running = asyncio.create_task(extract_worker.extract_pdf_isolated(path))
            for _ in range(200):
                if path.with_suffix('.ready').exists():
                    break
                await asyncio.sleep(.025)
            assert path.with_suffix('.ready').exists(), 'descendant never started'
            if mode == 'tree':
                started = time.monotonic()
                running.cancel()
                await asyncio.sleep(0)
                running.cancel()  # repeated stop must still wait for owner cleanup
                try:
                    await running
                    raise AssertionError('cancel returned normally')
                except asyncio.CancelledError:
                    pass
                assert time.monotonic() - started < 2
            else:
                assert await running == 'done'
            await asyncio.sleep(1.1)
            assert not path.with_suffix('.survived').exists(), 'descendant escaped containment'
    assert all(proc.poll() is not None for proc in owned), 'worker left alive'
    print('[pdf] memory, wire output, crash, partial-frame deadline, repeated cancellation and descendant cleanup: OK')


async def check_artifact_cancellation(root):
    from brain.task_runtime import TaskStopped
    path = root / 'artifact.pdf'
    text_pdf(path)
    item = commanding.Artifact(path=path, kind='pdf', required=True, overwrite=False)
    cancelled = asyncio.Event()
    with patch.dict(os.environ, {'HALO_TEST_PDF_VERIFY_BLOCK': '1'}):
        pending = asyncio.create_task(extract_worker.run_cancellable(commanding._verify_artifact, item, None, cancelled=cancelled))
        await asyncio.sleep(.25)
        started = time.monotonic()
        cancelled.set()
        try:
            await pending
            raise AssertionError('artifact ignored stop')
        except TaskStopped:
            pass
        assert time.monotonic() - started < 2
    print('[pdf] artifact verification observes TaskRuntime stop: OK')


async def check_parent_exit(root):
    for mode in ['crash', 'shutdown']:
        folder = root / mode
        folder.mkdir()
        path = folder / 'tree.pdf'
        path.write_bytes(b'%PDF')
        proc = subprocess.Popen([sys.executable, str(Path(__file__).with_name('pdf_parent_probe.py')), str(path), mode], creationflags=0x08000000 if os.name == 'nt' else 0)
        actual_pid = None
        try:
            for _ in range(240):
                if path.with_suffix('.ready').exists():
                    break
                await asyncio.sleep(.025)
            assert path.with_suffix('.ready').exists(), 'host did not start its worker descendant'
            actual_pid = int(path.with_suffix('.host').read_text())
            if mode == 'crash':
                os.kill(actual_pid, signal.SIGTERM)
            await asyncio.to_thread(proc.wait, 2)
            await asyncio.sleep(1.1)
            assert not path.with_suffix('.survived').exists(), f'descendant survived parent {mode}'
        finally:
            if proc.poll() is None:
                if actual_pid is not None:
                    try:
                        os.kill(actual_pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                proc.kill()
                proc.wait(timeout=2)
    print('[pdf] parent crash and asyncio shutdown reap worker descendants: OK')


async def main():
    with tempfile.TemporaryDirectory(prefix="halo-pdf-test-") as tmp:
        root = Path(tmp)
        check_public_entry_isolated(root)
        await check_registered_read_cancellation(root)
        check_real_pdf_edges(root)
        await check_worker_failures_and_trees(root)
        await check_artifact_cancellation(root)
        check_fallback_and_external_docx(root)
        await check_parent_exit(root)


if __name__ == "__main__":
    asyncio.run(main())
