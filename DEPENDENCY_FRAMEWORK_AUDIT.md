# H.A.L.O. dependency and framework audit

**Audit date:** 2026-09-04  
**Scope:** dependencies and frameworks that the current repository actually imports, builds, or runs. Future stack choices mentioned only in design documents (for example Pipecat, Playwright, openWakeWord, faster-whisper, Kokoro, pywinauto, and PyAutoGUI) are not counted as current dependency burden.

## Executive verdict

H.A.L.O. should become a **modular monolith**, not a literal single-process application.

Keep Tauri + React as the desktop shell and keep the authenticated loopback process boundary. Consolidate Brain and Voice into one Python distribution, one lock, one release artifact, and one documented installation path, while retaining two entry points/processes so crashes, future real-time audio, and Windows child-process cleanup remain isolated. Make semantic memory and document extraction capability groups rather than mandatory base-install weight. Treat replacing LangGraph as a measured second-stage migration, not a cleanup patch.

The repository does **not** currently suffer from a generally bloated UI or an obviously redundant framework stack. The main findings are more specific:

1. **Release blocker:** `pypdf==6.14.2` has six distinct current resource-exhaustion/denial-of-service advisories. Upgrade it to at least `6.16.1` (prefer the current compatible `6.16.2`) and regenerate the hashed lock.
2. **Open-source blocker:** there is no tracked root `LICENSE`, `COPYING`, `NOTICE`, or root `README`. Publishing the source without a license does not grant normal open-source reuse rights.
3. **Distribution blocker:** the Tauri bundle is active, but Brain and Voice still run from a source checkout through a discovered system Python. A built installer is therefore not self-contained.
4. **Highest safe weight reduction:** the semantic-memory stack accounts for about **18 marginal packages / 141 MiB** before downloaded model weights. Keep the feature in the full desktop build, but move it behind a `semantic` extra and provide SQLite FTS5/BM25 as the no-model baseline.
5. **Largest conditional framework reduction:** LangGraph/checkpointing accounts for about **24 marginal packages / 28 MiB** and constrains `websockets` below 16 through `langgraph-sdk`. The graph itself has only three nodes, but its persistence and interrupt semantics are critical. Replace it only through a compatibility migration with checkpoint conversion and restart/approval golden tests.

## Measured baseline

The numbers below are measurements from the locked Windows development environment, not marketing estimates. Marginal size means packages that disappear when the named feature group is removed while the other current groups remain. Model caches and installer compression are excluded.

| Area | Current direct dependencies | Locked/resolved graph | Relevant measured footprint |
|---|---:|---:|---:|
| Brain Python | 13 | 72 installed production packages | 193.87 MiB total installed closure |
| Voice Python | 1 declared | 1 in its own lock | Imports Brain without declaring it |
| Semantic memory | 2 direct | 18 marginal packages | 141.06 MiB, excluding embedding model download |
| LangGraph/checkpointing | 3 direct | 24 marginal packages | 27.92 MiB |
| Document extraction | 5 direct | 10 marginal packages | 14.87 MiB |
| OS secrets | `keyring` | 6 marginal packages | 1.13 MiB |
| UI npm | 7 runtime, 12 development | 299 lock entries; about 92 runtime entries | Current build: 449.20 kB JS / 139.11 kB gzip; 39.83 kB CSS |
| Tauri/Rust | 5 runtime declarations plus target-specific `windows` | 429 Cargo lock packages | Existing binaries are not a clean current release-size comparison |

Important interpretation: dependency count, `node_modules` size, and shipped bundle size are different things. For example, `react-markdown` owns most of the npm runtime package count, while the entire freshly built UI JavaScript remains 139.11 kB gzip. Conversely, FastEmbed's installed closure is large and its embedding model is downloaded separately, so its real first-run disk/network cost is larger than the table.

## Recommended target architecture

| Boundary | Target | Why this preserves features while simplifying ownership |
|---|---|---|
| Desktop | Keep Tauri 2 + React 19 + Vite | Native window/tray/global-shortcut/process supervision remain cohesive; replacing this stack would be a rewrite, not dependency cleanup. |
| Python product | One distribution, one lock, two entry points (`halo brain`, `halo voice`) | Removes the undeclared cross-package dependency and duplicated setup without coupling Voice crashes or future audio latency to the Brain event loop. |
| Capability profiles | `core`, `documents`, `semantic`, and convenience `full` extras | Contributors can run the core without ONNX/model/document-parser weight; official desktop packaging always selects `full`, so current features stay present. |
| Local transport | Keep authenticated loopback WebSocket | It is small, already hardened, supports two webviews and browser development, and avoids inventing a Tauri-to-Python RPC bridge. |
| Persistence | Keep `halo.db`; initially keep LangGraph's `checkpoints.db` behind one adapter | Avoids an unsafe big-bang migration. Merge checkpoint state into the application database only if the LangGraph replacement is completed. |
| Release | Bundle the Python backend as a Tauri sidecar artifact | Removes the system-Python/source-checkout prerequisite and makes the open-source release reproducible for users. |

This is “more monolithic” at the product, packaging, configuration, and persistence layers while preserving the process boundaries that currently provide fault containment.

## Prioritized change plan

### P0 — required before a public release

#### 1. Patch and contain PDF parsing

**Current evidence:** [`brain/requirements.lock`](brain/requirements.lock) pins `pypdf==6.14.2`; [`brain/brain/extract.py`](brain/brain/extract.py) uses it as a PDF fallback, and command artifact verification also parses PDFs. Current `pip-audit`/OSV results map to six distinct pypdf advisories covering crafted-input excessive runtime, memory exhaustion, and infinite loops.

**Change:**

- Upgrade `pypdf` to `6.16.2` or a later verified compatible patch and regenerate `brain/requirements.lock` with hashes.
- Route **every untrusted PDF ingress path** through the existing killable worker/deadline mechanism. `doc_digest` is contained today, but a direct `file_read` can still reach synchronous extraction without process-level termination.
- Keep `pypdfium2` as the primary renderer/extractor and `pypdf` as the fallback; replacing one parser with another does not eliminate hostile-document limits.

**Why this replacement:** this is a safe patch upgrade with no format regression. The relevant upstream advisories are [GHSA-23w6-3w8w-8484](https://github.com/py-pdf/pypdf/security/advisories/GHSA-23w6-3w8w-8484), [GHSA-763m-79hh-57f2](https://github.com/py-pdf/pypdf/security/advisories/GHSA-763m-79hh-57f2), [GHSA-jp53-mhqp-8xcg](https://github.com/py-pdf/pypdf/security/advisories/GHSA-jp53-mhqp-8xcg), and [GHSA-fc8x-2rww-xw9m](https://github.com/py-pdf/pypdf/security/advisories/GHSA-fc8x-2rww-xw9m).

#### 2. Add the legal/release surface

**Current evidence:** no root license, notice, or README is tracked; the Python, npm, and Cargo manifests also omit consistent license/repository/readme metadata.

**Change:** choose and add a project license, root README, contribution/security policy, and third-party notice/SBOM generation. Add matching SPDX metadata to both Python metadata and `Cargo.toml`, and package the license/notice files. Review the bundled PDFium notices, the `BAAI/bge-small-en-v1.5` model license, icons/fonts/assets, and Windows runtime redistribution separately from code-package licenses. Source code with no license is not open-source merely because it is public; see [Choose a License: No License](https://choosealicense.com/no-permission/).

**Observed license graph:** npm and Cargo metadata showed no obvious GPL-only dependency. Five Cargo transitive packages report MPL-2.0. Python metadata is inconsistent (13 packages had missing/unknown machine-readable license fields), so automate license policy instead of relying on this one-time scan.

#### 3. Produce a self-contained desktop artifact

**Current evidence:** [`ui/src-tauri/tauri.conf.json`](ui/src-tauri/tauri.conf.json) enables bundling but declares no external binary. [`ui/src-tauri/src/supervisor.rs`](ui/src-tauri/src/supervisor.rs) still launches `python -m brain` and `python -m voice` from the source tree.

**Change:** package one Python backend executable with a mode/entry-point argument and declare the target-triple sidecar through Tauri `externalBin`. Keep the current Rust supervisor because it already implements the required restart ladder, session freshness, hidden processes, shutdown ordering, and Windows job-object cleanup. Do not add `tauri-plugin-shell` solely for sidecar launching unless it can preserve all those semantics. Tauri documents this packaging model in [Embedding External Binaries](https://v2.tauri.app/develop/sidecar/).

### P1 — simplify installation without removing capabilities

#### 4. Merge Brain and Voice packaging, not their event loops

**Current evidence:** [`voice/pyproject.toml`](voice/pyproject.toml) declares only WebSockets but imports `brain.ipc.contract`. [`DEVELOPMENT.md`](DEVELOPMENT.md) instructs contributors to manually run `pip install -e ../brain`. Two locks describe what CI actually installs into one environment.

**Replace with:** a root Python distribution (for example `halo-local-assistant`) that includes both package namespaces and declares two console entry points. Generate one universal hashed lock and one development environment. Keep Brain and Voice as separately supervised processes.

This eliminates one package manifest, one lock, an undeclared dependency, and the most common contributor setup mismatch. It does **not** reduce the running process count, because doing so just before real audio work would trade a small WebSocket cost for latency and fault-isolation risk.

The fresh verifier demonstrated the current edge: the default launcher accepted a Python 3.12 runtime that met the version check but lacked `keyring`, causing `./dev.ps1 -Verify` to stop immediately. Explicitly selecting the repository `.venv` let all Python suites pass. The launcher should prefer `.venv/Scripts/python.exe` when it exists and should validate required packages, not only `sys.version_info`.

#### 5. Turn heavy features into install profiles

Use standard `[project.optional-dependencies]`, documented by the [Python Packaging User Guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/):

- `documents`: `pypdfium2`, `pypdf`, `mammoth`, `openpyxl`, `markdownify`.
- `semantic`: `fastembed`, `sqlite-vec`.
- `full`: convenience extra selecting both groups.

Official Tauri releases and the current full development path install `full`. Core-only environments must advertise unavailable capabilities and return a targeted “install the documents/semantic extra” response rather than failing at module import. That requires moving the eager parser imports in [`brain/brain/extract.py`](brain/brain/extract.py) into per-format lazy loaders.

#### 6. Add a built-in lexical memory baseline

**Current evidence:** [`brain/brain/store.py`](brain/brain/store.py) already degrades to recency when FastEmbed/model loading fails. The fallback preserves availability but loses relevance ranking.

**Replace the fallback with:** an SQLite FTS5 table over live beliefs, ranked with BM25. Keep FastEmbed + `sqlite-vec` as the optional semantic reranker/full-profile implementation. SQLite's built-in [FTS5 extension](https://www.sqlite.org/fts5.html) supplies full-text indexing and BM25 without a model runtime.

This reduces a minimal install by about 18 packages / 141 MiB while the full build retains current semantic behavior. Do not silently call lexical results “semantic”: expose the active search capability in diagnostics and tests.

### P2 — conditional framework consolidation

#### 7. Put LangGraph behind an internal checkpoint adapter, then decide whether to remove it

**Current evidence:** [`brain/brain/graph.py`](brain/brain/graph.py) builds a three-node graph (`route`, `respond`, `gate`), while H.A.L.O. already owns the model streaming loop, permission gate, task runtime, memory, SQLite domain store, and serialization policy. The file also reaches below public abstractions: it sets `aiosqlite`'s private `conn._thread.daemon`, queries LangGraph checkpoint tables directly, and depends on the private-looking `__interrupt__` channel. This is high coupling despite the small graph.

**Option A — lower risk now:** keep pinned LangGraph, isolate all checkpoint/interrupt access behind a H.A.L.O. interface, remove private attribute/schema access where upstream APIs permit, and add compatibility tests before every LangGraph upgrade.

**Option B — preferred medium-term if minimizing framework ownership is a product goal:** replace LangGraph + `langgraph-checkpoint-sqlite` + direct `aiosqlite` with a small durable conversation state machine in the existing store. Required states are `responding`, `waiting_approval`, `executing_tool`, `completed`, `interrupted`, and `failed`, with an append-only transition/continuation record and idempotency key per tool call.

Option B can remove about 24 marginal packages / 28 MiB, eliminate the separate checkpoint database, and unblock a future WebSockets upgrade. It is **not** an immediate simplification: LangGraph currently supplies durable interrupts, resume commands, and checkpoint recovery. Its own documentation emphasizes those guarantees in [Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) and [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence). No removal should merge until a migrated database passes every approval/restart scenario.

### P3 — small hygiene and governance

- Remove the direct `postcss` dev declaration from [`ui/package.json`](ui/package.json) unless a project-owned PostCSS config/plugin is added. Vite already resolves the same package transitively. This improves manifest ownership but does not materially shrink the current install graph.
- Update compatible patch/minor releases in small batches: pypdf first; then React/ReactDOM, Zustand, TanStack Virtual, Lucide, pypdfium2, and LangGraph separately with the full gate. Do not combine Vite 8, Vitest 4, TypeScript 7, or other major upgrades with architecture changes.
- Extend CI from one Windows/Python 3.12 lane to the declared Python 3.11 floor plus 3.12 (and 3.13 only after native-wheel validation). Keep npm and pip audits; add `cargo audit` or `cargo deny`, license policy, SBOM generation, and lock-drift checks.
- The current npm advisory endpoint timed out twice during this audit. Record that as “audit unavailable,” not “no vulnerabilities”; CI should retry and fail distinctly on audit-infrastructure failure.

## Dependencies/frameworks that should stay

| Dependency/framework | Verdict | Reason |
|---|---|---|
| Tauri 2 and current Rust plugins | Keep | They implement native windows, tray, global shortcut, state restoration, and hardened sidecar supervision. Electron would be heavier; a Rust-only rewrite would lose the Python AI/document ecosystem. |
| React 19 + Vite + Vitest | Keep | The UI is substantial and well-tested; the production bundle is modest. Vanilla DOM code would increase bespoke state/event complexity. |
| Zustand | Keep | Tiny dependency; the store uses selectors to limit rerenders. Replacing it saves little and risks projection/subscription regressions. |
| TanStack Virtual | Keep | Activity history is capped at 10,000 entries; virtualization is justified and the library's marginal footprint is small. |
| `react-markdown` | Keep | It supplies CommonMark parsing and safe-by-default rendering with raw HTML disabled; a home-grown parser would be a security and compatibility regression. See [react-markdown](https://github.com/remarkjs/react-markdown). |
| Lucide React | Keep | Broad current icon use and tree-shaking mean its large source package is not equivalent to shipped bundle weight. |
| `websockets` | Keep | Small, mature, and central to authenticated reconnect/multi-client behavior. Upgrade only after the LangGraph SDK constraint is removed or upstream permits it. |
| `httpx` | Keep | The Brain already uses a direct OpenRouter client; adding OpenAI/LangChain SDK layers would increase coupling. |
| `keyring` | Keep | A small cost for cross-platform OS-keystore behavior. Moving secrets through Tauri would create more IPC and platform-specific code. |
| Document parsers | Keep in `documents`/`full` | Each maps to a real supported format. Optionalizing them is safer than deleting formats or writing parsers. |
| Internal `TaskRuntime` | Keep | Plain asyncio + SQLite already gives bounded durable tasks without Celery/RQ or another service. |

Avoid adding FastAPI, Celery, Poetry/PDM, Electron, LangChain/OpenAI SDKs, or a JavaScript monorepo framework to solve this audit. None replaces a current problem with less total machinery.

## Edge cases and migration acceptance criteria

### Packaging and process lifecycle

- Brain restart must issue a new ephemeral port/token; UI and Voice must reread `session.json` before every reconnect.
- Installer sidecars must retain Windows job-object descendant cleanup, no console window, shutdown-before-kill ordering, and the 1s/5s/30s backoff reset.
- Packaging must include native binaries/wheels for `sqlite-vec`, PDFium, ONNX Runtime, keyring backends, target triples, and VC/WebView2 prerequisites. Test paths containing spaces and non-ASCII characters.
- PyInstaller hidden imports/resources and antivirus false positives must be tested on a clean machine. Signing/reproducible hashes belong in the release pipeline.
- A core-only developer install must not become the accidentally published desktop build; CI needs an assertion that release artifacts use the `full` profile.

### Optional capabilities and memory migration

- Importing Brain without document extras must succeed; only requests for missing formats should fail, with an actionable capability error.
- Switching semantic support off/on must not delete existing embeddings. Build FTS in a transaction, retain vectors, dual-write during migration, and make rebuild resumable.
- Escape FTS query syntax; test Unicode, punctuation-only input, very long queries, phrase behavior, multilingual text, archived/superseded beliefs, and empty indexes.
- Compare lexical and semantic relevance on a fixed corpus. The full profile must not regress current vector KNN ranking or silently download a model when offline mode is requested.
- Pin and document the embedding model separately from the Python package; model license, checksum, cache location, offline behavior, and upgrade/re-embedding policy are release concerns.

### LangGraph replacement

- Convert existing `checkpoints.db` transactionally and keep a rollback copy/version marker; never strand a pending approval during upgrade.
- Preserve same-conversation serialization, cross-conversation concurrency, exact tool-call IDs, queued multi-tool rounds, maximum recursion/round limits, and partial-stream failure behavior.
- Resume after crash at every boundary: before approval emission, while waiting, after approve/deny, before side effect, after side effect but before durable receipt, and before final response.
- Prove at-most-once side effects through idempotency records; a replayed continuation must not repeat a file mutation or command.
- Preserve interrupt cancellation, summary compaction, history replay filtering, spend accumulation, snapshot rehydration, and two-window convergence.
- During rolling migration, new code must read old checkpoints or explicitly block startup with a recoverable migration path. LangGraph warns that paused runs depend on graph compatibility; review its [backward-compatibility guidance](https://docs.langchain.com/oss/python/langgraph/backward-compatibility) before upgrades.

### Untrusted documents and dependency updates

- Test malformed, encrypted, incremental-update, deeply nested, huge-page-count, scanned/textless, and decompression-bomb-like PDFs under time, memory, page, and output caps.
- Ensure worker timeout kills descendants and deletes temporary files on success, parser crash, cancellation, and app shutdown.
- Validate DOCX external relationships and HTML output sanitization; document extraction must never fetch remote content.
- Keep lock generation compatible with Python 3.11 and platform markers. Native wheels must be available for every supported Windows architecture before updating.

### Open-source release mechanics

- Generate CycloneDX or SPDX SBOMs for Python, npm, Cargo, bundled binaries, and downloaded model assets; attach them to releases.
- Add a vulnerability-reporting policy and define whether local-only denial of service from a user-opened document is in security scope.
- Do not package API keys, session files, model caches, user databases, logs, absolute developer paths, or test artifacts.
- Verify clean-clone setup, offline startup/degradation, upgrade with an existing user database, uninstall behavior, and rollback from a failed schema/checkpoint migration.

## Ranked over-engineering findings (Ponytail view)

1. **native:** mandatory FastEmbed/ONNX for a system that already has SQLite — replacement: FTS5/BM25 baseline plus optional semantic reranking. (`brain/pyproject.toml`, `brain/brain/store.py`)
2. **yagni:** two Python projects and locks for one shipped product, where the 163-line Voice client imports Brain manually — replacement: one distribution/lock, two entry points/processes. (`voice/pyproject.toml`, `DEVELOPMENT.md`)
3. **shrink, conditional:** a three-node graph carries a 24-package checkpoint framework while code relies on its internal thread/schema/channel details — replacement: first an adapter, then a tested internal SQLite state machine if the migration pays for itself. (`brain/brain/graph.py`)
4. **delete:** direct `postcss` ownership with no repository config or direct use — replacement: Vite's existing dependency until a project-owned PostCSS pipeline exists. (`ui/package.json`)

**Net, stated honestly:** the immediate safe deletion is one direct manifest line. A minimal `core` profile can avoid about **28 marginal packages / 156 MiB** by optionalizing semantic and document features while the `full` profile keeps them. A separately justified LangGraph migration can avoid another **24 marginal packages / 28 MiB**. Packaging consolidation removes one lock and one manual install step but intentionally does not remove a process. No credible large source-line reduction should be promised before the LangGraph state-machine prototype exists.

## Verification performed and limitations

- Repository status was clean before the audit; this report is the only workspace change.
- Fresh `npm run build` passed: 2,007 modules transformed; 449.20 kB JavaScript (139.11 kB gzip), 39.83 kB CSS.
- UI tests passed outside the filesystem sandbox: 18 files / 91 tests.
- All Python Brain and Voice suites reached green when run with the repository `.venv`; the default verifier first selected an incomplete bundled Python, documenting the launcher issue above.
- IPC contract sync, TypeScript unused-symbol checks, `pip check`, Cargo offline check, and Vulture (80% confidence) passed. Vulture reported only one test-fake parameter.
- Current `pip-audit` found the pypdf issues described above. npm audit could not return a verdict because the registry advisory endpoint timed out twice. `cargo-audit` is not installed, so no Rust advisory verdict is claimed.
- License results are based on package metadata and require release-time SBOM/notice verification; missing metadata was treated as unknown, never as permissive.

## Suggested execution order

1. Patch pypdf, contain all PDF entry points, add license/release metadata, and make the existing verifier reliably select/install the project environment.
2. Consolidate Python packaging/lock and add `core`/`documents`/`semantic`/`full` profiles with explicit capability reporting.
3. Package the full backend as a Tauri sidecar and validate clean-machine install/upgrade/uninstall.
4. Add FTS5 baseline and migration/quality tests; keep semantic retrieval enabled in full builds.
5. Introduce the LangGraph adapter and collect maintenance/startup/footprint evidence.
6. Only then decide whether an internal state machine gives enough ownership and dependency reduction to justify checkpoint migration risk.
