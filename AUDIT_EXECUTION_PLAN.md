# Dependency audit execution

Source: DEPENDENCY_FRAMEWORK_AUDIT.md (2026-09-04). User approved isolated worktree and deferred the license portion on 2026-09-05. Architecture authority remains Halo-PRD.md and systemdesign/. This checklist makes the supplied audit executable; it does not replace it.

## Global constraints

Keep Tauri/React, authenticated loopback, separately supervised Brain and Voice, permission gate, durable TaskRuntime, reconnect freshness, and Windows descendant cleanup. No major frontend upgrades, new service framework, external publishing, or user data migration without rollback. Official desktop artifacts must select full capabilities. Preserve existing user data and embeddings. Do not claim native/clean-machine/model checks that were not performed. Project license/SPDX choice is deferred by the user; do not infer one. Use the existing plain asyncio/assert Python test style. Tests must exercise behavior. Run focused tests during iteration and the full repository gate at integration boundaries.

## Task 1: PDF containment and launcher reliability

Status: implemented in local commit e8ad7dc. Focused PDF/launcher tests and full repository gate passed (2026-09-05, Python 3.12.14; HF_HUB_OFFLINE=1 prevents an uncached-model download). Limits cover cancellation, memory, output, page count, parser faults and descendant cleanup; this is resource containment, not a privilege sandbox.

Implement audit P0 item 1 and P1 item 4 launcher fix. Verify current upstream pypdf patch/advisories, upgrade to 6.16.2 or a verified compatible later patch with hashed lock regeneration preserving unrelated pins. Route all production untrusted PDF ingress (file_read, doc_digest, command artifact verification, public extraction entry) through killable bounded workers. Preserve PDFium primary/pypdf fallback and pagination. Enforce time, memory, page, and output bounds; ensure child cleanup on timeout, cancellation, crash, shutdown, and temporary-file removal. Test malformed/encrypted/textless/huge-page/output PDF and stalled worker cancellation, including direct file_read. Check DOCX external relationship behavior does not fetch remote content. Prefer local .venv Python and validate required packages rather than version alone; actionable errors, explicit override semantics, and paths with spaces. Read IPC/task-runtime/document design before cross-process edits. Update affected documentation. Package/profile consolidation comes in Task 2, so leave its ownership to that task.

## Task 2: One Python distribution and optional capabilities

Status: unified root distribution, uv.lock and profiles implemented. Fresh non-editable core (Python 3.12.14) and full (Python 3.13.12 selected by uv) installs passed imports, diagnostics, authenticated Brain, Voice and restart reconnect from unrelated Unicode/space paths. Full repository gate passed on 3.12.14. Core still has sqlite-vec transitively through the existing LangGraph SQLite checkpointer; fastembed/ONNX and document parsers are absent. No embedding model was downloaded. Python 3.13 full-suite support is not claimed from the install/lifecycle check alone.

Implement audit P1 items 4-5: root halo-local-assistant distribution containing brain and voice namespaces; one universal hashed production lock and one environment; commands halo brain and halo voice, retaining python -m development compatibility. Remove obsolete independent manifests/locks and manual cross-install setup, update all launch/CI/docs references. Base core dependencies plus core/documents/semantic/full extras (full selects both). Lazy format loaders: no document extras must still allow Brain startup and plain text; missing formats yield actionable installation errors. Advertise document/semantic capabilities honestly in diagnostics, with mirrored contract changes/tests if needed. Official release full assertion. Fresh core and full installs, both entry points, offline/no-model behavior, undeclared-import checks, lock drift, existing tests. Respect Task 1 worker entry points and packaging needs of spawned workers. Do not add a dependency manager/framework.

## Task 3: Self-contained desktop sidecar

Status: implemented in d4c5fea plus 630ba73; unsigned installer built, not
installed or published. The legacy read-only Git process now receives a
sanitized frozen-process environment. The full frozen profile check exercises
an authenticated Brain `file_read` PDF request, sanitized Git, Voice reconnect,
and Brain restart from the executable. The final backend and unsigned NSIS
installer were rebuilt and the final backend repeated the full profile check on
2026-09-17. External clean-machine/signing/antivirus acceptance remains open.

Implement P0 item 3 using one frozen Python executable with brain/voice mode; declare target-triple externalBin. Preserve existing Rust supervisor lifecycle and Windows Job Object ownership, hidden processes, restart ladder, shutdown ordering; source dev remains supported. Include native PDFium/sqlite-vec/ONNX/keyring resources and required full-profile packages. Handle multiprocessing.freeze_support correctly. Provide reproducible build scripts and CI artifact route, fail if a core-only build is selected. Test backend artifact startup/auth/Voice/restart/termination from a path with spaces and non-ASCII without source/Python lookup. Build actual Windows artifact if toolchain permits. Document signing, antivirus, clean-machine install/upgrade/uninstall, VC/WebView prerequisites and any checks unavailable here. Do not install/uninstall software or sign/publish releases without authority. Keep bundled user data, secrets, caches, logs and development paths out of artifacts.

## Task 4: Lexical memory baseline

Status: implementation and canonical memory/model/IPC docs in the worktree.
FTS migration rollback, live-set mutations, profile/vector preservation,
multi-batch rebuild/restart/concurrent edit, query bounds and offline integrity
checks pass. Actual pinned model download and cached-only runs pass the fixed
corpus smoke; all three semantic targets ranked first. Diagnostics compatibility
tests exposed and fixed omitted-field and recency-labelling bugs. Full gate
passed 2026-09-14 (94 UI tests, 13 Rust tests, all Python/Voice and phase gates).
Independent review required NFC normalization for decomposed-accent queries and
omitting last-retrieval mode before the first search. Both regressions now have
tests and fixes; the final integrated gate passed on 2026-09-17.

Implement P1 item 6: transactional SQLite FTS5/BM25 over live active beliefs, fallback for absent/unavailable semantic model. Preserve full-profile vector KNN ranking and embeddings across semantic off/on; dual-write and resumable/recoverable migration. No silent model download when offline is requested; pin/document embedding model identity, cache, license/checksum policy and reembedding. Honest active retrieval diagnostics. Behavioral tests: query escaping, Unicode/multilingual, punctuation/empty/very long inputs, phrases, empty index, archive/supersede/delete/update and restart/migration, fixed relevance corpus and semantic ranking regression.

## Task 5: Checkpoint adapter and conditional decision

Status: Option A implemented. `CheckpointStore` owns saver lifecycle, graph
compilation, state reads/updates, resume, interrupt discovery, retention and
schema validation. Focused checkpoint/graph/snapshot and Phase-2 restart tests
pass. Option B is deferred: replacing LangGraph still lacks a proven legacy
checkpoint converter, side-effect idempotency/rollback proof, and measured
startup/footprint benefit. The adapter is the future migration seam.

Implement P2 Option A: isolate all LangGraph checkpoint/interrupt access behind a H.A.L.O. adapter preserving pinned APIs and legacy checkpoints. Remove private thread/schema access only where supported APIs preserve lifecycle/performance; explicitly document necessary coupling. Compatibility tests cover pending approval restart, approve/deny/cancel/stale responses, queued tool IDs, multi-tool rounds, same-conversation serialization, concurrent conversations, recursion, partial stream failures, history/summaries/spend and snapshots. Gather ownership/startup/footprint evidence for Option B; make an explicit evidence-backed proceed/defer decision. The audit conditions removal on a proven conversion/rollback/idempotency migration; do not claim the existing graph already guarantees at-most-once across every side-effect boundary. If removal is not justified, record remaining migration acceptance work and keep adapter.

## Task 6: Dependency governance and release documentation

Status: implemented and locally verified. Compatible lock updates
cover React-family packages, Zustand, TanStack Virtual, Lucide, PDFium and
LangGraph while retaining major framework lines; direct PostCSS and now-unused
direct aiosqlite declarations are removed. CI matrices Python 3.11/3.12 and adds
lock drift, retried Python/npm audits, Cargo audit, CycloneDX inventories,
license-policy reporting and release artifact upload. Project licensing remains
explicitly deferred. Lock drift passed; Python audit found no vulnerability;
npm found no high-severity vulnerability (two moderate Vitest findings require
the deferred major); Cargo found no vulnerability and seven allowed warnings;
SBOM policy found no disallowed declaration or local path while reporting 84
unknown declarations for human review.

Implement P3: remove unused direct postcss; current compatible updates in isolated batches (React/ReactDOM, Zustand, TanStack Virtual, Lucide, PDFium, LangGraph), keeping major framework versions. Verify primary upstream sources and wheel/Python floor compatibility; preserve pins where upgrades cannot meet gates and record why. CI Python 3.11 and 3.12, native-wheel checks before 3.13. Keep pip/npm audits with retries and distinct unavailable verdict; add Cargo advisory checks, license metadata policy/unknown reporting, CycloneDX or SPDX SBOM/third-party notice generation for Python/npm/Cargo/native/model assets, lock drift. No invented project license; source README/contribution/security guidance may describe the deferred license truthfully. Generated outputs must exclude developer paths and credentials. Wire artifacts into release workflow without publishing. Run full gate and audit commands and report actual verdicts.

## Task 7: Integration review and evidence handoff

Status: local integration complete on 2026-09-17. The full repository verifier
passed (34 schemas, all Python/Voice suites, five UI self-checks, 94 UI tests,
production build, 13 Rust tests, Phase 0/1/2 gates). Isolated locked Python 3.11
full-profile imports passed. The final unsigned backend/installer built, the
final backend passed its full frozen process profile, and release SBOMs were
generated. Remaining work is external/human: clean-machine install lifecycle,
signing/SmartScreen/antivirus, native visual/NVDA, real-key walkthrough, and
third-party legal review. Branch is left unmerged and unpublished for review.

Read source audit acceptance list against final code. Run full repository verification, core/full clean install and frozen process checks supported by this machine; evaluate final branch with independent review and fix concrete regressions. Update canonical matched design/techstack docs, VERIFY.md and project memory with evidence and pending external checks. Report branch/worktree, complete/deferred/blocked criteria, audit availability and conditional framework decision. Leave branch for user review; no merge/push/release implied.
