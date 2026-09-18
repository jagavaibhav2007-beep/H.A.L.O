# Halo — System Design: Overview

Companion to [Halo-PRD.md](../Halo-PRD.md). This folder holds one design doc per feature; this file is the backbone they all plug into. Tech choices live in [`../techstack/`](../techstack/00-stack-summary.md).

## Process model

Halo's process contract is **three resident processes** on the laptop plus local stores. The UI and Brain are functional today; the Voice process currently provides authenticated, reconnecting transport only, with its real audio pipeline scheduled for Phase 3c. Nothing is a server you dial into; it's an app.

```
┌────────────────────────── LAPTOP ──────────────────────────┐
│                                                             │
│  UI PROCESS ◄──WebSocket──► BRAIN PROCESS ◄──WS──► VOICE     │
│  Tauri+React               Python·LangGraph        WORKER    │
│  (glass UI, panels,        (control loop,          Python·   │
│   approval prompts)         router, gate,          transport │
│                             tools, memory)         today;    │
│                                                   audio 3c   │
│                                   │                          │
│              ┌────────────────────┼───────────────────┐      │
│              ▼                    ▼                    ▼      │
│   SQLite FTS5 + optional   skills/*.md         OS keystore    │
│   sqlite-vec               (self-made          (API keys)    │
│   (memory, tasks,           skills)                          │
│    activity log)                                            │
└─────────────────────────────────────────────────────────────┘
       │ cloud egress (only these leave the machine)
       ▼
  OpenRouter (LLM today; optional STT later) · future TTS/MCP · Codex/Claude CLIs
```

| Process | Responsibility | Talks to |
|---|---|---|
| **UI** | Render floating→expandable window and all panels; show approvals, activity feed, memory/task/skill views | Brain (WebSocket) |
| **Brain** | The agent. LangGraph control loop, model routing, permission gate, tool execution, memory, skills, task state | UI, Voice, OpenRouter, tools, MCP, CLIs |
| **Voice** | Today: authenticated sidecar transport and reconnect. Phase 3c: wake word → capture → STT → Brain → TTS with barge-in | Brain (WebSocket); future local/cloud speech providers |

Processes communicate over **local WebSocket** (loopback only). If Brain dies, UI shows "reconnecting" and Voice re-reads the new session endpoint before reconnecting. Utterance buffering begins with the real audio pipeline.

## The control loop (LangGraph)

Every task is a run through one graph:

```
perceive → route model → plan → [permission gate] → execute tool → checkpoint → narrate → loop → done
```

- **Checkpoint after every node**, persisted to SQLite. This is what makes tasks **resumable** and **interruptible** ("stop → what should I do differently? → resume from here").
- **`interrupt()`** is fired by the permission gate on Tier-3 actions and by an explicit user "stop." The graph suspends, state is saved, and it resumes on approval/redirect.

## Cross-cutting systems (each has its own doc)

| System | Doc | One-liner |
|---|---|---|
| Permission gate | [04-permissions](04-permissions.md) | Single choke point; Tier 3 → `interrupt()` |
| Memory | [03-memory](03-memory.md) | 3 tiers: session / curated beliefs / raw log; decay + auto-correct |
| Model router | see techstack | Light model default, escalate to heavy on reasoning gaps |
| Skill lifecycle | [08-self-improvement](08-self-improvement.md) | Planned: frequency → generate → sandbox-eval → activate/retire |
| Control lanes | [05-computer-control](05-computer-control.md) | Lane 1 implemented; Takeover/Sandbox planned |
| IPC contract & lifecycle | [11-ipc-contract](11-ipc-contract.md) | canonical WS schema, process launch/auth, concurrency, cancellation |

## Design principles

1. **One enforcement point, not scattered guards.** Permissions, model routing, and memory writes each have a single module every path routes through.
2. **Local-first data.** Only prompt text/audio and tool payloads leave the machine (to OpenRouter/Deepgram/MCP). Memory, logs, skills, keys stay on disk.
3. **Fast path by default.** Programmatic tools before GUI automation; light model before heavy; escalate only on a clear gap.
4. **Everything is inspectable.** Activity log, memory, and skills are all files/rows the user can view and undo/edit.

## Build status (from PRD §13)

1. **UI shell** — complete.
2. **Backend spine** — complete, including durable tasks, document ingestion, and memory retrieval.
3. **Heavy systems** — underway: managed-command and frozen-backend foundations are implemented; coding adapters, real voice, browser, GUI lanes, integrations, and self-improvement remain.
