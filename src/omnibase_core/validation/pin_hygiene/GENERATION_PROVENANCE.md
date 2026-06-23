# Generation Provenance — sibling-pin-hygiene COMPUTE validator (OMN-13509)

This validator's scanning logic (`handler.scan_source`) was **generated**, not
hand-written. It was produced by `node_generation_consumer` (omnimarket) running
the REAL `HandlerGenerationConsumer` against the live local model, and accepted
ONLY because it passed a deterministic acceptance corpus in the hardened sandbox.
The corpus verdict — not the LLM's self-report — is the acceptance authority
(memory `feedback_adversarial_receipts`, OMN-13289). This was the marquee
"omninode generates omninode" dogfood: the platform's own SEA generation node
produced the seed for its own pin-hygiene gate.

## Run summary

| Field | Value |
|-------|-------|
| accepted | `true` |
| corpus_checked / corpus_passed | `true` / `true` |
| contract_passed | `true` |
| attempt_count | `1` (first-pass) |
| provider | `local` |
| model_id | `Qwen3.6-35B-A3B` |
| endpoint_class | `local-coder` |
| resolved_endpoint | the live local-coder backend on the `.201` server |
| routing_source | `contract` (routing authority resolved provider/model/endpoint; the generator never selects its own model) |
| usage_source | `measured` |
| violation_fixtures | `7` (3 base + 4 adversarial mutation) — all flagged |
| clean_fixtures | `5` — all passed (0 findings) |
| correlation_id | `omn-13294-g2-pin-hygiene-8a87f3c07361` |

Full provenance JSON (handler source + contract yaml + the above) lives with the
omnimarket generation evidence for this ticket:
`omnimarket/docs/evidence/OMN-13509/pin-hygiene.generation.json`.

## What the corpus required

FLAG (violation) — a sibling git pin that is NOT an ancestor of the sibling's
`dev` HEAD:

- a `pyproject [tool.uv.sources]` `rev = "<sha>"` pin annotated
  `# pin-ancestry: orphan` (the commit diverged off the dev line);
- the same divergence in the PEP-508 `@<sha>` form and the uv.lock `?rev=<sha>`
  form (adversarial mutations — same divergence, different syntax);
- a `branch = "main"` sibling pin whose branch has diverged from dev
  (`# pin-ancestry: orphan`) — the literal #2071 shape;
- a pin whose ancestry could not be resolved (`# pin-ancestry: unknown`) — fail
  CLOSED, must flag.

CLEAN (must NOT flag):

- a sibling git pin in any syntax annotated `# pin-ancestry: ancestor`;
- a git pin for a NON-sibling package (out of scope, even when annotated orphan);
- a sibling pinned by a published version range (`omnibase-core>=0.44`), which is
  not a git pin at all.

## Hand-hardening of the corpus-accepted SEED

The generated artifact is a SEED, not drop-in. Two corrections were applied
against the real codebase (the seed passed the corpus but had a fail-OPEN hole
and a hallucinated module path):

1. **Fail-closed on a missing annotation.** The seed did
   `if not ancestry_match: continue` — silently SKIPPING a sibling git pin that
   carried no `# pin-ancestry:` annotation. That is fail-OPEN. The hardened
   handler treats a missing annotation on a sibling git pin as `unknown` and
   FLAGS it. (The corpus only fed annotated pins, so this gap could not be caught
   by corpus acceptance alone — exactly why a SEED needs hand-hardening.)
2. **Canonical placement + module path.** The seed's hallucinated
   `node_dependency_pin_ancestry_validator.models` module path was replaced by
   the canonical `omnibase_core.validation.pin_hygiene` layout (models / handler /
   runtime / `__init__`), the `onex-allow-pin-hygiene` suppression marker, typed
   Pydantic findings, and a deterministic source-order sort.

The git-ancestry resolution itself is NOT in the COMPUTE handler — it lives in
the EFFECT runner (`runtime_pin_hygiene.annotate_ancestry`), which runs
`git merge-base --is-ancestor` against the sibling's local canonical clone and
injects the `# pin-ancestry:` annotation. This is the honest division: git
resolution is an EFFECT, the verdict is a pure COMPUTE.

## Acceptance authority

The corpus
(`omnimarket/src/omnimarket/nodes/node_generation_consumer/validator_corpora/corpus_pin_hygiene.py`)
is the durable, committed evidence of what this validator was required to flag and
pass. A generation run is replayable: same corpus + same generated scanner =>
same verdict. The handler's scanning logic was generated; only the fail-closed
hardening and the canonical placement above were applied by hand.
