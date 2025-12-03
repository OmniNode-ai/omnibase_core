# v0.4.0 Architecture Refactor - Handoff Document

**Created**: 2025-12-03
**Target**: omnibase_core v0.4.0
**Status**: Planning Complete, Ready for Execution

---

## TL;DR

You're refactoring omnibase_core to separate legacy (mixin-based) nodes from declarative (pure) nodes. Legacy nodes move to `nodes/legacy/`, declarative nodes become the default. This enables the Runtime Host architecture in omnibase_infra.

**Duration**: ~26-35 days across 7 phases
**Issues**: 71 total (see MVP_PROPOSED_WORK_ISSUES.md)

---

## Key Documents

| Document | Purpose |
|----------|---------|
| `docs/MVP_PROPOSED_WORK_ISSUES.md` | Master plan with all 71 issues |
| `docs/architecture/CONTRACT_STABILITY_SPEC.md` | Contract versioning & fingerprint spec |
| `docs/PROJECT_REFACTORING_PLAN.md` | High-level architecture evolution |

---

## Execution Order

```
Phase 0: Stabilization (0.1-0.9)     ← START HERE
    ↓
Phase 1: Move legacy nodes (1.1-1.5)
    ↓
Phase 2: Promote declarative (2.1-2.7)
    ↓
Phase 3: Contract engine (3.1-3.11)  ← Highest risk
    ↓
Phase 4: Verify migration (4.1-4.7)
    ↓
Phase 5: Update tests (5.1-5.4)
    ↓
Phase 6: Documentation (6.1-6.6)
    ↓
Phase 7: CI enforcement (7.1-7.8)
    ↓
v0.4.0 RELEASE
```

---

## The 6 Invariants (Memorize These)

| ID | Name | One-Liner |
|----|------|-----------|
| INV-1 | Core Purity | No logging, caching, threading, or I/O in declarative nodes |
| INV-2 | Legacy Separation | Declarative ↔ legacy imports forbidden |
| INV-3 | Adapter Boundaries | Adapters don't call handlers, don't infer capabilities |
| INV-4 | Contract Stability | Fingerprints stable across Python versions |
| INV-5 | Cross-Repo | Core v0.4.0 ships before infra v0.1.0 |
| INV-6 | NodeRuntime | No concurrency primitives in core |

---

## What Changes

| Before (v0.3.x) | After (v0.4.0) |
|-----------------|----------------|
| `from omnibase_core.nodes import NodeCompute` | Same import, but gets declarative node |
| Mixin-based nodes with I/O | Pure nodes with handler injection |
| No contract fingerprints | All contracts fingerprinted |
| Implicit adapter behavior | Explicit adapter layer |

## What Does NOT Change

- `NodeCoreBase` interface (frozen)
- Contract YAML schema (backward compatible)
- Public API signatures (snapshot tested)
- SPI protocol surfaces

---

## High-Risk Items

| Risk | Phase | Mitigation |
|------|-------|------------|
| Contract validation bugs | 3 | Fuzz testing, >90% coverage |
| Adapter correctness | 3 | Round-trip tests, behavior equivalence |
| CI purity checks blocking PRs | 7 | CORE_PURITY_FAILURE.md documentation |
| Fingerprint instability | 3 | Cross-Python-version CI |

---

## Pre-Flight Checklist (Before Release)

```
CI Gates
[ ] mypy --strict passes
[ ] All purity AST checks pass
[ ] No omnibase_infra imports in core
[ ] No legacy imports outside nodes/legacy/

Coverage
[ ] Contract validator: >90%
[ ] Adapters (all 4): >90%
[ ] Overall: ≥60%

Behavior
[ ] Legacy vs declarative equivalence tests pass
[ ] SIMULATE_LEGACY_REMOVAL=true runs cleanly
[ ] All contracts have fingerprints

Cross-Repo
[ ] SPI protocol surfaces frozen
[ ] Infra team notified of adapter shapes
```

---

## Quick Commands

```bash
# Run all tests
poetry run pytest tests/

# Type check
poetry run mypy src/omnibase_core/

# Check for infra imports (should return nothing)
grep -r "from omnibase_infra" src/omnibase_core/

# Run with legacy removal simulation
SIMULATE_LEGACY_REMOVAL=true poetry run pytest tests/
```

---

## If You Get Stuck

1. **Purity check failing?** → See INV-1 in MVP doc, check for logging/caching/threading imports
2. **Fingerprint mismatch?** → Check CONTRACT_STABILITY_SPEC.md normalization pipeline
3. **Behavior equivalence failing?** → Check "Behavior Equivalence Rules" in MVP doc
4. **Cross-repo confusion?** → Look for 🔗 tags on issues (core+spi vs core+spi+infra)

---

## Next Session Prompt

Copy this to resume work:

```
Continue v0.4.0 refactor for omnibase_core.

Key docs:
- docs/MVP_PROPOSED_WORK_ISSUES.md (master plan, 71 issues)
- docs/architecture/CONTRACT_STABILITY_SPEC.md (fingerprint spec)
- docs/V040_HANDOFF.md (this handoff)

Current status: Planning complete, ready to execute Phase 0.

Start with Issue 0.1: Create pre-refactor API snapshot tests.
```

---

## Files Created This Session

| File | Lines | Purpose |
|------|-------|---------|
| `docs/MVP_PROPOSED_WORK_ISSUES.md` | ~2400 | Master plan with all issues |
| `docs/architecture/CONTRACT_STABILITY_SPEC.md` | ~260 | Contract versioning spec |
| `docs/V040_HANDOFF.md` | This file | Quick reference handoff |

---

**End of Handoff**
