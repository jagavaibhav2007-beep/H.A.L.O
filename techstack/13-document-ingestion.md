# Tech Stack: Document Ingestion & Token-Lean Reading

Companion to [systemdesign/13-document-ingestion.md](../systemdesign/13-document-ingestion.md).

## Choices

| concern | choice | why |
|---|---|---|
| PDF text | **pypdfium2** (already installed) | Chromium's PDFium via BSD-licensed bindings; fast C++ extraction; also rasterizes pages (future OCR/vision path). `pypdf` (installed, BSD) as fallback + metadata. |
| DOCX | **mammoth** (new) | MIT, pure Python, produces semantic HTML/markdown — headings and lists survive. |
| XLSX | **openpyxl** (new) | MIT, standard reader; we emit markdown pipe tables ourselves with row caps. |
| HTML | **markdownify** (new) | MIT, small; tag/boilerplate stripping is the biggest single token win of any format. |
| Digest map/reduce model | existing `llm.LIGHT` via OpenRouter | every call bounded ≤~3k tokens, flash-class safe; parallelism bounded by the existing `_LLM_SEM` (4). |
| Digest cache | SQLite table in the existing store, keyed `(path, sha256, digest_version)` | no new storage system; MigrationLog v3. |
| Chunk embeddings (deferred) | fastembed 0.8.0 + sqlite-vec (both already in the stack) | only if pointed Q&A over large corpora becomes a real need. |

## Explicitly not in the stack

- **pymupdf4llm / PyMuPDF** — AGPL-3.0; incompatible with distributing this repo under a permissive license. Best quality-per-ms on digital PDFs, but a licensing landmine (Artifex dual-licenses commercially).
- **docling** — MIT and best-in-class PDF structure (layout model + TableFormer), but ~1GB torch install and seconds-per-page on CPU. Candidate for an optional, lazily-installed "deep parse" tier later; never a base dependency.
- **unstructured** — needs poppler/tesseract/libreoffice system binaries; hostile on Windows; `fast` mode adds nothing over installed libs.
- **LLMLingua / LongLLMLingua** — torch + model downloads for token-deletion compression; degraded prompts hurt small models most; solves the wrong problem.
- **markitdown as a dependency** — we copy its dispatcher shape instead; its PDF path is flat pdfminer text, worse than pypdfium2 already installed.

## Install weight

PDF fallback is pinned to pypdf 6.16.2 in the hashed Brain lock (minimum
`>=6.16.2,<7`). Its [upstream changelog](https://pypdf.readthedocs.io/en/6.16.2/meta/CHANGELOG.html)
includes the 6.15.0 parser-complexity fixes and 6.16.1 XForm/outline iteration
bounds. The previous 6.14.2 pin is affected by
[GHSA-fc8x-2rww-xw9m](https://github.com/py-pdf/pypdf/security/advisories/GHSA-fc8x-2rww-xw9m).
Parser updates complement the shared subprocess resource limits; they do not
replace them. PDFium 5.12.1 is unchanged in this patch.

Mammoth external access remains explicitly off, matching its
[security guidance](https://github.com/mwilliamson/python-mammoth#security).

New deps: `mammoth` + `openpyxl` + `markdownify` — pure Python, a few MB total, no native builds, no model downloads. Everything else is already in the environment.
