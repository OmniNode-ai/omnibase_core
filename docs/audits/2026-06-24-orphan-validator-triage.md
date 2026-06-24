<!-- doc-content-file-ok OMN-13577 reason="validator-governance triage doc; OMN-XXXX ticket references and module-path examples are its load-bearing subject, not local-env leaks" -->

# Orphan-validator triage — OMN-13577

- **Ticket:** OMN-13577 (epic OMN-13573 — canonical validator governance)
- **Date:** 2026-06-24
- **Branch base:** `origin/dev` @ `be4f95460`
- **Scope:** governance-only triage of the "orphan" validators flagged by the
  2026-06-24 enforcement audit. SAFE SUBSET ONLY — delete the genuinely-dead
  modules, inventory the rest. **No spec / CI wiring changes** (those follow
  OMN-13574's Model B landing + OMN-13576; touching `validator-requirements.yaml`
  or `ci.yml` now would conflict with the in-flight PR #1327).

## What "orphan" means here

These modules were flagged as orphans because **none of them appear in the
`central_source` list of `architecture-handshakes/validator-requirements.yaml`**
(the canonical validator fleet spec). "Missing from the spec" is *not* the same
as "dead": a module can be wired via a remote pre-commit hook id, a dedicated CI
workflow, a console entry-point, package re-export, or library import without
ever being named in the spec. This triage separates the two.

## Method

For each module the four DEAD criteria were checked independently:

1. **hook** — defined in `omnibase_core/.pre-commit-hooks.yaml` and/or consumed
   by a `.pre-commit-config.yaml` (any of the 12 repos), by hook `id`.
2. **CI** — invoked by a `.github/workflows/*.yml` step (by module path or hook id).
3. **importer** — imported by non-test source anywhere (all repos), re-exported
   from a package `__init__.py`, or registered as a `pyproject.toml` entry-point.
4. **behavior test** — a test that exercises real module behavior.

A module is **DEAD** only when it has *no hook, no CI, no importer, and no
behavior test*. Wiring grep ran against 351 config files across all 11 local
repos (nested worktrees excluded). Independent corroboration via Repowise
`get_dead_code` (index age 0 days): its high-confidence zero-reference list
contains **none** of the modules below — every validator module is reachable in
its graph because they are `__main__`-invoked CLI entrypoints and/or carry
behavior-asserting tests.

## Result: NO modules safely deletable

Every flagged module carries at least one disqualifying live signal (consumed
hook, dedicated CI workflow, package re-export, console entry-point, library
import, or recently-landed feature scaffolding with a behavior test). Per the
task's explicit fallback, **only this inventory doc ships; zero modules deleted.**

---

## `src/omnibase_core/validators/` (14)

| Module | Status | Evidence | Recommendation |
|---|---|---|---|
| `backend_secret_discipline` | adopt-candidate | hook `backend-secret-discipline` consumed by omnibase_core/.pre-commit-config.yaml, omnibase_infra/.pre-commit-config.yaml, omnimarket/{.pre-commit-config.yaml,ci.yml}; CI `validator-backend-secret-discipline.yml` | OMN-13576: add to spec `central_source` |
| `breaking_schema_change` | adopt-candidate | hook `breaking-schema-change` consumed by omnibase_core/.pre-commit-config.yaml + ci.yml | OMN-13576: add to spec |
| `bypass_token_blocklist` | adopt-candidate | dedicated CI `validator-bypass-token-blocklist.yml` runs `python -m omnibase_core.validators.bypass_token_blocklist` (+ its test). Hook defined in `.pre-commit-hooks.yaml` but **not yet consumed** by any repo (workflow header notes pending fleet rollout) | OMN-13576: add to spec + finish pre-commit rollout |
| `contract_config_compliance` | adopt-candidate | hook `contract-config-compliance` consumed by omnibase_core/.pre-commit-config.yaml + ci.yml | OMN-13576: add to spec |
| `dispatch_surface_test_required` | adopt-candidate | hook `dispatch-surface-test-required` consumed by omnibase_core/.pre-commit-config.yaml + ci.yml | OMN-13576: add to spec |
| `dispatched_contract_operation` | adopt-candidate | hook `dispatched-contract-operation` consumed by omnibase_core/.pre-commit-config.yaml; CI `validator-dispatched-contract-operation.yml` | OMN-13576: add to spec |
| `gitignore_baseline` | adopt-candidate | hook `validate-gitignore-baseline` consumed by omnibase_core/.pre-commit-config.yaml; CI `validator-gitignore-baseline.yml` | OMN-13576: add to spec |
| `handler_di_gate` | adopt-candidate (defined, unconsumed) | hook `handler-di-gate` **exported** in `.pre-commit-hooks.yaml` (entry `python -m omnibase_core.validators.handler_di_gate`) but consumed by **no** repo; behavior test `tests/unit/validators/test_handler_di_gate.py`. Published infrastructure, not dead | OMN-13576: wire the exported hook into the fleet, then add to spec |
| `handler_github_token_env_reads` | library (COMPUTE form) | no hook, no CI, no non-test importer; **duplicate COMPUTE-node form** of the wired `validation/validator_github_token_env_reads.py` (which owns the `check-github-token-env-reads` entry-point + pre-commit hook). Landed in fleet-consolidation PR #1280 (OMN-13310) | KEEP; track convergence (canonical COMPUTE node vs procedural validator) under OMN-13573, do not delete in isolation |
| `no_plugin_daemon_classes` | adopt-candidate | hook `no-plugin-daemon-classes` consumed by omniclaude, omnibase_core, omnibase_infra, omnimarket pre-commit configs; CI omnibase_infra/ci.yml. Most-wired of the set | OMN-13576: add to spec (high priority — broad consumption already) |
| `operation_match_requires_operation` | adopt-candidate | hook `operation-match-requires-operation` consumed by omnibase_core, omnibase_infra, omnimarket; CI in all three (`validator-operation-match.yml`, ci.yml) | OMN-13576: add to spec |
| `publisher_injection_gate` | adopt-candidate (in-flight) | no hook def, no CI, no non-test importer; behavior test `tests/unit/validators/test_publisher_injection_gate.py`. **Landed 2026-06-16 (OMN-12881)** as a guardrail intended for wiring | KEEP; wire under OMN-13576. Recently-landed guardrail scaffolding, not dead debt |
| `skill_dispatch_receipt_mode` | adopt-candidate | hook `skill_dispatch_receipt_mode` consumed by omniclaude/.pre-commit-config.yaml; CI omniclaude/skill-receipt-mode-gate.yml; omniclaude test references the core module path | OMN-13576: add to spec |
| `transport_mock_lint` | adopt-candidate | hook `transport-mock-lint` consumed by omnibase_infra + omnimarket pre-commit configs; CI in both ci.yml | OMN-13576: add to spec |

## `src/omnibase_core/validation/validator_*.py` orphans (not in spec `central_source`)

Wired via dedicated CI workflow / consumed hook (adopt-candidates):

| Module | Evidence |
|---|---|
| `validator_canonical_inference` | CI `canonical-inference-gate.yml` in 5 repos + omnibase_core pre-commit |
| `validator_occ_merge_eligibility` | CI auto-merge.yml, occ-preflight.yml, receipt-gate.yml |
| `validator_receipt_gate` / `validator_receipt_gate_cli` | CI receipt-gate.yml |
| `validator_receipt_honesty` | CI receipt-honesty.yml in 6 repos + 2 pre-commit configs |
| `validator_requirements_consumer` | CI validate-validator-requirements.yml / check-handshake.yml in 8 repos (the spec consumer itself) |
| `validator_routing_authority` | CI omnimarket/ci.yml + pre-commit |
| `validator_runtime_profiles` | CI validator-runtime-profiles.yml in 5 repos + 2 pre-commit |
| `validator_transport_import` | omnibase_core pre-commit + omnimemory ci.yml |
| `validator_url_authority` | CI url-authority-gate.yml in 6 repos + pre-commit |
| `validator_node_purity` | omnibase_core pre-commit + omniintelligence/omnimemory ci.yml |
| `validator_banned_compose_vars` | CI validator-banned-compose-vars.yml |
| `validator_any_type`, `validator_base`, `validator_contract_linter`, `validator_local_paths`, `validator_pydantic_conventions`, `validator_topic_suffix` | consumed in omnibase_core (and omniclaude) pre-commit configs |

Library / entry-point (KEEP — not config-wired but live):

| Module | Status | Evidence |
|---|---|---|
| `validator_cli` | library | impl behind the `python -m omnibase_core.validation` CLI; imported by `cli/cli_commands.py` + `validator_cli_entry` |
| `validator_cli_entry` | library (entrypoint shim) | `python -m omnibase_core.validation.validator_cli_entry` module-run surface; re-exports `run_validation_cli`; behavior test present (no `validation/__main__.py`, so this is the module entrypoint) |
| `validator_demo_path_topic_coherence` | library (entrypoint) | `pyproject.toml` console-script `onex-demo-path-topic-gate` (OMN-12777) |
| `validator_github_token_env_reads` | library (entrypoint) | `pyproject.toml` console-script `check-github-token-env-reads` (OMN-13310) |
| `validator_skill_backing_node` | library (cross-repo) | consumed by omniclaude pre-commit hook `validate-skill-backing-node`, which delegates to `omnibase_core.validation.validator_skill_backing_node` (ADR-documented canonical home, OMN-10171) |
| `validator_protocol_patch` | library | defines `ProtocolPatchValidator` implemented by the wired `validator_contract_patch.py` (conformance asserted in tests) |
| `validator_migration_types` | library | imported by `models/validation/model_migration_plan.py`, `model_migration_conflict_union.py`, `services/service_protocol_migrator.py` |
| `validator_workflow` (+ `_step`, `_graph`, `_constants`) | library | re-exported from `validation/__init__.py`; the `_step`/`_graph`/`_constants` chain is imported by `validator_workflow` |
| `validator_architecture`, `validator_circular_import`, `validator_contract_patch`, `validator_contract_pipeline`, `validator_contracts`, `validator_fsm_analysis`, `validator_hardcoded_topics`, `validator_hex_color`, `validator_naming_convention`, `validator_patterns`, `validator_reserved_enum`, `validator_startup_contract`, `validator_types`, `validator_utils` | library | re-exported from `validation/__init__.py` (public package surface) |
| `validator_proof_tier_gate` | in-flight (KEEP) | exports `evaluate_proof_tier`; **no current importer** (the module docstring's "the gate, node_dod_verify... exercise this path" is aspirational), but **landed 2026-06-19 (OMN-13338)** as receipt-gate proof-tier scaffolding. Recently-landed feature code intended for wiring, not dead debt |

## Disposition

No module met the strict DEAD bar (no hook **and** no CI **and** no importer
**and** no behavior test) without a confounding live signal:

- `handler_di_gate` / `bypass_token_blocklist` — exported/CI'd hooks, just not
  yet fleet-consumed (published infrastructure).
- `publisher_injection_gate` / `validator_proof_tier_gate` — feature scaffolding
  landed in the last 8 days, intended for imminent wiring.
- `handler_github_token_env_reads` — intentional COMPUTE-node duplicate of a
  wired validator; convergence belongs to the canonical-form effort, not a
  drive-by delete.
- `validator_cli_entry` — the documented `python -m` module entrypoint.

Deleting any would remove advertised hook infrastructure, in-flight feature work,
or a CLI entrypoint — outside the "safe subset." **Follow-up (OMN-13576):** adopt
the adopt-candidates into `validator-requirements.yaml` `central_source` and
finish the pending pre-commit rollouts; revisit `handler_github_token_env_reads`
COMPUTE/procedural duplication under the OMN-13573 canonicalization effort.
