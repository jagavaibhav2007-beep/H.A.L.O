# Tech Stack: Chat

Design: [systemdesign/01-chat](../systemdesign/01-chat.md). Global stack: [00-stack-summary](00-stack-summary.md).

## Feature-specific
| Concern | Choice |
|---|---|
| Turn orchestration | LangGraph graph run per turn |
| Checkpoint boundary | H.A.L.O. `CheckpointStore` adapter over pinned `langgraph-checkpoint-sqlite`; public saver APIs for lifecycle/state/resume, isolated validated SQL only for interrupt enumeration and retention |
| Streaming | token stream over local WebSocket → React |
| Markdown render | a React markdown renderer (client-side) |
| History handling | summarize-on-overflow (light model) into curated memory, not blind truncation |

The adapter is the migration seam if LangGraph checkpointing is replaced later.
Removing LangGraph is deferred: it currently owns graph execution, streaming,
interrupt/resume semantics, message reducers, and checkpoint serialization. A
replacement needs a versioned legacy-checkpoint converter, idempotency proof at
side-effect boundaries, rollback, and measured startup/footprint benefit first.

## Models
- **Default:** `google/gemma-4-26b-a4b-it` (light).
- **Escalate:** `deepseek/deepseek-v4-pro` when the router detects reasoning/coding/planning depth.

## Cost note
- Cheapest surface in the app — most turns are light-model only. Escalation is the exception, not the rule.
- No STT/TTS cost in text chat.
