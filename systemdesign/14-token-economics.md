# System Design: Token Economics & Tool Answerability

Status: **implemented.** This document records the current controls for keeping model turns answerable, bounded, and honestly metered. Document payload controls live in [13-document-ingestion](13-document-ingestion.md).

## Design objective

Token cost is the product of request count, tokens per request, and model price. Halo controls all three instead of relying on one context-size limit:

- tools must return the facts needed to answer the user's question;
- repeated or unproductive tool loops are bounded;
- old restorable tool payloads are projected as compact references;
- light-model routing is the default and escalation is one-shot;
- provider usage is accumulated across every model call and surfaced to the user.

## Answerable file discovery

`dir_list` and `file_search` return structured, valid JSON entries with name/path, directory flag, byte size, and modification time. Results are newest-first by default and capped by entry count, never by slicing serialized JSON in the middle of an object. A truncation marker states that more entries exist.

This makes requests such as “latest downloads” directly answerable. Read-only command aliases reuse the same formatter so an alternate path cannot silently discard timestamps.

## Per-turn loop controls

Each interactive turn maintains an in-memory tool-call ledger keyed by tool name plus canonical arguments.

- An identical read-only call is suppressed unless new state makes a retry meaningful.
- A configurable estimated-token budget stops additional model rounds before an accidental loop becomes an unbounded bill.
- Tool schemas remain stable within a turn so provider prefix caching is not defeated by volatile ordering.
- Task-shaped tools detach through [TaskRuntime](12-task-runtime.md); their streaming output uses bounded `task_log` tails instead of repeated model context.

Budget exhaustion produces an honest partial answer/error path. It never invents missing results and never silently continues on a more expensive model.

## Prompt projection

The checkpoint and reducer retain the full durable transcript. Before a provider request, older restorable tool results are replaced with byte-stable references that identify the tool, source, and returned size. The current tool round remains verbatim, and assistant tool-call/message pairs are never separated.

This is projection-time compression, not destructive history rewriting. The model can call the tool again with a narrower range when it genuinely needs the source material.

## Routing and escalation

The light model handles ordinary chat, classification, extraction, and deterministic preparation. A mid-stream failure may mark the next attempt for the heavy model, but `route_model` consumes that flag once and immediately resets it. Transport failure is therefore not a permanent per-conversation price upgrade.

## Usage and spend accounting

`brain/brain/llm.py` records OpenRouter usage for every request, including calls made by summaries, memory consolidation, and document digests. The shared usage accumulator adds rather than overwrites multi-round values:

- prompt tokens;
- completion tokens;
- cached prompt tokens when reported;
- reasoning tokens when reported; and
- provider-reported cost.

Every call also writes spend through the same store path. Conversation/session projections and durable monthly totals therefore draw from one accounting boundary instead of separate partial meters. `spend_update` exposes the available totals without treating a missing provider field as zero evidence.

## Document and memory boundaries

- `file_read` is format-aware, paginated, and capped.
- `doc_digest` maps bounded per-document extracts and reduces compact structured digests through TaskRuntime.
- Memory consolidation strips operational tool payloads before extraction and uses its own bounded prompt budget.
- SQLite FTS5 retrieval works without an embedding runtime; optional semantic search does not add a cloud token cost.

## Verification

Automated tests cover metadata ordering/caps, valid structured truncation, duplicate-call suppression, one-shot escalation, multi-round usage accumulation, cost persistence, prompt projection, document digestion, and contract synchronization. The full repository verifier exercises the integrated flows.

The remaining real-key check is empirical rather than architectural: compare a representative multi-round OpenRouter conversation with Halo's spend/tokens and record provider-specific cache/reasoning fields in `VERIFY.md`. Provider pricing and cache behavior can change, so documentation must not freeze an unverified price claim.

## Deliberate non-choices

Halo does not add LiteLLM, Langfuse, a hosted prompt proxy, `tiktoken`, semantic response caching, or another agent framework for these controls. The current implementation uses provider-reported usage, standard-library metadata/sorting, the existing store, and small per-turn data structures. Reconsider tool-schema search only if the active tool surface grows large enough for schema transmission to become a measured dominant cost.
