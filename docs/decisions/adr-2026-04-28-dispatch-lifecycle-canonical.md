> **Navigation**: [Home](../INDEX.md) > [Decisions](README.md) > OMN-10180 Dispatch Lifecycle Canonical

# ADR: Dispatch Lifecycle Canonical Source

## Document Metadata

| Field | Value |
|-------|-------|
| **Document Type** | Architecture Decision Record (ADR) |
| **Status** | 🟢 **ACCEPTED** |
| **Created** | 2026-04-28 |
| **Last Updated** | 2026-04-28 |
| **Author** | Codex (GPT-5) |
| **Related Issue** | `OMN-10180` |
| **Canonical Model** | `src/omnibase_core/models/dispatch/model_dispatch_lifecycle_event.py` |

---

## Executive Summary

Typed lifecycle/FSM events are the canonical representation of dispatch lifecycle. In practice that means `ModelDispatchLifecycleEvent` in `omnibase_core` is the source of truth, while YAML or file-backed lifecycle records are projections and compatibility surfaces derived from those typed events.

This ADR ratifies the existing `omnibase_core` model home rather than relocating it. The decision is about ownership and canonical semantics, not about removing every downstream projection surface.

## Context

The current dispatch substrate work references two abstractions for the same lifecycle:

- typed lifecycle/FSM events via `ModelDispatchLifecycleEvent`
- filesystem or YAML lifecycle records used as sidecars, receipts, or compatibility projections

Without a declared canonical source, separate tickets can claim lifecycle correctness against different abstractions. That creates drift risk and makes it too easy to treat a local file artifact as authoritative proof instead of a projection of the actual lifecycle stream.

The current user direction resolves that ambiguity:

- implementation ADRs live in the owning repo
- `omnibase_core` is the canonical home for typed lifecycle/FSM events
- YAML or file-backed records are projections and compatibility surfaces

That direction matches the code already in place:

- `src/omnibase_core/models/dispatch/model_dispatch_lifecycle_event.py` defines `ModelDispatchLifecycleEvent` (commit `2ddc0971`)
- `src/omnibase_core/models/dispatch/model_lifecycle_chain.py` composes typed lifecycle chains from those events (commit `2ddc0971`)
- `tests/unit/models/dispatch/test_model_dispatch_lifecycle_event.py` exercises the state machine semantics (commit `2ddc0971`)

## Decision

Typed lifecycle/FSM events are canonical.

`ModelDispatchLifecycleEvent` in `omnibase_core` is the authoritative representation of dispatch lifecycle state and transition semantics. Any YAML, file-backed, or sidecar lifecycle record is a projection of terminal or intermediate lifecycle state, not the source of truth.

Concretely:

- lifecycle validity is defined by the typed event model and its state-machine rules
- projection writers must derive records from canonical typed events
- downstream repos may keep compatibility records, but those records must not redefine lifecycle semantics
- implementation ADR ownership for this surface remains in `omnibase_core`

## Consequences

### Positive

- One canonical lifecycle model defines accepted states, emitters, and transition semantics.
- Runtime, skill, and proof workflows can all point at the same typed surface when proving lifecycle behavior.
- Projection records remain useful without being allowed to silently fork the lifecycle contract.

### Negative

- Downstream code that treated file records as authoritative must be reframed around typed events first.
- Compatibility surfaces may require follow-up rename or cleanup work where older record types imply canonical ownership.

### Neutral

- YAML and file-backed lifecycle records may continue to exist as compatibility outputs, receipts, or derived views.
- This ADR does not bundle any downstream rename or migration work into `OMN-10180`; it only establishes canonical ownership and semantics.

## Alternatives Rejected

### Keeping YAML or file records as canonical

Rejected because a local record is too easy to self-attest and too weak to carry typed lifecycle semantics on its own.

### Creating a second canonical lifecycle home outside `omnibase_core`

Rejected because it would add indirection without improving ownership clarity or reducing drift.

### Treating typed events and projections as co-equal

Rejected because co-equal ownership leaves the same lifecycle open to inconsistent claims across tickets and repos.

## References

- Workspace ADR source: `/Users/jonah/Code/omni_home/docs/decisions/adr-2026-04-28-dispatch-lifecycle-canonical.md`
- Canonical model: `src/omnibase_core/models/dispatch/model_dispatch_lifecycle_event.py` (commit `2ddc0971`)
- Lifecycle chain model: `src/omnibase_core/models/dispatch/model_lifecycle_chain.py` (commit `2ddc0971`)
- State-machine tests: `tests/unit/models/dispatch/test_model_dispatch_lifecycle_event.py` (commit `2ddc0971`)
