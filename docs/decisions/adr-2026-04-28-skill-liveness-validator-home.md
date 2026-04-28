> **Navigation**: [Home](../INDEX.md) > [Decisions](README.md) > OMN-10180 Validator Home

# ADR: Skill Liveness Validator Home

## Document Metadata

| Field | Value |
|-------|-------|
| **Document Type** | Architecture Decision Record (ADR) |
| **Status** | 🟢 **ACCEPTED** |
| **Created** | 2026-04-28 |
| **Last Updated** | 2026-04-28 |
| **Author** | Codex (GPT-5) |
| **Related Issue** | `OMN-10180` |
| **Implementation Home** | `src/omnibase_core/validation/` |

---

## Executive Summary

The skill-backing-node liveness validator is owned by `omnibase_core`. That keeps reusable validator logic with the existing validation substrate, while `omniclaude` and `omnimarket` remain invocation and enforcement surfaces rather than the code home.

This ADR applies to the skill liveness validator surface only. It does not declare that every future validator must live in `omnibase_core`, but it does ratify `omnibase_core` as the correct owner for this cross-repo validator.

## Context

Two competing workspace plans placed the same validator in different homes:

- `docs/plans/2026-04-27-skills-to-market-phase-2-validator-gates.md`
- `docs/plans/2026-04-26-runtime-lifecycle-part-4-skill-shim-runtime-proof.md`

On 2026-04-28 the user direction corrected that ambiguity: implementation ADRs live in the owning repo, and the validator home for this surface is `omnibase_core`.

That direction is consistent with current repo precedent. `omnibase_core` already owns reusable validation surfaces such as:

- `src/omnibase_core/nodes/node_validator.py` (commit `2ddc0971`)
- `src/omnibase_core/mixins/mixin_node_type_validator.py` (commit `2ddc0971`)
- `src/omnibase_core/models/core/model_node_action_validator.py` (commit `2ddc0971`)
- `src/omnibase_core/validation/validator_runtime_profiles.py` (commit `2ddc0971`)

Putting the new validator in `omnimarket` or `omniclaude` would make a cross-repo rule look like a consumer-local utility. Putting it in `omnibase_compat` would blur compat DTO boundaries with validator ownership.

## Decision

The skill-backing-node liveness validator lives in `omnibase_core`, under the repo's existing validation/validator surface.

Execution surfaces remain split by audience:

- `omniclaude` invokes the validator in pre-commit for local author feedback.
- `omnimarket` invokes the validator in CI for shared enforcement.
- `omnibase_core` owns the validator implementation, typed inputs, and rule semantics.

The owning-repo ADR for this decision lives here in `omnibase_core`, not in `omni_home`, because the implementation and architectural ownership are both on the core side.

## Consequences

### Positive

- Validator ownership is aligned with the repo that already carries validation infrastructure.
- Cross-repo consumers share one implementation instead of growing repo-specific copies.
- The corrected plan expectation is explicit: code lives in `omnibase_core`, while pre-commit and CI remain downstream enforcement surfaces.

### Negative

- Downstream repos must integrate a validator they do not own, which adds coordination work for invocation wiring.
- Future validator proposals will still need an ownership decision; this ADR is scoped to the skill liveness surface only.

### Neutral

- Older workspace plans that proposed other homes should be treated as retired in favor of this repo-owned ADR.
- No backwards-compatibility shim is implied for alternate validator homes.

## Alternatives Rejected

### `omnimarket` as code home

Rejected because the validator is broader than a single consumer repo and should not be anchored to one CI surface.

### `omniclaude` as code home

Rejected because pre-commit is an invocation surface, not the correct architectural owner for reusable validator logic.

### `omnibase_compat` as code home

Rejected because compat should remain focused on DTOs and compatibility seams, not become a general validator bucket.

## References

- Workspace ADR source: `/Users/jonah/Code/omni_home/docs/decisions/adr-2026-04-28-skill-liveness-validator-home.md`
- Validation ownership precedent: `src/omnibase_core/nodes/node_validator.py` (commit `2ddc0971`)
- Validation ownership precedent: `src/omnibase_core/mixins/mixin_node_type_validator.py` (commit `2ddc0971`)
- Validation ownership precedent: `src/omnibase_core/models/core/model_node_action_validator.py` (commit `2ddc0971`)
