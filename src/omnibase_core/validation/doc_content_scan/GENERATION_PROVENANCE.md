<!-- doc-content-file-ok reason="this provenance file's subject IS the local-env traces / endpoint the doc-content validator scans for; the literals are intentional evidence" -->
<!-- onex-allow-file-internal-ip reason="this provenance documents the live generation backend endpoint; the IP literal is evidence, not config" -->

# Doc-Content COMPUTE Validator — Generation Provenance

This package's scanning logic (`handler.scan_source`) is a **generated artifact** —
a G2 mechanical scanner of the validator-standardization program. It was produced
by the canonical generator `node_generation_consumer` (omnimarket),
local-model-first through the real delegation chain, and accepted **only** because
it passed a deterministic acceptance corpus
(`node_generation_consumer.validator_corpora.corpus_doc_content_scan.DOC_CONTENT_SCAN_CORPUS`)
in the hardened sandbox. This file is the durable evidence of that generation +
acceptance.

## Generation run (live)

| Field | Value |
|---|---|
| correlation_id | `omn-13294-g2-doc-content-scan-437913c1133f` |
| provider | `local` |
| model_id | `Qwen3.6-35B-A3B` |
| routing_source | `contract` |
| resolved_endpoint | `http://192.168.86.201:8000/v1/chat/completions` (local-coder backend) | <!-- onex-allow-internal-ip generation-evidence endpoint -->
| endpoint_class | `local-coder` |
| attempt_count | `1` (corpus-accepted on the FIRST attempt — no repair loop needed) |
| usage_source | `measured` (real provider-reported token usage) |
| contract_passed | `true` |
| corpus_checked | `true` |
| corpus_passed | `true` |
| corpus_errors | `[]` |
| generated_handler_hash | `sha256:043a2aac4e52f92bdeaf76b94a7666238963f1e1169481d0451c7d77afcfd312` |

The model was selected by the routing authority (contract `model_routing` + bifrost
delegation overlay keyed by `endpoint_ref: local-coder`), not by the generator —
generation never selects its own model, and escalation to `cheap_cloud` (Gemini)
was authorized but not needed (first-attempt accept). The driver is committed at
`omnimarket/scripts/generation/drive_validator_generation.py` (the `doc-content-scan`
task description was added there); the full generation+acceptance JSON (including
the verbatim generated `handle(input_data)` source) is committed at
`omnimarket/docs/evidence/doc-content-scan.generation.json`.

## Acceptance authority — the corpus, not the LLM

The generated scanner was accepted by `evaluate_corpus_acceptance` against a
fixture corpus of **15 violation fixtures (9 adversarial mutation cases)
+ 13 clean fixtures (8 adversarial mutation cases)**, committed at
`omnimarket/.../node_generation_consumer/validator_corpora/corpus_doc_content_scan.py`.
The corpus is seeded from the hand-authored ground-truth invariant — the docs-facing
union of CLAUDE.md Rule 6 (no hardcoded LAN IPs / personal absolute paths) and the
knowledge-base sanitizer (strip ticket ids / IPs / `.201` / private URLs / e-mail) —
and the `doc-content-ok` / `doc-content-file-ok` suppression markers.

Acceptance = the generated scanner flagged **every** violation fixture and produced
**zero** findings on **every** clean fixture, by deterministic execution in the
hardened sandbox (no filesystem / network / env / `os` / `pathlib` reachable):

```
corpus_checked: true   corpus_passed: true   corpus_errors: []
violation_fixtures: 15/15 flagged   clean_fixtures: 13/13 passed
```

The boundary cases the clean fixtures pin: `localhost` / `127.0.0.1` (LEFT by
decision), the RFC5737 documentation IP ranges (`192.0.2.x` / `198.51.100.x` /
`203.0.113.x`), `example.com`, the portable env-var forms (`$OMNI_HOME` /
`${ONEX_HOST}` / `Path.home()`), a decimal token `$0.200` and a SemVer `v1.201.0`
(NOT a `.201`/`.200` host shorthand), the `doc-content-ok` suppression marker, and
the `OMNI_HOME` / `OMNINODE` tokens that are NOT the ticket-reference shape.

The corpus is a TEXT-only acceptance authority (the sandbox only ever sees
`input_data["source"]`, never a path). The **path-based** ticket-reference exemptions
(a file under `onex_change_control/` or `contracts/` keeps its ticket references)
are therefore proven by the transplanted `scan_source(content, path)` unit tests in
`tests/unit/validation/doc_content_scan/`, not by the text-only corpus.

## Committed handler — a structured refactor of the generated seed

The corpus-accepted seed was a self-contained `handle(input_data)` returning a
`{"findings": [...]}` dict (committed verbatim in the generation JSON). The
committed `handler.scan_source` is a structured refactor of that seed: it emits the
canonical `line` / `column` / `violation_type` / `matched_text` / `context` finding
shape (mirroring the sibling private-IP / hardcoded-topic validators), de-duplicates
to at most one finding per (line, class) in a stable source order, and adds the
PATH-based ticket-reference exemptions the text-only corpus could not express. The
`re` patterns are octet-parsed (LAN IP), guarded against digit-prefixed `.200`/`.201`
tokens (host shorthand), and bounded to standalone ticket-reference tokens (so
`OMNI_HOME` / `OMNINODE` never match). Verdicts are pinned to the acceptance corpus
by the parametrized tests in
`tests/unit/validation/doc_content_scan/test_handler_doc_content_scan_compute.py`.

## Sandbox builtin note

The hardened acceptance sandbox (`semantic_validation._SAFE_BUILTINS`) does NOT
expose `any()` / `all()`; the accepted seed used only explicit loops, and the
committed refactor follows the same constraint so the committed and generated logic
remain behaviorally equivalent under the same corpus.

## Gate wiring — deferred

This validator is PRODUCED and corpus-accepted; it is **NOT** wired as a blocking
gate here. The pre-commit hook + CI workflow wiring (and the shadow-bake over the
real docs tree) is tracked separately and deliberately deferred so no untested
validator is blanket-blocked. Nothing in `.pre-commit-hooks.yaml`,
`architecture-handshakes/validator-requirements.yaml`, or any CI workflow is changed
by the landing of this validator.
