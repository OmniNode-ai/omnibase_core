<!-- onex-allow-file-todo-marker OMN-13480 reason="this provenance doc names the TODO/FIXME/HACK marker token as its subject; the tokens are not unfinished work" -->
# Unfinished-work-marker COMPUTE Validator — Generation Provenance (OMN-13480, G2 SEA-dogfood)

This package's scanning logic (`handler.scan_source`) is a **generated artifact** —
the "agent lands what SEA generated" step of the validator-standardization plan.
It was produced by the canonical generator `node_generation_consumer`
(`HandlerGenerationConsumer`, omnimarket), local-model-first through the real
delegation chain against the live model, and accepted **only** because it passed a
deterministic acceptance corpus
(`node_generation_consumer.validator_corpora.corpus_todo_marker.TODO_MARKER_CORPUS`)
in the hardened sandbox. This file is the durable evidence of that generation +
acceptance. The raw generation+acceptance JSON is committed in the omni_home
evidence tree at
`docs/evidence/2026-06-22-sea-dogfood-handler/todo-fixme-marker.generation.json`
(kept out of this package's scanned `src/` tree because its `handler_source` field
literally contains the marker tokens the scanner flags, and JSON cannot carry a
suppression comment).

## Generation run (live)

| Field | Value |
|---|---|
| correlation_id | `omn-13294-g2-todo-fixme-marker-ae6c296452de` |
| validator | `todo-fixme-marker` |
| provider | `local` |
| model_id | `Qwen3.6-35B-A3B` |
| routing_source | `contract` |
| endpoint_class | `local-coder` |
| resolved_endpoint | `http://192.168.86.201:8000/v1/chat/completions` (local-coder backend) | <!-- onex-allow-internal-ip OMN-13480 generation-evidence endpoint -->
| attempt_count | `1` (corpus-accepted on the FIRST attempt) |
| usage_source | `measured` (real provider-reported token usage) |
| contract_passed | `true` |
| corpus_checked | `true` |
| corpus_passed | `true` |
| corpus_errors | `[]` |
| violation_fixture_count | `5` |
| clean_fixture_count | `4` |
| accepted | `true` |
| generated_handler_hash | `sha256:dce4859ea5d1a512c54241b107a83f69b9fb6098809f989000cd004757371e88` |

The model was selected by the routing authority (contract `model_routing` +
bifrost delegation overlay keyed by `endpoint_class: local-coder`), not by the
generator — generation never selects its own model.

## Acceptance authority — the corpus, not the LLM

The generated scanner was accepted by `evaluate_corpus_acceptance` (OMN-13289, G0)
against a fixture corpus of **5 violation fixtures (3 adversarial mutation cases) +
4 clean fixtures (3 adversarial mutation cases)**, committed at
`omnimarket/.../node_generation_consumer/validator_corpora/corpus_todo_marker.py`.
The corpus is seeded from the hand-authored ground-truth invariant
`node_aislop_sweep._TODO_PATTERN` (`re.compile(r"\b(TODO|FIXME|HACK)\b")`): "an
agent-left unfinished-work marker in shipped source is work that must not merge
silently."

Acceptance = the generated scanner flagged **every** violation fixture and produced
**zero** findings on **every** clean fixture, by deterministic execution in the
hardened sandbox (no filesystem / network / env / `os` / `pathlib` reachable). The
boundary cases the clean fixtures pin: a marker token as an identifier SUBSTRING
(no word boundary on the uppercase token), the letters of the marker lowercase
inside `hackathon`, and the lowercase prose phrase "to do" (not the uppercase
marker).

```
corpus_checked: true   corpus_passed: true   corpus_errors: []
violation_fixtures: 5/5 flagged   clean_fixtures: 4/4 passed
```

### Re-run against the COMMITTED handler (verifier ≠ runner)

The committed `handler.scan_source` was re-run against the SAME omnimarket corpus
(`TODO_MARKER_CORPUS`) — the verifier is the corpus fixtures, the runner is the
landed handler:

```
violation_fixtures flagged: 5/5  (v-base-todo, v-base-fixme, v-mut-hack,
                                  v-mut-todo-no-colon, v-mut-fixme-bracketed)
clean_fixtures passed     : 4/4  (c-base-clean-code, c-mut-todo-substring,
                                  c-mut-hack-substring, c-mut-lowercase-prose)
errors: []   VERDICT: ACCEPTED
```

The raw generated `handle(input_data)` (623 chars) — committed verbatim in
`todo-fixme-marker.generation.json` — was *also* re-run through
`evaluate_corpus_acceptance` in the hardened sandbox: `checked=True passed=True`,
`5/5` violations flagged, `4/4` clean passed, `errors=[]`.

## Committed handler — a structured refactor of the generated logic

The model produced a word-boundary marker scan (`re.compile(r"\b(TODO|FIXME|HACK)\b")`
applied per line, returning `{'findings': [...]}`) — the right shape to flag a
standalone marker while excluding it as a substring of a larger identifier. The
committed `handler.scan_source` is a structured refactor of that generated logic:
it adds `line` / `marker` / `context` to each finding to match the canonical
finding shape, and adds line-level (`# onex-allow-todo-marker`) and file-level
(`# onex-allow-file-todo-marker`) escape hatches so ticket-referenced markers and
documentation-heavy source whose subject IS the marker token are not false-flagged.
Its verdicts are pinned to the acceptance corpus by the parametrized tests in
`tests/unit/validation/todo_marker/test_handler_todo_marker_compute.py`.

## Shadow-run — the gate runs clean on the files this PR touches

The COMPUTE validator was run over the in-memory bus against the PR's changed
source (`src/omnibase_core/validation/todo_marker/` + the constants topic block).
After annotating the validator's own documentation-heavy package files with the
file-level `# onex-allow-file-todo-marker` marker (their subject IS the marker
token), the gate is clean:

```
scanned: src/omnibase_core/validation/todo_marker/ + constants_event_types.py
exit=0   findings=0
SHADOW-RUN CLEAN on PR-changed source.
```

A full-tree census (`src/`) surfaces 81 pre-existing marker tokens in untouched
files — genuine ticket-referenced `TODO(OMN-XXXX)` debt and validator/contract
source whose subject IS the marker pattern (aislop rules, antipattern registry,
the merge/contract/receipt validators). These are NOT false positives: they are
real marker tokens in code the scanner correctly flags. The pre-commit hook is
`pass_filenames: true` and scans only STAGED files, so untouched pre-existing
markers do not block the repo at commit time — identical to how the G1 local-paths
and G2 private-IP canaries landed.

## Fail-closed proof (verifier ≠ runner)

The gate (the runtime, not a self-report) was run against a planted violation and
a reverted clean file:

```
# planted file content:
def handle():
    pass  # TODO: wire the projection consumer before merge

$ python -m omnibase_core.validation.todo_marker.runtime_todo_marker <plant>
<plant>:2: [TODO] pass  # TODO: wire the projection consumer before merge
1 unfinished-work-marker violation(s). ...
EXIT=1

# reverted (clean) file:
def handle():
    return resolve()
$ python -m omnibase_core.validation.todo_marker.runtime_todo_marker <clean>
No unfinished-work-marker violations found.
EXIT=0
```

A planted marker makes the gate exit non-zero; the revert restores green. The gate
BLOCKS.

## Required CI gate — enforcement, not detection (Rule 5)

The pre-commit hook (`check-todo-fixme-marker-compute`) is the binding local gate
(`--no-verify` is prohibited). To close the enforcement story so a pre-commit
bypass cannot land an agent-left marker, the SAME `HandlerTodoMarkerCompute` is
wired as a standalone CI workflow:

```
.github/workflows/validator-todo-marker.yml   (job: validate)
```

This mirrors the sibling generated validators (`validator-pin-hygiene.yml`,
`validator-no-none-guard-publish.yml`) one-for-one. The workflow runs on every
`pull_request` / `push` / `merge_group` against `main` / `develop` / `dev`:

1. **Verifier** — `pytest tests/unit/validation/todo_marker/` (the corpus-pinned
   parametrized tests are the acceptance authority; they fail first if the
   handler ever drifts off the corpus invariant).
2. **Enforcement** — runs `runtime_todo_marker` (the same in-memory-bus COMPUTE
   handler the pre-commit hook uses) over **only the files the PR changed**
   (diff vs base ref), excluding `tests/` + `docs/` (whose subject legitimately
   IS the marker token). Exit non-zero on any agent-left marker → the check
   fails.

The CI scan is intentionally changed-files-only (not a full `src/` scan): a
repo-wide blocking scan would fail on the legitimate pre-existing
ticket-referenced markers and validator/contract source whose subject IS the
marker pattern (the 66-token full-tree census above). Changed-files-only is the
exact STAGED-only semantics of the `pass_filenames: true` pre-commit hook, so
local and CI verdicts cannot drift. The CI scan command was proven fail-closed
on a planted marker (`EXIT=1`) before landing.
