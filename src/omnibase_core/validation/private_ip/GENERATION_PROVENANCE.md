<!-- onex-allow-internal-ip OMN-13294: this provenance file's subject IS the private-IP validator; IP literals are intentional evidence (corpus invariants, planted violation proof, generation endpoint) -->
# Private-IP COMPUTE Validator — Generation Provenance (OMN-13294, G2)

This package's scanning logic (`handler.scan_source`) is a **generated artifact** —
the first G2 mass-produced mechanical scanner of the validator-standardization
plan (§5 G2). It was produced by the canonical generator `node_generation_consumer`
(omnimarket), local-model-first through the real delegation chain, and accepted
**only** because it passed a deterministic acceptance corpus
(`node_generation_consumer.validator_corpora.corpus_hardcoded_ip`) in the hardened
sandbox. This file is the durable evidence of that generation + acceptance.

## Generation run (live)

| Field | Value |
|---|---|
| correlation_id | `omn-13294-g2-hardcoded-private-ip-fb180d007325` |
| provider | `local` |
| model_id | `Qwen3.6-35B-A3B` |
| routing_source | `contract` |
| resolved_endpoint | `http://192.168.86.201:8000/v1/chat/completions` (local-coder backend) | <!-- onex-allow-internal-ip OMN-13294 generation-evidence endpoint -->
| attempt_count | `3` (corpus-accepted on attempt 3 via the repair loop) |
| usage_source | `measured` (real provider-reported token usage) |
| contract_passed | `true` |
| corpus_checked | `true` |
| corpus_passed | `true` |
| generated_handler_hash | `sha256:e2aa4c9ae0ab4da342b261f3e986a0928e55bb66759b4b828cb8ec497e4112e7` |

The model was selected by the routing authority (contract `model_routing` +
bifrost delegation overlay keyed by `endpoint_ref: local-coder`), not by the
generator — generation never selects its own model. The driver is committed at
`omnimarket/scripts/generation/drive_validator_generation.py`; the full
generation+acceptance JSON is committed at
`omnimarket/docs/evidence/OMN-13294/hardcoded-private-ip.generation.json`.

## Acceptance authority — the corpus, not the LLM

The generated scanner was accepted by `evaluate_corpus_acceptance` (OMN-13289, G0)
against a fixture corpus of **7 violation fixtures (4 adversarial mutation cases)
+ 5 clean fixtures (4 adversarial mutation cases)**, committed at
`omnimarket/.../node_generation_consumer/validator_corpora/corpus_hardcoded_ip.py`.
The corpus is seeded from the hand-authored ground-truth invariant
`node_aislop_sweep._HARDCODED_CONFIG_PATTERNS` (RFC1918 ranges `192.168.`, `10.`,
`172.16`–`172.31`) and the `# onex-allow-internal-ip` suppression marker named in
CLAUDE.md Rule 6.

Acceptance = the generated scanner flagged **every** violation fixture and produced
**zero** findings on **every** clean fixture, by deterministic execution in the
hardened sandbox (no filesystem / network / env / `os` / `pathlib` reachable). The
boundary cases the clean fixtures pin: a PUBLIC IP (`8.8.8.8`), a SemVer-shaped
token (`1.10.172.0`), a `172.15` address BELOW the `172.16`–`172.31` private band,
a contract-sourced endpoint reference (no IP literal), and an
`onex-allow-internal-ip`-suppressed line.

```
corpus_checked: true   corpus_passed: true   corpus_errors: []
violation_fixtures: 7/7 flagged   clean_fixtures: 5/5 passed
```

## Committed handler — a structured refactor of the generated logic

The model produced an octet-parsing RFC1918 validator (regex finds IPv4
candidates; octet logic decides private-band membership) — the right shape to
exclude version strings and public IPs that a naive prefix regex would mis-flag.
The committed `handler.scan_source` is a structured refactor of that generated
logic: it adds `line` / `column` / `rfc1918_block` / `context` to each finding to
match the canonical finding shape, and adds a file-level `onex-allow-file-internal-ip`
escape hatch for documentation-heavy source. Its verdicts are pinned to the
acceptance corpus by the parametrized tests in
`tests/unit/validation/private_ip/test_handler_private_ip_compute.py` (19 tests).

## Shadow-bake — zero false positives on real core code

Before flipping the gate to blocking, the COMPUTE validator was run against the
full `omnibase_core/src/` tree. The first pass surfaced **20 real private-IP
literals**, all documentation (docstring `>>>` examples, `Field(description=...)`
examples, the security model's own RFC1918 CIDR example data, and this validator's
own provenance/boundary docs). None were config leaks. Each legitimate site was
annotated at line level with `# onex-allow-internal-ip` (or, for documentation-
heavy files whose subject IS IP literals, the file-level `# onex-allow-file-internal-ip`);
two doc-example error/docstring strings were switched to the RFC5737 documentation
range (`192.0.2.x`, TEST-NET-1) which is the correct choice for illustrative IPs.
After annotation:

```
scanned: omnibase_core/src/   exit=0   findings=0
SHADOW-BAKE PASS: zero hardcoded private-IP findings on the clean core tree.
```

## Fail-closed proof (verifier ≠ runner)

The gate (the runtime, not a self-report) was run against a planted violation and
a reverted clean file:

<!-- onex-allow-internal-ip OMN-13294: fail-closed proof — planted violation examples are intentional evidence of what the validator flags -->
```
# planted file content:
BROKER_HOST = "192.168.86.201"

$ python -m omnibase_core.validation.private_ip.runtime_private_ip <plant>
<plant>:1:16: [192.168/16] '192.168.86.201'
  BROKER_HOST = "192.168.86.201"
1 hardcoded private-IP violation(s). ...
EXIT=1

# reverted (clean) file:
BROKER_HOST = resolve_endpoint("local-coder")
$ python -m omnibase_core.validation.private_ip.runtime_private_ip <clean>
No hardcoded private-IP violations found.
EXIT=0
```

A planted violation makes the gate exit non-zero with the specific error; the
revert restores green. The gate BLOCKS.

## Cold-start benchmark (§7.9 HARD GATE)

The COMPUTE-over-in-memory-bus runner cold-start was measured (3 runs, single clean
file): `3.95 / 2.02 / 1.27` wall-seconds, settling at ~1.3s once the import cache
is warm — the first run carries one-time `uv` resolution overhead. This is at the
same order as the G1 local-paths canary (~1.0s, both dominated by shared Python +
pydantic import cost). The cold-start gate is satisfied; no warmed/minimal runtime
profile is required, so the hook does not drive `--no-verify` (Rule 10).
