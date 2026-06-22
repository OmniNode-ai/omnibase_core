# Generation Provenance — no-faked-boundary COMPUTE validator (OMN-13497)

This validator's scanning logic (`handler.scan_source`) was **generated**, not
hand-written. It was produced by `node_generation_consumer` (omnimarket) running
the REAL `HandlerGenerationConsumer` against the live local model, and accepted
ONLY because it passed a deterministic acceptance corpus in the hardened sandbox.
The corpus verdict — not the LLM's self-report — is the acceptance authority
(memory `feedback_adversarial_receipts`, OMN-13289).

## Run summary

| Field | Value |
|-------|-------|
| accepted | `true` |
| corpus_checked / corpus_passed | `true` / `true` |
| contract_passed | `true` |
| attempt_count | `9` |
| provider | `local` |
| model_id | `Qwen3.6-35B-A3B` |
| endpoint_class | `local-coder` |
| resolved_endpoint | the live local-coder backend on the `.201` server <!-- onex-allow-faked-boundary OMN-13497: provenance note --> |
| routing_source | `contract` (routing authority resolved provider/model/endpoint; the generator never selects its own model) |
| usage_source | `measured` |
| violation_fixtures | `8` (4 base + 4 adversarial mutation) — all flagged |
| clean_fixtures | `6` — all passed (0 findings) |
| correlation_id | `omn-13294-g2-no-faked-boundary-3957c068d7e5` |

Full provenance JSON (handler source + contract yaml + the above):
`docs/evidence/2026-06-22-omn13497-no-faked-boundary/generation.json`.

## What the corpus required

FLAG (violation) — a fake of the platform's OWN inference / routing / dispatch
boundary:

- a `Fake`/`Stub`/`Mock` class subclassing one of the boundary protocols
  (`*InferenceAdapter` / `*Bridge` / `*Router` / `*RoutingResolver` / `*Registry`
  / `*Dispatch*`), e.g. `class _FakeBridge(ModelInferenceAdapter):`;
- `patch("httpx.Client")` / `patch("httpx.AsyncClient")` around an inference call
  in a real-dispatch / golden-chain test;
- a `MagicMock()` / `AsyncMock()` assigned to an inference / bridge / router /
  dispatch target;
- an echo / prompt-derived fixture completion: `completion=prompt` or
  `completion=f"[recorded] {prompt}"`.

CLEAN (must NOT flag):

- a recorded-from-real replay adapter whose `completion` is a literal string;
- a real `RoutingResolvedJudgeInferenceAdapter(...)` usage;
- a real `EventBusInmemory()` real-resolution test;
- a legitimate mock / patch of a genuinely-external third-party service
  (`slack_sdk.WebClient`, `boto3.client`) that is NOT the platform's own
  inference / dispatch surface;
- a recorded literal completion whose prose merely contains the word "prompt".

## Acceptance authority

The corpus
(`omnimarket/src/omnimarket/nodes/node_generation_consumer/validator_corpora/corpus_no_faked_boundary.py`)
is the durable, committed evidence of what this validator was required to flag and
pass. A generation run is replayable: same corpus + same generated scanner =>
same verdict. The handler here was NOT hand-edited to force a pass — refinement
happened in the task description / corpus and the generator re-ran until the
corpus accepted attempt 9.
