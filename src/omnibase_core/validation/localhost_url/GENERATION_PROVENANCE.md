<!-- doc-content-file-ok reason="generation provenance: the IP literal is the live endpoint used during generation; evidence, not config" -->
# Localhost-URL COMPUTE Validator — Generation Provenance

This package's scanning logic (`handler.scan_source`) is a **generated artifact** —
a residual G2 mechanical scanner of the validator-standardization plan (§5 G2),
capturing the localhost-URL coverage item. It was produced by the canonical generator
`node_generation_consumer` (omnimarket), local-model-first through the real delegation
chain, and accepted **only** because it passed a deterministic acceptance corpus
(`node_generation_consumer.validator_corpora.corpus_hardcoded_localhost_url`) in the
hardened sandbox. This file is the durable evidence of that generation + acceptance.

## Generation run (live)

| Field | Value |
|---|---|
| correlation_id | `omn-13294-g2-hardcoded-localhost-url-3bb832ee2667` |
| provider | `local` |
| model_id | `Qwen3.6-35B-A3B` |
| routing_source | `contract` |
| resolved_endpoint | `http://<onex-host>:8000/v1/chat/completions` (local-coder backend) |
| attempt_count | `3` (corpus-accepted on attempt 3 via the repair loop) |
| usage_source | `measured` (real provider-reported token usage) |
| contract_passed | `true` |
| corpus_checked | `true` |
| corpus_passed | `true` |
| generated_handler_hash | `sha256:05dc63cf00b51a02754fd6968071f81aa8c7aa3ac81f9830fe549541971eec00` |

The model was selected by the routing authority (contract `model_routing` +
bifrost delegation overlay keyed by `endpoint_ref: local-coder`), not by the
generator — generation never selects its own model. The driver is committed at
`omnimarket/scripts/generation/drive_validator_generation.py`; the full
generation+acceptance JSON is committed at
`omnibase_core/docs/evidence/hardcoded-localhost-url.generation.json` (and
mirrored historically at `omnimarket/docs/evidence/hardcoded-localhost-url.generation.json`
from the original G2 batch).

Re-running the driver is deterministic at the acceptance level: same corpus + same
generated scanner ⇒ same verdict. This provenance reflects a fresh
2026-06-23 run of `drive_validator_generation.py --validator hardcoded-localhost-url`.

## Acceptance authority — the corpus, not the LLM

The generated scanner was accepted by `evaluate_corpus_acceptance` against a
fixture corpus of **5 violation fixtures (3 adversarial mutation cases) +
5 clean fixtures (3 adversarial mutation cases)**, committed at
`omnimarket/.../node_generation_consumer/validator_corpora/corpus_hardcoded_localhost_url.py`.
The corpus is seeded from the hand-authored ground-truth invariant
`node_aislop_sweep._HARDCODED_CONFIG_PATTERNS` (`http(s)://localhost`,
`http(s)://127.0.0.1`) and the CLAUDE.md "All URLs from contracts only" rule,
with the `# onex-allow-internal-ip` suppression marker named in CLAUDE.md Rule 6.

Acceptance = the generated scanner flagged **every** violation fixture and produced
**zero** findings on **every** clean fixture, by deterministic execution in the
hardened sandbox (no filesystem / network / env / `os` / `pathlib` reachable). The
boundary cases the clean fixtures pin: a PUBLIC host URL (`https://docs.omninode.ai/v1`),
a contract-sourced endpoint reference (no URL literal), the bare word `localhost` in
prose (not inside an `http(s)://` URL), a public host whose NAME merely CONTAINS the
substring `localhost` (`https://localhost-mirror.omninode.ai/v1`), and an
`onex-allow-internal-ip`-suppressed line.

```
corpus_checked: true   corpus_passed: true   corpus_errors: []
violation_fixtures: 5/5 flagged   clean_fixtures: 5/5 passed
```

## Committed handler — a structured refactor of the generated logic

The model produced a regex-and-boundary-check validator: an `https?://(localhost|127\.0\.0\.1)`
match with a trailing check that the loopback host is not the prefix of a longer
hostname (so `localhost-mirror` is excluded). The committed `handler.scan_source`
is a structured refactor of that generated logic: it expresses the host-boundary
constraint as a trailing negative lookahead `(?![\w.-])` on the host group (fixing
a latent bug in the generated draft, which read `source[host_end_index]` against the
whole text rather than the current line), scans strictly per-line, and adds
`line` / `column` / `host` / `matched_url` / `context` to each finding to match the
canonical finding shape used by the private-IP validator. A file-level
`onex-allow-file-internal-ip` escape hatch was added for documentation-heavy source.
Its verdicts are pinned to the acceptance corpus by the parametrized tests in
`tests/unit/validation/localhost_url/test_handler_localhost_url_compute.py`.

## Coverage rationale — not a duplicate of url-authority or no-env-fallbacks

This validator is the COMPLEMENT of the two pre-existing localhost-adjacent gates,
not a duplicate (verified empirically before authoring):

* `validator_url_authority` — its `public-https-literal` rule
  deliberately EXCLUDES localhost/loopback (it requires a dotted TLD), and its
  `url-const-assignment` rule only catches a loopback literal assigned to a
  `*_URL` / `*_ENDPOINT`-named constant. A loopback URL in any OTHER context — a
  call arg `client.connect("http://localhost:8000")`, a dict value, a list element,
  a non-URL-named variable, a function default — passes url-authority clean.
* `scripts/validate_no_env_fallbacks.py` — only catches the
  fallback/default idiom (`os.environ.get("X", "localhost...")`,
  `default="localhost..."`, `${VAR:-localhost}`). A plain module constant
  `BASE_URL = "http://localhost:8000/v1"` passes it clean.

Empirical proof: five hardcoded localhost URLs in non-`*_URL`-named contexts pass
BOTH existing validators clean. This validator flags ANY
`http(s)://localhost|127.0.0.1` literal regardless of context, closing the residual.

## Fail-closed proof (verifier ≠ runner)

The gate (the runtime, not a self-report) was run against a planted violation and a
reverted clean file; see the PR body for the captured `probe_stdout`. A planted
violation makes the gate exit non-zero with the specific error; the revert restores
green. The gate BLOCKS (no warn-only, no `--report`).
