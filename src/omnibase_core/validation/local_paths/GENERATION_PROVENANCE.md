# Local-Paths COMPUTE Validator — Generation Provenance

This package's scanning logic (`handler.scan_source`) is a **generated artifact**.
It was produced by the canonical generator `node_generation_consumer` (omnimarket),
local-model-first through the real delegation chain, and accepted **only** because
it reproduces the hand-authored ground truth
(`omnibase_core.validation.validator_local_paths`) across a deterministic fixture
corpus. This file is the durable evidence of that generation + acceptance.

## Generation run (live)

| Field | Value |
|---|---|
| correlation_id | `omn-13293-g1-96cb0e3cdf8d` |
| provider | `local` |
| model_id | `Qwen3.6-35B-A3B` |
| routing_source | `contract` |
| resolved_endpoint | `http://192.168.86.201:8000/v1/chat/completions` (local-coder backend) | <!-- onex-allow-internal-ip generation-evidence endpoint -->
| attempt_count | `1` (first-attempt success) |
| usage_source | `measured` (real provider-reported token usage) |
| contract_passed | `true` |
| corpus_checked | `true` |
| corpus_passed | `true` |

The model was selected by the routing authority (contract `model_routing` +
bifrost delegation overlay keyed by `endpoint_ref: local-coder`), not by the
generator — generation never selects its own model.

## Acceptance authority — the corpus, not the LLM

The generated scanner was accepted by `evaluate_corpus_acceptance` against a
fixture corpus of **14 violation fixtures (5 adversarial mutation cases) + 11
clean fixtures**. Every fixture's required verdict is **derived from the ground
truth** `validator_local_paths.py` (its regex patterns + `# local-path-ok`
suppression), so "violation"/"clean" provably means "what the ground truth says".
The corpus includes the two hard cases: the `# local-path-ok` suppression line and
`_SKIP_DIRS`-style content, plus near-miss tokens (`/usr/local/`, `/homelab/`,
bare `/Users` with no trailing segment, lowercase `/users/` in a URL).

Acceptance = the generated scanner flagged **every** violation fixture and
produced **zero** findings on **every** clean fixture, by deterministic execution
in the hardened sandbox (no filesystem / network / env / `os` / `pathlib`
reachable).

## Behavioral equivalence with the ground truth (DoD #8)

A verifier-≠-runner equivalence harness ran BOTH the generated scanner (in the
sandbox) AND the real `ValidatorLocalPaths` against **all 25 corpus fixtures**:

```
ground_truth_hash:      sha256:b97589b8b49ec33c82076fb15fd9ca7888817a7e5a338df9d47975b0cdf10b8b
generated_handler_hash: sha256:41cf72603cd28d70f0dc5c89858c2f1cfd72f02e8d7921f11bd7ef0b1cefaf87
fixtures_checked: 25 (violation=14, clean=11)
EQUIVALENCE PASSED: 0 mismatches.
```

The committed `handler.scan_source` is a structured refactor of the generated
logic (it adds line/column/pattern_name to each finding to match the ground
truth's finding shape); its verdicts are pinned to the ground truth by the
parametrized equivalence tests in
`tests/unit/validation/local_paths/test_handler_local_paths_compute.py`.

## Shadow-bake — zero false positives on real fleet code

Before flipping the gate to blocking, the COMPUTE validator was run against
**6,999 real fleet files** (core `src/` + omnimarket `src/`) and compared
file-by-file to the ground truth:

```
scanned_files=6999 ground_truth_flagged=3 compute_flagged=3
SHADOW-BAKE PASS: COMPUTE verdict == ground-truth verdict on every scanned file (0 mismatches).
```

## Cold-start benchmark (§7.9 HARD GATE)

The COMPUTE-over-in-memory-bus runner cold-start was measured against the direct
ground-truth script (3 runs each, single clean file):

| path | cold-start (s) |
|---|---|
| COMPUTE over in-memory bus | 1.03 / 1.05 / 1.10 |
| direct `validator_local_paths` script | 1.08 / 1.14 / 1.13 |

The bus path is **at or below** the direct-script time — both are dominated by
shared Python + pydantic import cost (~1.0s); the bus stand-up + dispatch
round-trip adds < 0.05s. The cold-start gate is satisfied; **no warmed/minimal
runtime profile is required** for the canary. A slow hook would drive
`--no-verify` (Rule 10) — it is not slow.

## Generated handler (verbatim, as produced by the model)

```python
import re

def handle(input_data):
    source = input_data.get('source', '')
    patterns = [
        re.compile(r'/Volumes/[A-Za-z][A-Za-z0-9_.\-]*/'),
        re.compile(r'/Users/[A-Za-z_][A-Za-z0-9_.\-]*/'),
        re.compile(r'/home/[A-Za-z_][A-Za-z0-9_.\-]*/'),
        re.compile(r'[Cc]:[/\\][Uu]sers[/\\]')
    ]
    findings = []
    for line in source.split('\n'):
        if 'local-path-ok' in line:
            continue
        for pattern in patterns:
            if pattern.search(line):
                findings.append({'line_content': line, 'pattern_matched': pattern.pattern})
                break
    return {"findings": findings}
```

## Integration problem surfaced (and fixed) by this dogfood run

The first live run failed 6/6 attempts with `security: hardcoded absolute path
detected`: the generator's own handler-security pre-filter
(`_HARDCODED_PATH_RE`) rejects any generated handler containing a quoted
`/Users`/`/Volumes`/... literal — but a hardcoded-path *detector* must embed
exactly those literals. The G0 acceptance test had only passed by assembling the
needle from string parts (`"/" + "Users"`), an obfuscation a real local model
does not produce. Fix: `node_generation_consumer._validate_generation` /
`_check_handler_security` are now corpus-aware — for a validator-generation run
(carrying a `validator_corpus`) the path-literal pre-filter is suppressed;
correctness is enforced by the corpus gate in the hardened sandbox. The topic
check stays unconditional. See the omnimarket producer PR for the associated
fix.
