# Embedding model assets

The `semantic`/`full` Python profiles include the runtime, not model weights.
Brain startup and `halo diagnostics` do not download a model. The first actual
embedding request may download the pinned snapshot unless offline mode is set.
Failure leaves lexical memory available; initialization failure is memoized for
the process, so restart after repairing the cache or connectivity.

## Identity and integrity

| Field | Pinned value |
|---|---|
| FastEmbed model identity | `BAAI/bge-small-en-v1.5` |
| Hugging Face repository | `Qdrant/bge-small-en-v1.5-onnx-Q` |
| Snapshot revision | `52398278842ec682c6f32300af41344b1c0b0bb2` |
| Weights | `model_optimized.onnx` (about 66.5 MB) |
| Weights SHA-256 | `51f1bd0addd6e859e42c2c8021a5e5461385bb676a649f4b269aa445449f2431` |
| Vector size / intended language | 384 / English; model input limit 512 tokens |

The [upstream snapshot](https://huggingface.co/Qdrant/bge-small-en-v1.5-onnx-Q/tree/52398278842ec682c6f32300af41344b1c0b0bb2)
pins weights, config and tokenizer files together. The
[weights metadata](https://huggingface.co/Qdrant/bge-small-en-v1.5-onnx-Q/blob/52398278842ec682c6f32300af41344b1c0b0bb2/model_optimized.onnx)
provides the SHA-256 above. `brain.embedding` verifies this hash before model
construction and requires all four config/tokenizer files. Those auxiliary
files are revision-pinned, not separately hash-verified. A mismatch or incomplete
snapshot is rejected; there is no fallback to a moving `main` revision.

Upstream metadata is not a project license decision: the ONNX repository
declares Apache-2.0, while the installed FastEmbed registry labels the model
MIT. Preserve both source declarations in the asset inventory and resolve
redistribution notices before publishing weights. Project license selection
is explicitly deferred by the user; this document grants no license.

## Cache and offline operation

The default Hugging Face snapshot cache is `%LOCALAPPDATA%\Halo\models` on
Windows, with `HALO_MODEL_CACHE` as an explicit override. An exact snapshot in
the legacy temporary `fastembed_cache` is also reusable without moving or
deleting it. Model caches must not be swept into the desktop artifact.

- `HALO_SEMANTIC=off` disables vector loading and embedding requests.
- `HALO_SEMANTIC=offline`, `HALO_SEMANTIC_OFFLINE=1`, or `HF_HUB_OFFLINE=1`
  permits already cached, verified weights but forbids model downloads.
- Without an offline flag, a cache miss may fetch only the pinned snapshot.
  No model code is remotely executed: FastEmbed loads local ONNX assets.

## Repair and upgrade

Close Halo before maintenance. Back up `halo.db` before changing model identity.
Repair a corrupt/incomplete snapshot from the pinned upstream revision, then
restart the process; do not bypass checksum verification. Run
`halo memory-reindex` to fill missing/stale live-belief embeddings. Each row
commits separately, so a model failure retains prior progress and a retry skips
completed rows. Text changed while embedding is computed is skipped until the
next pass, never indexed under stale text.

For a model/revision change, update identity, hash and inventory together and
run `halo memory-reindex --all` with Halo closed. That flag starts a full pass
on every invocation; it is not a checkpointed model-conversion tool. Keep the
backup for rollback and do not serve mixed old/new model vectors during a
partial upgrade. Changing vector dimensionality additionally requires a
versioned schema migration; `--all` alone cannot do that. Merely switching a
profile off/on does not require a full re-embedding pass.

Verification on 2026-09-09 covers offline cache absence, pinned request
parameters, incomplete/tampered assets and synthetic-vector ranking/profile
preservation. `python shared/memory_model_check.py --allow-download` also fetched
and verified the actual pinned weights: three lexical queries and three
semantic paraphrase queries passed on an eight-belief fixed corpus (all intended
semantic results ranked first). Repeating without `--allow-download` passed
from the verified local cache. The checker uses a temporary database and an
ignored repository-local cache, never the user's database. This is a small
English relevance smoke test, not a general multilingual quality benchmark.
