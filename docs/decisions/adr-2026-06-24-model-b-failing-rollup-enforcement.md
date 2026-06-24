# ADR: Model B — Failing-Rollup Validator Enforcement (pilot: omnibase_core)

## Document Metadata

| Field | Value |
|-------|-------|
| **Document Type** | Architecture Decision Record (ADR) |
| **Status** | 🟢 **IMPLEMENTED (pilot)** |
| **Created** | 2026-06-24 |
| **Author** | ONEX Framework Team |
| **Related Issue** | OMN-13574 (pilot), epic OMN-13573; fleet rollout OMN-13576 |
| **Audit** | `docs/audits/2026-06-24-validator-enforcement-deficiency-audit/INDEX.md` |

---

## Context

`architecture-handshakes/validator-requirements.yaml` is the single source of
truth for which validators every repo must wire. Its consumer
(`validator_requirements_consumer.py`) proves each spec-required validator is
**present** — a matching pre-commit hook id, and a matching keyword somewhere in
`.github/workflows/*.yml`. Each repo also carries
`required_check_on_main` strings naming a granular branch-protection context per
validator (e.g. `"Quality Gate / ruff"`, `"AI Slop / check"`).

The 2026-06-24 enforcement-deficiency audit found two structural gaps:

1. **The granular `required_check_on_main` contexts do not exist in live branch
   protection.** omnibase_core's `dev` branch requires four aggregate rollup
   contexts: `CI Summary`, `verify / verify`, `gate / CodeRabbit Thread Check`,
   `call-reject-skip-token / scan / reject-skip-gate-token`. The per-validator
   contexts the spec names were never registered. The consumer never reads
   `required_check_on_main` at all, so this drift was invisible.

2. **"Present" is not "gating".** A repo can be handshake-clean while the single
   required rollup never actually depends on the job that runs a validator:
   - `naming-conventions` and `aislop-patterns` ran only in
     `omni-standards-compliance.yml`, which has **no aggregator job and is not in
     branch protection** — a real violation could not turn `CI Summary` red.
   - `pydantic-patterns` had **no real CI job at all**; the consumer's `pydantic`
     keyword matched incidental `pip install pydantic` lines in unrelated
     workflows.
   - `version-pin-check` was listed in `quality-gate.needs` but carried
     `continue-on-error: true`, so its failure could never propagate.

## Decision

Adopt **Model B**: keep **one** required aggregate rollup context per repo
(`CI Summary` for omnibase_core), but make that rollup **airtight** so it goes
red if *any* spec-required validator sub-job fails. Explicitly **reject Model A**
(registering granular per-validator contexts in branch protection): it inflates
the branch-protection surface that must be mutated through the gated path, and
the aggregate rollup is already a required check.

Three mechanisms enforce airtightness:

1. **The rollup transitively covers every spec-required validator.** Every
   spec-required validator that applies to omnibase_core now runs as a job in
   `ci.yml` (the workflow that emits `CI Summary`) and feeds
   `quality-gate → ci-summary`. New jobs added: `naming-conventions`,
   `pydantic-patterns`, `aislop-patterns`. `version-pin-check` was removed from
   `quality-gate.needs` because `continue-on-error: true` means it can never
   gate — keeping it in `needs` implied a gate it did not provide.

2. **A meta-check prevents silent drop.** `validator_rollup_coverage.py` parses
   the rollup workflow's `needs` graph and asserts the rollup job transitively
   depends on a real, non-`continue-on-error` job for every opted-in
   spec-required validator. It is wired as a pre-commit hook
   (`validate-rollup-coverage`) and a `check-handshake.yml` CI step.
   `tests/validation/test_validator_rollup_coverage.py` exercises the logic,
   including planted-failure cases (dropped need, `continue-on-error`, deleted
   job, drifted rollup name).

3. **Per-repo opt-in keeps the fleet safe.** A new additive top-level spec block
   `model_b_rollup_enforcement.repos` lists only the pilot (omnibase_core). The
   legacy consumer reads only `required_validators` + `known_repos` and ignores
   the new block, so the other 11 repos' `validate-validator-requirements`
   handshake is byte-for-byte unchanged. Fleet rollout is OMN-13576.

## Why Model B over Model A

- **Lower branch-protection surface.** Branch-protection mutations route through
  the gated node path; one required rollup is far less to manage and audit than
  ~18 granular contexts per repo.
- **The rollup is already required.** `CI Summary` already gates merge; the only
  defect was that it did not actually depend on every validator. Fixing the
  `needs` graph is strictly additive to existing infrastructure.
- **The meta-check closes the silent-drop hole** that made Model A's per-context
  registration attractive: a validator cannot be quietly removed from the rollup
  without a deterministic test going red.

## Consequences

- A real `naming-conventions`, `pydantic-patterns`, or `aislop-patterns`
  violation now turns `CI Summary` red on omnibase_core (previously it could not).
- `validator_rollup_coverage.py` must stay in sync with the spec's
  `validator_jobs` map; the meta-check test asserts the map references only real,
  applicable, `ci_workflow: required` validators.
- Grandfathered baseline gaps (e.g. `spdx-headers`, `stub-implementations`) are
  intentionally **not** asserted by the rollup verifier yet — they remain in
  `validator-requirements-baseline.yaml` as `MISSING_CI_WORKFLOW` and graduate
  into `validator_jobs` as their wiring lands.
- Fleet rollout (OMN-13576) adds the other 11 repos to
  `model_b_rollup_enforcement.repos`, each with its own rollup mapping.

## Verification

- `uv run python -m omnibase_core.validation.validator_rollup_coverage --repo omnibase_core --repo-root .`
  → `rollup-coverage: AIRTIGHT`.
- Planted-failure proof (no merge): `test_validator_rollup_coverage.py`
  `test_planted_dropped_need_is_detected` / `test_planted_continue_on_error_is_detected`
  fail-detect a dropped/swallowed covering job.
- Other-11-repos proof: the consumer's gap set is identical under the current
  main spec and this branch's spec for every other repo (additive top-level key
  only; `required_validators` byte-identical).
