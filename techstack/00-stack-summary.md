# Halo — Tech Stack Summary

The global stack. Per-feature files list only what's *specific* to that feature on top of this. Design lives in [`../systemdesign/`](../systemdesign/00-overview.md).

## Backbone
| Concern | Choice | Why (cheap / efficient / quality) |
|---|---|---|
| **App shell** | **Tauri** (Rust core + web UI) | ~10× lighter RAM than Electron; native tray + always-on-top windows; fits an always-resident app |
| **UI** | **React** + CSS (glassmorphism) | biggest component ecosystem for the premium look |
| **Brain** | **Python + LangGraph** | provider-agnostic agent loop; **checkpointer** = resumable tasks; **`interrupt()`** = Tier-3 gate for free |
| **Model access** | **OpenRouter** (one API key, many models) | provider-agnostic routing; per-task cost control |
| **Voice worker** | Python sidecar now; **Pipecat** local-audio pipeline planned for Phase 3c | authenticated/reconnecting transport is implemented; capture, STT, TTS, and barge-in are not yet |
| **Wake word** | **openWakeWord** (planned) | future on-device wake detection; a custom "Halo" model is required |
| **Memory store** | **SQLite FTS5/BM25** + optional **sqlite-vec** | always-available local lexical search; semantic KNN when the full profile is present |
| **Embeddings** | optional local **fastembed** (`BAAI/bge-small-en-v1.5`) | free/private semantic enhancement; lexical retrieval remains functional without it |
| **Browser** | **Playwright** over **CDP** → real Chrome profile | uses your logins; scriptable; reliable |
| **GUI automation** | **Windows UI Automation** (`pywinauto`/`uiautomation`) → **vision + `pyautogui`** fallback | element-based first, pixels only when forced |
| **Coding agents** | **Codex / Claude CLIs** as subprocesses | reliable Lane-1 orchestration, no cursor |
| **Secrets** | OS keystore (Windows Credential Manager via `keyring`) | no plaintext keys |
| **IPC** | local WebSocket (loopback) | simple, language-agnostic between the 3 processes |

## Models (OpenRouter) — verified 2026-07
| Role | Model ID | Status |
|---|---|---|
| **Heavy** (reasoning, code, planning) | `deepseek/deepseek-v4-pro` | ✅ confirmed on OpenRouter |
| **Light** (classify, narrate, memory extract) | `google/gemma-4-26b-a4b-it` | ✅ confirmed live on OpenRouter — **paid variant** ($0.06/M in, $0.33/M out), not the rate-limited `:free` |
| **STT (planned 3c)** | **faster-whisper** (local via CTranslate2) | pip-installable, MIT; future cloud fallback: OpenRouter Whisper |
| **TTS (planned 3c)** | **Kokoro** (local, 82M params real-time CPU) | Apache-2.0, hexgrad; future cloud fallback: Deepgram Aura |

## Cost strategy (from agentic-engineering skill)
- **Default light, escalate on gap.** Most calls (routing, narration, memory extraction, simple chat) → light model. Escalate to heavy only when the task shows real reasoning/coding depth.
- **Local where free:** wake word, embeddings, memory search, file ops, GUI, browser DOM reads — no API cost.
- **Browser: learn once, replay free.** A first encounter uses the Brain's own typed Playwright planning loop; the successful path is saved as a **playbook** and replayed via raw Playwright at **$0 LLM cost** thereafter, with light-model self-healing for one broken step. Accessibility-tree snapshots, not screenshots, are the default page representation. See [06-browser](06-browser.md).
- **Cloud only for:** LLM reasoning today (OpenRouter); optional STT/TTS fallback after Phase 3c; and user-enabled MCP/API services. These are the only planned recurring remote costs.

## What leaves the machine
Prompt text + tool payloads → OpenRouter; enabled MCP/API calls go to their services. **Everything else (memory, logs, skills, keys, and future local STT/TTS audio) stays local.** Cloud speech remains an explicit fallback after the local Phase 3c pipeline exists.
