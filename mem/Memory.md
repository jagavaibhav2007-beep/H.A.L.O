# Project Memory

_Current durable context only. Historical implementation detail belongs in Git history and the focused memory ledgers._

## Current state — 2026-09-18

- Phases 0, 1, and 2 are complete. Phase 3 is underway.
- The Phase 3a shared managed-command foundation is implemented. Thin Codex and Claude adapters are the next coding-orchestration tranche.
- Text chat, authenticated loopback IPC, permissions, activity/undo, memory consolidation, document ingestion, spend accounting, conversation history, and durable `TaskRuntime` execution are real.
- The Voice sidecar is authenticated and reconnects after Brain restarts, but audio capture, wake word, STT, TTS, and barge-in are not implemented yet.
- Browser automation, Windows GUI control, the governed self-improvement loop, MCP integrations, and per-client `stream_frame` subscriptions are not implemented.
- The floating companion capsule, in-place approval panel, batched task completion, and cooperative task cancellation are implemented and documented in the canonical `systemdesign/`, `ui_ux/`, and `VERIFY.md` files.

## Dependency and packaging baseline

- One root `pyproject.toml` and checked-in `uv.lock` define the Python distribution. The locked `core`, `full`, and `dev` profiles are checked by repository verification.
- Release packaging builds one frozen `halo-backend` executable with Brain, Voice, and isolated PDF-worker modes. Tauri uses source modules in development and the external binary in release packaging.
- PDF extraction is process-contained with bounded time, memory, output, and page limits. Frozen Git/command children sanitize PyInstaller DLL-path changes locally.
- Memory retrieval always has SQLite FTS5/BM25. `sqlite-vec` plus `fastembed` is an optional semantic layer; schema v6 maintains lexical indexes and vector-staleness bookkeeping.
- Dependency governance includes vulnerability/license checks, an allowlist with expiry/review metadata, third-party notices, SBOM generation, and release artifact verification. The final project-license choice and compatibility review remain deferred until the product is finished, by explicit user decision.

## Verification baseline

- The dependency/framework audit implementation passed the full repository verifier: Python and Voice suites, 34 IPC schemas, five UI self-checks, 94 Vitest tests, UI production build, 13 Rust tests, and Phase 0/1/2 gates.
- A fresh full-profile frozen backend and unsigned NSIS installer were built and profile-checked. Python 3.11 full-profile imports also passed.
- Human/native verification remains intentionally user-owned before commit: run the app, exercise representative chat/file/document/task/approval flows, and complete the relevant unchecked scenarios in `VERIFY.md`.

## Working situation

- Active implementation branch: `codex/dependency-framework-audit` in `.worktrees/dependency-framework-audit`.
- The dependency/framework work is committed through `495e785`; the final documentation cleanup is deliberately left uncommitted so the user can verify app functionality before committing.
- Do not merge, commit, push, or remove the worktree unless the user asks after verification.
- Preserve unrelated changes in the main checkout.

## Durable references

- Product behavior: `Halo-PRD.md`
- Current architecture: `systemdesign/`
- Concrete technology choices: `techstack/`
- Interaction design: `ui_ux/`
- Roadmap and implemented status: `phases.md`, `AGENTS.md`
- Verification evidence and remaining human checks: `VERIFY.md`
- Focused history: `mem/Bugs.md`, `mem/Decisions.md`, `mem/Patterns.md`, `mem/Gotchas.md`, `mem/MigrationLog.md`
