<!-- onex-allow-file-topic-literal reason="this provenance doc names onex.* topic literals as its subject (the corpus fixtures the scanner flags); they are evidence, not contract drift" -->
<!-- doc-content-file-ok reason="generation provenance: the IP literal is the live endpoint used during generation; evidence, not config" -->
# Hardcoded-topic-string COMPUTE Validator — Generation Provenance

This package's scanning logic (`handler.scan_source`) is a **generated artifact** —
the "agent lands what SEA generated" step of the validator-standardization plan.
It was produced by the canonical generator `node_generation_consumer`
(`HandlerGenerationConsumer`, omnimarket), local-model-first through the real
delegation chain against the live model, and accepted **only** because it passed a
deterministic acceptance corpus
(`node_generation_consumer.validator_corpora.corpus_hardcoded_topic.HARDCODED_TOPIC_CORPUS`)
in the hardened sandbox. This file is the durable evidence of that generation +
acceptance. The raw generation+acceptance JSON (including the verbatim generated
`handle(input_data)` in its `handler_source` field) is committed at
`docs/evidence/hardcoded-topic-string.generation.json`.

## Generation run (live)

| Field | Value |
|---|---|
| correlation_id | `omn-13294-g2-hardcoded-topic-string-c16a083e1635` |
| validator | `hardcoded-topic-string` |
| provider | `local` |
| model_id | `Qwen3.6-35B-A3B` |
| routing_source | `contract` |
| endpoint_class | `local-coder` |
| resolved_endpoint | `http://<onex-host>:8000/v1/chat/completions` (local-coder backend) |
| attempt_count | `1` (corpus-accepted on the FIRST attempt) |
| usage_source | `measured` (real provider-reported token usage) |
| contract_passed | `true` |
| corpus_checked | `true` |
| corpus_passed | `true` |
| corpus_errors | `[]` |
| violation_fixture_count | `5` |
| clean_fixture_count | `4` |
| accepted | `true` |
| generated_handler_sha256 | `sha256:40091bee230431febeb0d9f506955c45e455e9d9eebc3e226548369b91ac51f2` |

The model was selected by the routing authority (contract `model_routing` +
bifrost delegation overlay keyed by `endpoint_class: local-coder`), not by the
generator — generation never selects its own model. The driver is
`omnimarket/scripts/generation/drive_validator_generation.py --validator
hardcoded-topic-string`, the SAME proven G1/G2 loop that landed the private-IP,
unfinished-work-marker, no-faked-boundary, and pin-hygiene validators this session.

## Acceptance authority — the corpus, not the LLM

The generated scanner was accepted by `evaluate_corpus_acceptance` against a
fixture corpus of **5 violation fixtures (3 adversarial mutation cases) +
4 clean fixtures (2 adversarial mutation cases)**, committed at
`omnimarket/.../node_generation_consumer/validator_corpora/corpus_hardcoded_topic.py`.
The corpus is seeded from the hand-authored ground-truth invariant
`node_aislop_sweep._HARDCODED_TOPIC_PATTERN` (`re.compile(r'"onex\.[a-z]+\.[a-z]+\.[a-z]')`):
"a quoted `onex.<a>.<b>.<c>` topic literal in handler source is a contract-drift
bug — topics must be declared in `contract.yaml` and resolved through it, never
pasted as a string literal" (omnimarket CLAUDE.md; memory `feedback_bus_is_the_transport`).

Acceptance = the generated scanner flagged **every** violation fixture and produced
**zero** findings on **every** clean fixture, by deterministic execution in the
hardened sandbox (no filesystem / network / env / `os` / `pathlib` reachable). The
boundary cases the clean fixtures pin: a two-segment `onex.core` string (BELOW the
`onex.<a>.<b>.<c>` topic shape), a non-`onex` four-segment `kafka.cluster.broker.id`
string (right shape, wrong prefix), a contract-resolved topic (no literal), and a
dotted python import path.

```
corpus_checked: true   corpus_passed: true   corpus_errors: []
violation_fixtures: 5/5 flagged   clean_fixtures: 4/4 passed
```

### Re-run against the COMMITTED handler (verifier ≠ runner)

The committed `handler.scan_source` was re-run against the SAME omnimarket corpus
fixtures (re-pinned verbatim in the unit test, since core ↛ market layering forbids
importing the omnimarket corpus) — the verifier is the corpus fixtures, the runner
is the landed handler:

```
violation_fixtures flagged: 5/5  (v-base-generation-topic, v-base-publish-call,
                                  v-mut-single-quote, v-mut-other-domain,
                                  v-mut-deeper-segments)
clean_fixtures passed     : 4/4  (c-base-contract-topic, c-base-module-path,
                                  c-mut-two-segment, c-mut-non-onex-prefix)
errors: []   VERDICT: ACCEPTED
```

## Committed handler — a structured refactor of the generated logic

The model produced a quoted-topic scan
(`(['"])onex\.[a-z0-9]+\.[a-z0-9]+\.[a-z0-9]+(?:\.[a-z0-9]+)*\1` applied per line,
returning `{'findings': [...]}`) — the right shape to flag a quoted
`onex.<a>.<b>.<c>` topic literal (≥3 segments) while a backreferenced closing quote
excludes mismatched-quote fragments. The committed `handler.scan_source` is a
structured refactor of that generated logic: it adds `line` / `topic` / `context`
to each finding to match the canonical finding shape, adds line-level
(`# onex-allow-topic-literal`) and file-level (`# onex-allow-file-topic-literal`)
escape hatches, and **drops the model's `re.IGNORECASE` flag** (onex topics are
lowercase by contract, matching the aislop ground truth and the corpus exactly).
Its verdicts are pinned to the acceptance corpus by the parametrized tests in
`tests/unit/validation/hardcoded_topic/test_handler_hardcoded_topic_compute.py`.

## Shadow-run — the gate runs clean on the files this PR touches

The COMPUTE validator was run over the in-memory bus against the PR's changed
source (`src/omnibase_core/validation/hardcoded_topic/` + the constants topic
block). After file-suppressing the canonical topic registry (`constants_event_types.py`)
and this validator's own documentation-heavy package files (their subject IS topic
literals), the gate is clean:

```
scanned: src/omnibase_core/validation/hardcoded_topic/ + constants_event_types.py
exit=0   findings=0
SHADOW-RUN CLEAN on PR-changed source.
```

## Pre-existing population — honest discovered-open finding (CI report-only)

A full-tree census (`src/omnibase_core/`) surfaces **32 pre-existing hardcoded
`onex.*` topic literals across 22 untouched files**. These are NOT handler-pasted
contract drift — they are legitimate **source-of-truth topic declarations**: the
canonical `topics.py` wire-topic registry, per-event `event_type=` / `*_EVENT`
constants in `models/events/`, and schema doc-examples (some already carrying the
old advisory `# onex-topic-doc-example` marker). Flipping the full-src CI self-scan
to BLOCKING before those are annotated with `# onex-allow-topic-literal` would
red-wedge the repo on day one.

Following the proven `no_faked_boundary` precedent (where the same graduated
roll-out was applied):

* The **pre-commit hook** (`check-hardcoded-topic-compute`) is **BLOCKING** with
  `pass_filenames: true` — it scans only STAGED files, so every NEW pasted topic
  literal is blocked at commit time; pre-existing untouched declarations do not
  block the repo (identical to how the G1 local-paths / G2 private-IP / unfinished-work-marker
  canaries landed).
* The **CI self-scan** (`validator-hardcoded-topic.yml`) lands **`--report-only`**
  for the burn-down: it prints the legacy SOT population but exits 0.
  Drop `--report-only` to flip to blocking once the population is annotated /
  reaches zero. The unit-test step (the corpus-acceptance proof) is fully BLOCKING.

The same handler runs under both surfaces, so local and CI verdicts cannot drift.

## Fail-closed proof (verifier ≠ runner)

The gate (the runtime, not a self-report) was run against a planted violation and
a reverted clean file:

```
# planted file content:
def handle():
    return bus.publish("onex.runtime.node.deploy.requested", env)

$ python -m omnibase_core.validation.hardcoded_topic.runtime_hardcoded_topic <plant>
<plant>:2: [onex.runtime.node.deploy.requested] return bus.publish("onex.runtime.node.deploy.requested", env)
1 hardcoded onex.* topic literal(s). ...
EXIT=1

# reverted (clean) file:
def handle():
    return bus.publish(self._contract.topics["deploy_requested"], env)
$ python -m omnibase_core.validation.hardcoded_topic.runtime_hardcoded_topic <clean>
No hardcoded onex.* topic-literal violations found.
EXIT=0
```

A pasted topic literal makes the gate exit non-zero; the revert restores green. The
gate BLOCKS (on staged files at commit time, and on any explicit scan target).
