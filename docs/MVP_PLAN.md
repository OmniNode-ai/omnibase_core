# MVP Proposed Work Issues - omnibase_core

**Repository**: omnibase_core
**Version Target**: v0.4.0 (Architecture Cleanup)
**Generated**: 2025-12-03 (v8 - Consolidated Architecture)
**Linear Project**: MVP - OmniNode Platform Foundation

---

## Executive Summary

### Current Status (as of 2026-01-01)

> **PROJECT STATUS**: The **MVP - OmniNode Platform Foundation** project is **COMPLETED** in Linear. Development has transitioned to the **Beta - OmniNode Platform Hardening** phase.

#### Linear Backlog Summary

| Project | Total | Done | In Review | In Progress | Backlog |
|---------|-------|------|-----------|-------------|---------|
| **MVP - OmniNode Platform Foundation** | 1 | 1 | 0 | 0 | 0 |
| **Beta - OmniNode Platform Hardening** | 88 | 42 | 3 | 6 | 25 |
| No Project (Projector Work) | 11 | 0 | 0 | 1 | 10 |
| **Total** | **100** | **43** | **3** | **7** | **35** |

#### MVP v0.4.0 Phase Completion Status

| Phase | Complete | Partial | Not Started | Total |
|-------|----------|---------|-------------|-------|
| Phase 0: Repository Stabilization | 9 | 0 | 0 | 9 |
| Phase 1: Legacy Node Migration | 5 | 0 | 0 | 5 |
| Phase 2: Declarative Node Promotion | 7 | 0 | 0 | 7 |
| Phase 3-7 | 36 | 0 | 0 | 36 |
| Future (F.5 RUNTIME_HOST) | 14 | 0 | 0 | 14 |
| **Total** | **71** | **0** | **0** | **71** |

> **UPDATE (2026-01-01)**: The MVP v0.4.0 milestone is **COMPLETE**. All 71 issues have been addressed. The project has transitioned to Beta - OmniNode Platform Hardening for type safety improvements and tech debt remediation.

**Key Completions (MVP)**:
- ✅ EnumNodeKind with RUNTIME_HOST value (PR #108)
- ✅ EnumHandlerType enum for protocol handlers
- ✅ ModelOnexEnvelope unified message format (PR #112)
- ✅ Core error hierarchy (RuntimeHostError, HandlerExecutionError, etc.)
- ✅ Contract Linter CLI (omniintelligence)
- ✅ Pre-refactor API snapshot tests (4 test files in `tests/unit/api_snapshots/`)
- ✅ NodeCoreBase interface frozen (interface tests + documentation)
- ✅ Issue 2.1: NodeReducerDeclarative renamed to NodeReducer (primary FSM-driven)
- ✅ Issue 2.2: NodeOrchestratorDeclarative renamed to NodeOrchestrator (primary workflow-driven)
- ✅ All handler protocols defined in omnibase_spi
- ✅ FileRegistry, NodeInstance, NodeRuntime, RuntimeHostContract implemented
- ✅ Runtime Host CLI command added

#### Beta Phase Active Work (2026-01-01)

**In Review (3)**:
- OMN-1178: [CORE] Remove `Any` from all mixins - PR #303
- OMN-1176: [CORE] Remove `Any` from models/container + models/configuration - PR #302
- OMN-1073: [Typing] Audit and reduce # type: ignore comments (277 occurrences)

**In Progress (6)**:
- OMN-1188: [CORE] Complete or remove stub implementations - PR #301
- OMN-1166: ModelProjectorContract & Schema Models - PR #296
- OMN-1113: [BETA] Manifest Generation & Observability
- OMN-1126: ModelContractPatch & Patch Validation
- OMN-1075: [Refactor] Replace generic Exception catches with specific types
- OMN-1021: refactor(semver): Replace local ModelSemVer with omnibase_core canonical version

**Recently Completed (Beta)**:
- OMN-1179: [CORE] Remove `Any` from utils + runtime + container - PR #300 ✅
- OMN-1177: [CORE] Remove `Any` from models/workflow + models/fsm + models/orchestrator - PR #298 ✅
- OMN-1157: [BETA] Hook Typing Enforcement Enablement - PR #297 ✅
- OMN-1156: ModelCapabilityMetadata & ServiceProviderRegistry - PR #295 ✅
- OMN-1155: ModelBinding & ServiceCapabilityResolver - PR #299 ✅
- OMN-1146: Contract Validation Event Schema - PR #293 ✅
- OMN-1117: Handler Contract Model & YAML Schema - PR #292 ✅
- OMN-1114: [BETA] Pipeline Runner & Hook Registry - PR #291 ✅
- OMN-549: Add SAFE_FIELD_PATTERN validation for injection protection ✅

### What v0.4.0 Changes
- **Legacy nodes HARD DELETED** (not moved to legacy namespace - decision changed due to no existing users)
- Declarative nodes become the ONLY exports (`NodeReducer`, `NodeOrchestrator`)
- Contract adapters and validators formalized
- Strict purity enforcement via CI

### What v0.4.0 Does NOT Change
- `NodeCoreBase` interface (frozen)
- Contract YAML schema (backward compatible)
- Public API signatures (snapshot tested)
- Cross-repo protocol surfaces in SPI

### Before You Start
- [ ] Read "Global Architectural Invariants" section
- [ ] Understand "Behavior Equivalence Rules"
- [ ] Review "Release Blockers" table
- [ ] Check cross-repo sync points if your issue is tagged with cross-repo impact

### Release Criteria
- [ ] All CI purity checks pass
- [ ] All behavior equivalence tests pass
- [ ] All contracts have fingerprints
- [ ] No infra imports in core
- [x] Legacy imports removed (hard deletion - no `nodes/legacy/` namespace exists)
- [ ] Contract validator + adapters have >90% coverage
- [ ] `SIMULATE_LEGACY_REMOVAL=true` runs cleanly

### High-Risk Items (Schedule Pressure)

| Item | Risk | Mitigation |
|------|------|------------|
| Contract validation engine | Complex logic, many edge cases | Start early, fuzz testing |
| Adapter correctness | Must match legacy behavior exactly | Behavior equivalence tests |
| CI purity checks | May block many PRs initially | Document failures clearly |
| Cross-repo synchronization | External dependencies | Explicit sync points |

### Priority Visual Legend

| Priority | Meaning |
|----------|---------|
| Urgent (1) | Release blocker, do first |
| High (2) | Important, schedule early |
| Medium (3) | Should complete before release |
| Low (4) | Nice to have, can defer |

---

## Overview

This document outlines proposed issues for the MVP milestone, derived from the architecture refactoring planning documents. Issues are organized by phase and priority.

> **Note**: For detailed architectural rules, see "Global Architectural Invariants" section below.

---

## Audience & Intent

**Intended audience**: Core maintainers and architectural contributors. External teams should treat this as internal planning and rely on `CLAUDE.md` + tutorials for implementation guidance.

**Document purpose**: This is a detailed refactor specification for the v0.4.0 architecture cleanup. It is NOT a user-facing guide.

---

## Global Architectural Invariants

> **Canonical Reference**: All phases and issues inherit these invariants. Do not restate them - reference this section.

### INV-1: Core Purity Rules

| ID | Rule | Rationale | Enforcement |
|----|------|-----------|-------------|
| P1 | No `import logging` in declarative nodes | Logging is infra concern | AST scan |
| P2 | No class-level mutable data | Immutability guarantee | AST scan |
| P3 | No caching or memoization | Non-determinism prevention | AST scan |
| P4 | Inheritance only from `NodeCoreBase` + `Generic` | No mixin pollution | AST scan |
| P5 | No handler type inspection | Use contract->adapter->handler pipeline | Code review |
| P6 | No contract mutation after construction | Read-only contracts | Code review |
| P7 | No top-level executable code | No import-time side effects | AST scan |
| P8 | No sys, asyncio loops, threading, multiprocessing, path ops | Pure computation only | AST scan |

### INV-2: Legacy vs Declarative Separation

| ID | Rule | Direction |
|----|------|-----------|
| S1 | Declarative MUST NOT import legacy | Never |
| S2 | Legacy MUST NOT import declarative | Never |
| S3 | Legacy MUST NOT import adapters | Never |
| S4 | External MAY import legacy with warning | Deprecated |

### INV-3: Adapter Boundaries

| ID | Rule | Rationale |
|----|------|-----------|
| A1 | Adapters MUST NOT call handlers | Return request models only |
| A2 | Adapters MUST NOT perform capability inference | Validator responsibility |
| A3 | Adapters MUST NOT transform data beyond structural mapping | No business logic |
| A4 | Adapters MUST NOT cache results | Infra concern |

### INV-4: Contract Stability

| ID | Rule | Rationale |
|----|------|-----------|
| C1 | Fingerprints stable across Python versions | Prevent hash drift |
| C2 | Fingerprint computed after normalization | Canonical ordering |
| C3 | Normalization: defaults -> remove nulls -> sort -> serialize | Reproducibility |
| C4 | Validators MUST NOT raise Pydantic exceptions directly | Wrap in declarative errors |

### INV-5: Cross-Repo Constraints

| ID | Rule | Scope |
|----|------|-------|
| X1 | Core v0.4.0 releases before infra v0.1.0 | Release gate |
| X2 | Handler protocols defined in SPI only | Single source of truth |
| X3 | No infra imports in core | Dependency direction |
| X4 | Core MUST NOT import SPI | Dependency direction |

### INV-6: NodeRuntime Constraints

> **Definition**: `NodeRuntime` refers to the planned pure orchestrator class in `omnibase_core` that coordinates node execution without owning an event loop. It is distinct from `RuntimeHostProcess` in `omnibase_infra` which provides scheduling and I/O. See Glossary for full definition.

| ID | Rule | Rationale |
|----|------|-----------|
| R1 | No scheduling or concurrency primitives | Lives in infra |
| R2 | No NodeInstance mutation after construction | Immutability |
| R3 | Adapters instantiated per invocation | No state leakage |

---

## Behavior Equivalence Rules

> **Migration Bar**: All phases must satisfy these equivalence rules. Reference as "See Behavior Equivalence Rules" rather than restating.

| Aspect | Definition | Tolerance |
|--------|------------|-----------|
| Output equivalence | Byte-for-byte identical JSON after serialization | None (exact match) |
| Error equivalence | Same error code and message structure | Field ordering may differ |
| State equivalence | Identical state machine transitions | Timing not compared |
| Non-deterministic cases | Seeded RNG or mocked randomness | Must produce identical results |

### Partial Contract Handling

| Scenario | Expected Behavior |
|----------|-------------------|
| Missing required field | `ContractValidationError` (both legacy and declarative) |
| Missing optional field | Silently use defaults (no warning) |
| Extra fields | Ignored silently (declarative) or INFO log (legacy) |

### Test Environment

| Environment | `SIMULATE_LEGACY_REMOVAL` | Use Case |
|-------------|---------------------------|----------|
| Legacy tests | `false` | Testing deprecated paths |
| Declarative tests | `true` and `false` | Verify isolation |
| Release validation | `true` | Must pass cleanly |

---

## Cross-Repository Contract Rules

> **CRITICAL**: These rules MUST be enforced throughout the refactoring.

| Rule | Description |
|------|-------------|
| SPI imports Core | `omnibase_spi` imports `omnibase_core` models at runtime |
| Core MUST NOT import SPI | No imports from `omnibase_spi` anywhere in `omnibase_core` |
| Core MUST NOT import omnibase_infra | No I/O dependencies in core |
| SPI MUST NOT define Pydantic models | All `BaseModel` definitions live in `omnibase_core` |
| Core MUST NOT include I/O handler implementations | All handlers live in infra |
| Declarative nodes MUST accept handler-protocol injections | Via constructor or method parameters |
| Legacy nodes MAY contain direct I/O | Until removal in v1.0.0 |
| Infra uses SPI + Core | `omnibase_infra` implements handlers using SPI protocols and Core models |

**Dependency Direction**:
```text
omnibase_infra  ──implements──►  omnibase_spi  ──imports──►  omnibase_core
     │                                │                            │
     │ (handlers, RuntimeHostProcess) │ (protocols only)           │ (models, NodeRuntime, pure logic)
     │                                │                            │
     └────────────────────────────────┴────────────────────────────┘
                    Infra uses both SPI protocols AND Core models
```

### Protocol Alignment with Runtime Host

> **IMPORTANT**: Handler protocols (`ProtocolHandler`, `ProtocolEventBus`, etc.) and event bus protocols are defined in `omnibase_spi` and must remain the single source of truth. This document must not redefine or contradict those protocol surfaces. See the `omnibase_infra` Runtime Host plan for implementation details.

> **NodeRuntime Constraints**: See INV-6 in "Global Architectural Invariants" section.

---

## v0.4.0 Non-Goals

The following are explicitly **out of scope** for v0.4.0:

| Non-Goal | Rationale |
|----------|-----------|
| No new I/O handlers in core | All handlers live in `omnibase_infra` |
| No new event bus implementations in core | Event bus is infra concern |
| No RuntimeHostProcess implementation in core | Lives in `omnibase_infra` |
| No direct Kubernetes/deployment concerns | Infrastructure layer only |
| No orchestrator event loop in core | Only pure orchestration logic; event loops live in infra |
| No Kafka/message broker implementations | Transport layer lives in infra |

---

> **Core Purity Rules**: See INV-1 in "Global Architectural Invariants" section.

> **Legacy vs Declarative Separation**: See INV-2 in "Global Architectural Invariants" section.

---

## Summary Statistics

| Phase | Issue Count | Priority | Duration |
|-------|-------------|----------|----------|
| Phase 0: Repository Stabilization | 9 | CRITICAL | 3-4 days |
| Phase 1: Legacy Node Migration | 5 | HIGH | 3-4 days |
| Phase 2: Declarative Node Promotion | 7 | HIGH | 3-4 days |
| Phase 3: Contract Adapters & Validators | 11 | HIGH | 5-6 days |
| Phase 4: Migration Verification Tests | 7 | HIGH | 3-4 days |
| Phase 5: Test Updates | 4 | MEDIUM | 3-4 days |
| Phase 6: Documentation | 6 | MEDIUM | 2 days |
| Phase 7: Deprecation & CI | 8 | MEDIUM | 3 days |
| Future: Mixin Migration | 4 | LOW | - |
| Future: Runtime MVP | 6 | LOW | - |
| Future: Developer Tooling | 4 | LOW | - |
| **Total** | **71** | - | ~26-35 days |

## Phase Classification

| Phase | Primary Focus | Secondary Focus |
|-------|---------------|-----------------|
| Phase 0 | Core purity & structure | RuntimeHost readiness |
| Phase 1 | Core purity & structure | - |
| Phase 2 | Core purity & structure | RuntimeHost readiness |
| Phase 3 | RuntimeHost readiness | Core purity & structure |
| Phase 4 | Core purity & structure | - |
| Phase 5 | Core purity & structure | - |
| Phase 6 | Documentation | - |
| Phase 7 | Core purity & structure | RuntimeHost readiness |

> If v0.4.0 timeline slips, **RuntimeHost readiness** items can be deferred while **Core purity & structure** items remain blocking.

---

## Coverage Policy for v0.4.0

| Component Type | Minimum Coverage | Rationale |
|----------------|------------------|-----------|
| Adapters (`adapters/`) | >90% | Critical transformation logic |
| Validators (`validation/`) | >90% | Contract correctness is foundational |
| Error classes (`errors/`) | >90% | Error handling must be comprehensive |
| Legacy compatibility shims | >=60% | Lower risk, being deprecated |
| Test infrastructure | >=60% | Supporting code |

**Default**: All new code must meet >=60% coverage (configured in `pyproject.toml`).

---

## API Stability Contract

Defines which modules are public, semi-public, or internal for v0.4.0.

### Public API (Stable)

These modules have **stable** signatures. Breaking changes require major version bump.

| Module | Stability |
|--------|-----------|
| `omnibase_core.nodes` | Stable |
| `omnibase_core.models.contracts.*` | Stable |
| `omnibase_core.errors` | Stable |
| `omnibase_core.adapters` | Stable |
| `omnibase_core.services.service_contract_validator` | Stable |

### Semi-Public (Use with Caution)

May change in minor versions. Document usage if depending on these.

| Module | Notes |
|--------|-------|
| `omnibase_core.infrastructure.*` | Base classes may evolve |
| `omnibase_core.utils.*` | Helper functions may change |
| `omnibase_core.mixins.*` | Being deprecated |

### Internal (Subject to Change)

**Do not depend on these** outside of `omnibase_core`.

| Module | Reason |
|--------|--------|
| `omnibase_core._internal.*` | Implementation details |
| `omnibase_core.*.impl_*` | Private implementations |

> **Note**: The originally planned `omnibase_core.nodes.legacy.*` namespace was never created. Legacy nodes were hard deleted in v0.4.0 due to no existing users.

---

## Minimal Contract Templates

These are the smallest valid contracts for each node type. Use as reference when implementing adapters and validators.

### Minimal Compute Contract
```yaml
type: compute
version: "0.4.0"
name: "identity"
input:
  type: object
  properties:
    value: { type: string }
  required: [value]
output:
  type: object
  properties:
    result: { type: string }
  required: [result]
```

### Minimal Effect Contract
```yaml
type: effect
version: "0.4.0"
name: "log_message"
effect_type: log
input:
  type: object
  properties:
    message: { type: string }
  required: [message]
capabilities: [logging]
```

### Minimal Reducer Contract (Smallest FSM)
```yaml
type: reducer
version: "0.4.0"
name: "toggle"
initial_state: "off"
states: [off, on]
transitions:
  - from: off
    event: toggle
    to: on
  - from: on
    event: toggle
    to: off
```

### Minimal Orchestrator Contract (Smallest DAG)
```yaml
type: orchestrator
version: "0.4.0"
name: "single_step"
steps:
  - name: step1
    node: some_compute_node
    depends_on: []
```

---

## Reference Documents

- `docs/PROJECT_REFACTORING_PLAN.md`
- `docs/ARCHITECTURE_EVOLUTION_OVERVIEW.md`
- `docs/MIXIN_MIGRATION_PLAN.md`
- `docs/MINIMAL_RUNTIME_PHASED_PLAN.md`
- `docs/DEPENDENCY_REFACTORING_PLAN.md`
- `docs/architecture/CONTRACT_STABILITY_SPEC.md` - Contract versioning and fingerprint specification

---

## Deprecation Timeline (Cross-Repository)

| Version | omnibase_core | omnibase_spi | omnibase_infra | omniintelligence |
|---------|---------------|--------------|----------------|------------------|
| v0.3.x | Current state | Current state | Current state | Current state |
| v0.4.0 | Legacy nodes deprecated | Handler protocols added | Handlers implemented | Updated imports |
| v0.5.0 | Deprecation warnings as errors | Stable | Stable | Migration complete |
| v1.0.0 | Legacy nodes removed | Stable | Stable | Stable |

### Version Advancement Signals

**Before advancing to v0.5.0**:
- [ ] `SIMULATE_LEGACY_REMOVAL=true` must run cleanly (Issue 7.7)
- [ ] All deprecation warnings converted to errors in test suite
- [ ] No consumer repos using legacy imports without explicit opt-in

**Before advancing to v1.0.0**:
- [ ] All legacy nodes removed from codebase
- [ ] All `__getattr__` compatibility shims deleted
- [ ] All deprecated import paths removed
- [ ] Cross-repo migration verified (omniintelligence, etc.)

---

## Cross-Repo Synchronization Points

### Blocking Dependencies

| Core Phase | Blocks Infra? | Synchronization Gate |
|------------|---------------|----------------------|
| Phase 2 (handler capability mapping) | Yes | Infra cannot define handlers until capabilities are defined |
| Phase 3.1-3.4 (adapter request models) | Yes | Runtime Host cannot process requests until models are stable |
| Phase 3.7 (fingerprint specification) | Yes | Infra logging/tracing depends on fingerprint format |
| Phase 4 (migration verification) | Yes | Infra integration tests require stable core |

### Release Sequencing Rule

> **CRITICAL**: `omnibase_core` v0.4.0 MUST be cut and released **before** `omnibase_infra` v0.1.0 Runtime Host implementation begins. No exceptions.

### SPI/Core Synchronization

| Sync Point | SPI Change | Core Change | When |
|------------|------------|-------------|------|
| Handler capabilities | `ProtocolHandler` capability enum | `EFFECT_CAPABILITIES` constants | After Issue 2.7 |
| Request models | Handler request protocols | Adapter output types | After Issues 3.1-3.4 |
| Fingerprint format | Contract metadata protocol | Fingerprint generator | After Issue 3.7 |

---

## Repository Source of Truth

| Component | Repository | Notes |
|-----------|------------|-------|
| Protocols (ProtocolHandler, etc.) | `omnibase_spi` | Single source of truth for interfaces |
| Contract models | `omnibase_core` | Pydantic models for node contracts |
| Adapters | `omnibase_core` | Pure transformation from contract to request |
| Validators | `omnibase_core` | Contract validation logic |
| Error taxonomy | `omnibase_core` | Declarative error classes |
| Handlers | `omnibase_infra` | Protocol implementations with I/O |
| Runtime Host | `omnibase_infra` | Event loop, scheduling, orchestration |
| Event Bus | `omnibase_infra` | Message transport implementation |

---

## CI Enforcement Overview

All CI checks must pass before cutting v0.4.0. This table consolidates CI-related tasks across phases:

| Check Name | Scope | Issue | Phase | v0.4.0 Blocker? |
|------------|-------|-------|-------|-----------------|
| Import violation check | No `omnibase_infra` imports in core | 0.4 | 0 | Yes |
| Purity AST check | No I/O in declarative nodes | 0.8 | 0 | Yes |
| Strict typing (`mypy --strict`) | All source files | 7.3 | 7 | Yes |
| Architectural violations | No legacy symbols in declarative namespace | 7.4 | 7 | Yes |
| Pure node linter | No `Any`/`Dict[Any]` in declarative nodes | 7.6 | 7 | Yes |
| Snapshot tests | API stability verification | 0.1 | 0 | Yes |
| No top-level executable code | No module-level side effects | New | 0 | Yes |
| Import-time purity scan | No sys, asyncio loops, threading, multiprocessing, path ops | New | 0 | Yes |
| Private symbol leak check | No `_private` objects in `__all__` | New | 7 | Yes |
| Legacy import isolation | N/A - legacy nodes hard deleted, no legacy namespace exists | New | 7 | Yes |

---

## Phase 0: Repository Stabilization

**Priority**: CRITICAL
**Duration Estimate**: 2-3 days
**Dependencies**: None (must be first)
**Related docs**: `PROJECT_REFACTORING_PLAN.md`, `DEPENDENCY_REFACTORING_PLAN.md`

### Phase 0 Risk Matrix

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Snapshot tests too brittle | Medium | High | Document intentional change process |
| Purity checks block legitimate code | Medium | Medium | Clear failure documentation |
| Import checks miss violations | High | Low | Multiple check strategies |

### Epic: Freeze Pre-Refactor Behavior

Before ANY refactoring begins, establish a stable baseline that prevents silent breakage.

#### Issue 0.1: Create pre-refactor API snapshot

**Title**: Create pre-refactor API snapshot tests
**Type**: Task
**Priority**: Urgent (1)
**Labels**: `architecture`, `testing`, `prerequisite`

**Description**:
Lock current public API behavior with snapshot tests before any changes.

**Acceptance Criteria**:
- [x] All public exports from `omnibase_core.nodes` captured
- [x] All public exports from `omnibase_core.infrastructure` captured
- [x] Snapshot tests verify import paths work
- [x] Snapshot tests verify class instantiation signatures
- [x] CI runs snapshot tests on every PR
- [ ] If snapshot tests fail due to intentional breaking changes, they MUST be updated in the same PR with a migration note in the changelog

---

#### Issue 0.2: Add integration baseline tests

**Title**: Add integration baseline tests for node behavior
**Type**: Task
**Priority**: Urgent (1)
**Labels**: `testing`, `prerequisite`

**Description**:
Create integration tests that verify current node behavior before refactoring.

**Acceptance Criteria**:
- [x] NodeCompute behavior captured in tests
- [x] NodeEffect behavior captured in tests
- [ ] NodeReducer behavior captured in tests
- [ ] NodeOrchestrator behavior captured in tests
- [x] Tests use real container injection
- [ ] Tests pass before AND after refactoring

---

#### Issue 0.3: Document current import paths

**Title**: Document all current import paths for compatibility
**Type**: Documentation
**Priority**: High (2)
**Labels**: `documentation`, `prerequisite`

**Description**:
Create a compatibility matrix documenting all current import paths that must continue working.

**Acceptance Criteria**:
- [ ] All `from omnibase_core.nodes import X` documented
- [ ] All `from omnibase_core.infrastructure import X` documented
- [ ] Consumer repos identified (omniintelligence, etc.)
- [ ] Required compatibility shims identified

---

#### Issue 0.4: Add import validation CI check

**Title**: Add CI check for cross-repo import violations
**Type**: Task
**Priority**: High (2)
**Labels**: `ci`, `prerequisite`

**Description**:
Add CI rules that will catch architectural violations during and after refactoring.

**Implementation**:
```yaml
# .github/workflows/import-check.yml
- name: Check no infra imports in core
  run: |
    ! grep -r "from omnibase_infra" src/omnibase_core/
    ! grep -r "import omnibase_infra" src/omnibase_core/
```

**Acceptance Criteria**:
- [ ] CI check prevents `omnibase_infra` imports in core
- [ ] CI check prevents direct I/O in declarative nodes (after Phase 2)
- [ ] CI check enforces `__all__` exports match actual exports
- [ ] CI runs on all PRs

---

#### Issue 0.5: Freeze NodeCoreBase interface

**Title**: Freeze NodeCoreBase interface before refactoring
**Type**: Task
**Priority**: High (2)
**Labels**: `architecture`, `prerequisite`

**Description**:
Document and freeze `NodeCoreBase` interface. Determine if it needs splitting into base logic vs contract-based logic.

**Acceptance Criteria**:
- [x] `NodeCoreBase` public methods documented
- [x] Decision made: single class vs split architecture
- [x] Interface tests created
- [x] Breaking changes identified and documented

---

#### Issue 0.6: Add ModelContractVersion with semver semantics

**Title**: Create ModelContractVersion with typed semver fields
**Type**: Feature
**Priority**: Urgent (1)
**Labels**: `architecture`, `prerequisite`, `contracts`

**Description**:
The system already relies on contract-version correctness during migration. Version drift causes silent breaking. Lock down contract version semantics early.

**Location**: `src/omnibase_core/models/contracts/model_contract_version.py`

**Specification**: See `docs/architecture/CONTRACT_STABILITY_SPEC.md` for full specification.

**Acceptance Criteria**:
- [ ] `ModelContractVersion` created with typed semver fields (`major`, `minor`, `patch`)
- [ ] Semver progression rules enforced (no downgrades without explicit flag)
- [ ] Integrated into contract snapshot tests
- [ ] CI check prevents unversioned contracts
- [ ] CI check prevents downgrading semver without `ALLOW_DOWNGRADE=true`
- [ ] mypy --strict passes
- [ ] Unit tests with >90% coverage

---

#### Issue 0.7: Create contract hash registry module

**Title**: Add cross-repo contract hash registry
**Type**: Feature
**Priority**: High (2)
**Labels**: `architecture`, `prerequisite`, `contracts`

**Description**:
Adapters and nodes rely on contract hashing, but there's no defined location for the hash registry.

**Location**: `src/omnibase_core/contracts/hash_registry.py`

**Specification**: See `docs/architecture/CONTRACT_STABILITY_SPEC.md` for full specification.

**Acceptance Criteria**:
- [ ] Stores deterministic SHA256 fingerprints for loaded contracts
- [ ] Used for debugging migration issues
- [ ] Detects drift between declarative and legacy versions
- [ ] Test verifies same contract produces identical hash before and after migration
- [ ] Contract fingerprints use `ModelContractVersion` + hash registry and MUST match the fingerprint format defined in Issue 3.7
- [ ] mypy --strict passes
- [ ] Unit tests with >90% coverage

---

#### Issue 0.8: Add NodeCoreBase purity contract tests

**Title**: Create purity guarantee tests for NodeCoreBase
**Type**: Task
**Priority**: High (2)
**Labels**: `testing`, `prerequisite`, `architecture`

**Description**:
Interface is frozen but purity guarantees are not. Protect architecture when contributors add convenience shortcuts.

**Acceptance Criteria**:
- [ ] Purity tests verify no declarative node calls to: networking libs, filesystem, subprocess, threading
- [ ] Use `ast` inspection to flag imports of anything outside core (note: core MUST NOT import SPI)
- [ ] CI rule blocks PRs that add I/O to core
- [ ] Test coverage for all pure computation paths
- [ ] Documentation of purity guarantees
- [ ] AST scan blocks: `import logging`, class-level mutable data, caching decorators (`@lru_cache`, `@cache`)
- [ ] Inheritance check: only `NodeCoreBase` and `Generic` allowed as base classes

---

#### Issue 0.9: Define declarative node meta-model specification

**Title**: Create node_meta_model.py with field specifications
**Type**: Feature
**Priority**: High (2)
**Labels**: `architecture`, `prerequisite`, `contracts`

**Description**:
Nodes are being reorganized but the meta-model they adhere to is not defined. Without this, the declarative set becomes inconsistent.

**Location**: `src/omnibase_core/contracts/node_meta_model.py`

**Acceptance Criteria**:
- [ ] Required fields for all declarative node contracts defined
- [ ] Optional fields defined
- [ ] Reserved extension fields defined
- [ ] Meta-schema validation enforces cross-node consistency
- [ ] mypy --strict passes
- [ ] Unit tests for meta-model validation

---

## Phase 1: Legacy Node Migration

**Priority**: HIGH
**Duration Estimate**: 3-4 days
**Dependencies**: Phase 0 complete
**Related docs**: `PROJECT_REFACTORING_PLAN.md`, `ARCHITECTURE_EVOLUTION_OVERVIEW.md`

> **SUPERSEDED (v0.4.0)**: This phase was originally planned to move legacy nodes to a `nodes/legacy/` namespace with deprecation warnings. However, after confirming there were **no existing users** of the legacy node implementations, the decision was made to **hard delete** the legacy code entirely. The issues below are retained for historical reference but are no longer applicable.
> **What Actually Happened**:
> - Legacy nodes (`NodeReducerLegacy`, `NodeOrchestratorLegacy`) were **never created**
> - The `nodes/legacy/` namespace was **never created**
> - Declarative nodes (`NodeReducer`, `NodeOrchestrator`) became the ONLY implementations
> - See `CHANGELOG.md` v0.4.0 for the "Implementation Note: Hard Deletion" section

~~### Epic: Move Legacy Nodes to Legacy Namespace~~ (SUPERSEDED)

~~Move current mixin-based node implementations to a `legacy/` namespace, making room for declarative implementations.~~ **This was replaced by hard deletion.**

#### Issue 1.1: Create nodes/legacy/ directory structure

**Title**: Create nodes/legacy/ directory structure
**Type**: Task
**Priority**: High (2)
**Labels**: `architecture`, `refactoring`

**Description**:
Create `src/omnibase_core/nodes/legacy/` directory with `__init__.py` that exports legacy classes with deprecation warnings.

**Acceptance Criteria**:
- [ ] Directory `src/omnibase_core/nodes/legacy/` exists
- [ ] `__init__.py` created with module docstring explaining deprecation
- [ ] Module-level `DeprecationWarning` emitted on import
- [ ] `__all__ = []` in `legacy/__init__.py` with explicit dictionary re-exports
- [ ] CI check blocks imports of legacy names from outside `nodes/legacy/`
- [ ] mypy --strict passes
- [ ] pyright passes

---

#### Issue 1.2: Move NodeCompute to NodeComputeLegacy

**Title**: Move NodeCompute to NodeComputeLegacy
**Type**: Task
**Priority**: High (2)
**Labels**: `architecture`, `refactoring`

**Description**:
Move `node_compute.py` to `nodes/legacy/node_compute_legacy.py`, rename class to `NodeComputeLegacy`.

**Acceptance Criteria**:
- [ ] File moved to `nodes/legacy/node_compute_legacy.py`
- [ ] Class renamed from `NodeCompute` to `NodeComputeLegacy`
- [ ] Deprecation docstring with `.. deprecated:: 0.4.0`
- [ ] Migration guide in docstring
- [ ] Export added to `legacy/__init__.py`
- [ ] mypy --strict passes
- [ ] pyright passes
- [ ] All existing tests pass unmodified (via compatibility shim)

---

#### Issue 1.3: Move NodeEffect to NodeEffectLegacy

**Title**: Move NodeEffect to NodeEffectLegacy
**Type**: Task
**Priority**: High (2)
**Labels**: `architecture`, `refactoring`

**Description**:
Move `node_effect.py` to `nodes/legacy/node_effect_legacy.py`, rename class to `NodeEffectLegacy`.

**Acceptance Criteria**:
- [ ] File moved to `nodes/legacy/node_effect_legacy.py`
- [ ] Class renamed from `NodeEffect` to `NodeEffectLegacy`
- [ ] Deprecation docstring with `.. deprecated:: 0.4.0`
- [ ] Migration guide in docstring
- [ ] Export added to `legacy/__init__.py`
- [ ] mypy --strict passes
- [ ] pyright passes
- [ ] All existing tests pass unmodified

---

#### Issue 1.4: Move NodeReducer to NodeReducerLegacy

**Title**: Move NodeReducer to NodeReducerLegacy
**Type**: Task
**Priority**: High (2)
**Labels**: `architecture`, `refactoring`

**Description**:
Move `node_reducer.py` to `nodes/legacy/node_reducer_legacy.py`, rename class to `NodeReducerLegacy`.

**Acceptance Criteria**:
- [ ] File moved to `nodes/legacy/node_reducer_legacy.py`
- [ ] Class renamed from `NodeReducer` to `NodeReducerLegacy`
- [ ] Deprecation docstring with `.. deprecated:: 0.4.0`
- [ ] Migration guide in docstring
- [ ] Export added to `legacy/__init__.py`
- [ ] mypy --strict passes
- [ ] pyright passes
- [ ] All existing tests pass unmodified

---

#### Issue 1.5: Move NodeOrchestrator to NodeOrchestratorLegacy

**Title**: Move NodeOrchestrator to NodeOrchestratorLegacy
**Type**: Task
**Priority**: High (2)
**Labels**: `architecture`, `refactoring`

**Description**:
Move `node_orchestrator.py` to `nodes/legacy/node_orchestrator_legacy.py`, rename class to `NodeOrchestratorLegacy`.

**Acceptance Criteria**:
- [ ] File moved to `nodes/legacy/node_orchestrator_legacy.py`
- [ ] Class renamed from `NodeOrchestrator` to `NodeOrchestratorLegacy`
- [ ] Deprecation docstring with `.. deprecated:: 0.4.0`
- [ ] Migration guide in docstring
- [ ] Export added to `legacy/__init__.py`
- [ ] mypy --strict passes
- [ ] pyright passes
- [ ] All existing tests pass unmodified

---

## Phase 2: Declarative Node Promotion

**Priority**: HIGH
**Duration Estimate**: 2-3 days
**Dependencies**: Phase 1 complete
**Related docs**: `ONEX_FOUR_NODE_ARCHITECTURE.md`, `MIGRATING_TO_DECLARATIVE_NODES.md`

### Epic: Make Declarative Nodes the Default

Rename existing declarative nodes, create new declarative implementations, and establish compatibility shims.

### Declarative Node Examples

> These examples illustrate the purity rules defined in [INV-1: Core Purity Rules](#inv-1-core-purity-rules). For complete node implementation guidance, see [Node Building Guide](guides/node-building/README.md) and [ONEX Four-Node Architecture](architecture/ONEX_FOUR_NODE_ARCHITECTURE.md).

#### GOOD: Pure Compute Node

```python
from typing import Generic, TypeVar
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.models.contracts import ModelComputeContract

T_In = TypeVar("T_In")
T_Out = TypeVar("T_Out")

class NodeIdentityCompute(NodeCoreBase, Generic[T_In, T_Out]):
    """Pure compute node - no I/O, no state, no side effects."""

    def __init__(self, contract: ModelComputeContract) -> None:
        self._contract = contract  # Read-only reference

    def compute(self, input_data: T_In) -> T_Out:
        # Pure transformation only
        return {"result": input_data["value"]}
```

#### BAD: Impure Node (Multiple Violations)

```python
import logging  # P1: No logging imports
from functools import lru_cache  # P3: No caching

class BadNode(NodeCoreBase, SomeMixin):  # P4: No extra inheritance
    cache = {}  # P2: No class-level mutable data

    def __init__(self, contract, handler):
        self._contract = contract
        self._handler = handler  # P5: No handler inspection
        self._contract.name = "modified"  # P6: No contract mutation

    @lru_cache  # P3: No caching
    def compute(self, input_data):
        logging.info("Processing")  # P1: No logging
        if isinstance(self._handler, HttpHandler):  # P5: No handler inspection
            pass
        return self._handler.execute(input_data)  # A1: Adapters don't call handlers
```

**Violation Summary**:

| Code | Violation | Rule |
|------|-----------|------|
| `import logging` | Logging in declarative node | INV-1 P1 |
| `@lru_cache` | Caching in core | INV-1 P3 |
| `SomeMixin` | Extra inheritance | INV-1 P4 |
| `cache = {}` | Class-level mutable data | INV-1 P2 |
| `isinstance(handler, ...)` | Handler type inspection | INV-1 P5 |
| `contract.name = ...` | Contract mutation | INV-1 P6 |

---

#### Issue 2.1: Rename NodeReducerDeclarative to NodeReducer ✅ COMPLETE

**Title**: Rename NodeReducerDeclarative to NodeReducer
**Type**: Task
**Priority**: High (2)
**Labels**: `architecture`, `refactoring`
**Status**: ✅ **COMPLETE** (v0.4.0)

**Description**:
Rename `node_reducer_declarative.py` to `node_reducer.py`, rename class from `NodeReducerDeclarative` to `NodeReducer`.

**Acceptance Criteria**:
- [x] File renamed from `node_reducer_declarative.py` to `node_reducer.py`
- [x] Class renamed from `NodeReducerDeclarative` to `NodeReducer`
- [x] Docstring updated with `.. versionchanged:: 0.4.0`
- [x] All internal imports updated
- [x] mypy --strict passes
- [x] pyright passes
- [x] Pydantic validation tests pass

**Result**: `NodeReducer` is now the PRIMARY FSM-driven implementation. Import from `omnibase_core.nodes.node_reducer`.

---

#### Issue 2.2: Rename NodeOrchestratorDeclarative to NodeOrchestrator ✅ COMPLETE

**Title**: Rename NodeOrchestratorDeclarative to NodeOrchestrator
**Type**: Task
**Priority**: High (2)
**Labels**: `architecture`, `refactoring`
**Status**: ✅ **COMPLETE** (v0.4.0)

**Description**:
Rename `node_orchestrator_declarative.py` to `node_orchestrator.py`, rename class from `NodeOrchestratorDeclarative` to `NodeOrchestrator`.

**Acceptance Criteria**:
- [x] File renamed from `node_orchestrator_declarative.py` to `node_orchestrator.py`
- [x] Class renamed from `NodeOrchestratorDeclarative` to `NodeOrchestrator`
- [x] Docstring updated with `.. versionchanged:: 0.4.0`
- [x] All internal imports updated
- [x] mypy --strict passes
- [x] pyright passes
- [x] Pydantic validation tests pass

**Result**: `NodeOrchestrator` is now the PRIMARY workflow-driven implementation. Import from `omnibase_core.nodes.node_orchestrator`.

---

#### Issue 2.3: Create declarative NodeCompute

**Title**: Create declarative NodeCompute implementation
**Type**: Feature
**Priority**: High (2)
**Labels**: `architecture`, `new-feature`

**Description**:
Create new `nodes/node_compute.py` with declarative `NodeCompute` class implementing pure computation pattern (no I/O).

**Acceptance Criteria**:
- [ ] New file `nodes/node_compute.py` created
- [ ] `NodeCompute` class inherits from `NodeCoreBase` and `Generic[T_Input, T_Output]`
- [ ] `compute()` method defined as abstract (raises `NotImplementedError`)
- [ ] Docstring includes `.. versionadded:: 0.4.0`
- [ ] Enforces pure computation (no I/O allowed)
- [ ] Node contract hash included in metadata
- [ ] mypy --strict passes
- [ ] pyright passes
- [ ] Unit tests created with Pydantic validation

---

#### Issue 2.4: Create declarative NodeEffect

**Title**: Create declarative NodeEffect implementation
**Type**: Feature
**Priority**: High (2)
**Labels**: `architecture`, `new-feature`

**Description**:
Create new `nodes/node_effect.py` with declarative `NodeEffect` class that receives handlers via injection (no direct I/O).

**Acceptance Criteria**:
- [ ] New file `nodes/node_effect.py` created
- [ ] `NodeEffect` class inherits from `NodeCoreBase` and `Generic[T_Input, T_Output]`
- [ ] `execute_effect()` method accepts `handler: ProtocolHandler` parameter
- [ ] Handler is injected, NOT instantiated internally
- [ ] Docstring includes `.. versionadded:: 0.4.0`
- [ ] Node contract hash included in metadata
- [ ] mypy --strict passes
- [ ] pyright passes
- [ ] Unit tests created with Pydantic validation

---

#### Issue 2.5: Update nodes/__init__.py exports

**Title**: Update nodes/__init__.py for declarative defaults
**Type**: Task
**Priority**: High (2)
**Labels**: `architecture`, `refactoring`

**Description**:
Update `nodes/__init__.py` to export declarative nodes as default, add `__getattr__` compatibility shim.

**Implementation**:
```python
# Compatibility mapping: maps deprecated names (pre-v0.4.0) to current names (v0.4.0+)
# - "NodeReducerDeclarative" was the v0.3.x name, now simply "NodeReducer"
# - "NodeOrchestratorDeclarative" was the v0.3.x name, now simply "NodeOrchestrator"
# Note: "NodeComputeLegacy" and "NodeEffectLegacy" are the v0.4.0 names for
# deprecated mixin-based implementations (see Phase 1 issues 1.2-1.5)
_LEGACY_ALIASES = {
    "NodeReducerDeclarative": "NodeReducer",      # v0.3.x -> v0.4.0
    "NodeOrchestratorDeclarative": "NodeOrchestrator",  # v0.3.x -> v0.4.0
}

def __getattr__(name: str):
    if name in _LEGACY_ALIASES:
        warnings.warn(
            f"{name} is deprecated, use {_LEGACY_ALIASES[name]}",
            DeprecationWarning,
            stacklevel=2,
        )
        return globals()[_LEGACY_ALIASES[name]]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

**Acceptance Criteria**:
- [ ] Default exports: `NodeCompute`, `NodeEffect`, `NodeReducer`, `NodeOrchestrator` (all declarative)
- [ ] `__getattr__` handles deprecated names with warnings
- [ ] `__all__` updated and verified
- [ ] Module docstring updated with `.. versionchanged:: 0.4.0`
- [ ] Shim remains in place for v0.4.x and v0.5.x; removed in v1.0.0 when legacy nodes are deleted
- [ ] mypy --strict passes
- [ ] pyright passes

---

#### Issue 2.6: Update EnumNodeKind enum and compatibility map

**Title**: Update EnumNodeKind enum for declarative node support
**Type**: Task
**Priority**: High (2)
**Labels**: `architecture`, `refactoring`

**Description**:
Update `EnumNodeKind` enum with any new values needed, create compatibility mapping for legacy->declarative names.

**Acceptance Criteria**:
- [x] `EnumNodeKind` enum reviewed for completeness
- [x] Legacy name → new name mapping created
- [x] Serializer/deserializer updated for backward compatibility
- [ ] Legacy→declarative compatibility fingerprint added
- [x] mypy --strict passes
- [x] Unit tests for enum serialization

---

#### Issue 2.7: Add required handler capability mapping 🔗 core+spi

**Title**: Define handler capability requirements per node type
**Type**: Feature
**Priority**: High (2)
**Labels**: `architecture`, `validation`

**Description**:
Contracts are validated but node type capability requirements are not specified. Prevents runtime explosions at execution time.

**Location**: `src/omnibase_core/constants/handler_capabilities.py`

**Acceptance Criteria**:
- [ ] `NodeEffect` requires handler that implements `execute()`
- [ ] `NodeReducer` requires no handler, but may require FSM interpreter
- [ ] `NodeOrchestrator` requires workflow resolver
- [ ] Constants file: `EFFECT_CAPABILITIES = {"http", "db", "kv", ...}`
- [ ] Validation: contracts demanding unsupported capabilities produce clear errors
- [ ] mypy --strict passes
- [ ] Unit tests for capability validation

---

## Phase 3: Contract Adapters & Validators

**Priority**: HIGH
**Duration Estimate**: 3-4 days
**Dependencies**: Phase 2 complete

> **Source of Truth**: Phase 3 defines the canonical mapping between declarative contracts and running nodes. After v0.4.0, **any new node type or adapter must conform to these patterns**. This phase establishes the "contract brain" of OmniNode.

**Related docs**: `MINIMAL_RUNTIME_PHASED_PLAN.md`, `ONEX_FOUR_NODE_ARCHITECTURE.md`

### Phase 3 Risk Matrix

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Adapter bugs cause silent data corruption | High | Medium | Fuzz testing, round-trip tests |
| Validator misses edge cases | High | Medium | Property-based testing |
| Fingerprint instability | Medium | Low | Cross-Python-version CI |
| Error taxonomy incomplete | Medium | Medium | Review infra error types |

> **Adapter Boundary Rules**: See INV-3 in "Global Architectural Invariants" section.

### Epic: Create Contract-to-Protocol Adapters

Declarative nodes must wrap Core Pydantic models into SPI-compliant request objects.

#### Issue 3.1: Create effect contract adapter 🔗 core+spi

**Title**: Create effect_adapter.py for Effect node contracts
**Type**: Feature
**Priority**: High (2)
**Labels**: `architecture`, `new-feature`, `adapter`

**Description**:
Create adapter that transforms `ModelEffectContract` into SPI-compliant handler requests.

**Location**: `src/omnibase_core/adapters/effect_adapter.py`

**Acceptance Criteria**:
- [ ] Adapter class created with type-safe transformations
- [ ] Handles all effect types (HTTP, DB, event, etc.)
- [ ] Validates contract shape before transformation
- [ ] Adapter MUST NOT call handlers directly
- [ ] Adapter MUST NOT perform capability inference
- [ ] Adapter MUST NOT perform data transformation beyond structural mapping
- [ ] mypy --strict passes
- [ ] pyright passes
- [ ] Unit tests with >90% coverage
- [ ] Pydantic validation tests included
- [ ] Used by: `NodeEffect`
- [ ] Produces: SPI-level request models for `ProtocolHandler` integrations
- [ ] Assumes inputs passed `contract_validator`; focuses only on transformation

---

#### Issue 3.2: Create compute contract adapter 🔗 core+spi

**Title**: Create compute_adapter.py for Compute node contracts
**Type**: Feature
**Priority**: High (2)
**Labels**: `architecture`, `new-feature`, `adapter`

**Description**:
Create adapter that validates and transforms Compute contracts for pure computation.

**Location**: `src/omnibase_core/adapters/compute_adapter.py`

**Acceptance Criteria**:
- [ ] Adapter class created for compute contracts
- [ ] Validates input/output type shapes
- [ ] Enforces pure computation (no I/O references in contract)
- [ ] Adapter MUST NOT call handlers directly (compute nodes have no handlers, but this constraint ensures adapters remain pure transformation layers consistent with effect/reducer/orchestrator adapters)
- [ ] Adapter MUST NOT perform capability inference
- [ ] Adapter MUST NOT perform data transformation beyond structural mapping
- [ ] mypy --strict passes
- [ ] pyright passes
- [ ] Unit tests with >90% coverage
- [ ] Used by: `NodeCompute`
- [ ] Produces: SPI-level request models for pure computation
- [ ] Assumes inputs passed `contract_validator`; focuses only on transformation

---

#### Issue 3.3: Create reducer contract adapter 🔗 core+spi

**Title**: Create reducer_adapter.py for Reducer node contracts
**Type**: Feature
**Priority**: High (2)
**Labels**: `architecture`, `new-feature`, `adapter`

**Description**:
Create adapter that transforms Reducer contracts for FSM-based state management.

**Location**: `src/omnibase_core/adapters/reducer_adapter.py`

**Acceptance Criteria**:
- [ ] Adapter class created for reducer contracts
- [ ] Validates FSM definition in contract
- [ ] Transforms state transitions to ModelIntent emissions
- [ ] Adapter MUST NOT call handlers directly
- [ ] Adapter MUST NOT perform capability inference
- [ ] Adapter MUST NOT perform data transformation beyond structural mapping
- [ ] mypy --strict passes
- [ ] pyright passes
- [ ] Unit tests with >90% coverage
- [ ] Used by: `NodeReducer`
- [ ] Produces: ModelIntent emissions for FSM-based state management
- [ ] Assumes inputs passed `contract_validator`; focuses only on transformation

---

#### Issue 3.4: Create orchestrator contract adapter 🔗 core+spi

**Title**: Create orchestrator_adapter.py for Orchestrator node contracts
**Type**: Feature
**Priority**: High (2)
**Labels**: `architecture`, `new-feature`, `adapter`

**Description**:
Create adapter that transforms Orchestrator contracts for workflow coordination.

**Location**: `src/omnibase_core/adapters/orchestrator_adapter.py`

**Acceptance Criteria**:
- [ ] Adapter class created for orchestrator contracts
- [ ] Validates workflow definition in contract
- [ ] Transforms workflow steps to ModelAction emissions
- [ ] Adapter MUST NOT call handlers directly
- [ ] Adapter MUST NOT perform capability inference
- [ ] Adapter MUST NOT perform data transformation beyond structural mapping
- [ ] mypy --strict passes
- [ ] pyright passes
- [ ] Unit tests with >90% coverage
- [ ] Used by: `NodeOrchestrator`
- [ ] Produces: ModelAction emissions for workflow coordination
- [ ] Assumes inputs passed `contract_validator`; focuses only on transformation

---

#### Issue 3.5: Create Core contract validation layer 🔗 core+spi

**Title**: Add Core contract validation layer
**Type**: Feature
**Priority**: High (2)
**Labels**: `architecture`, `validation`, `new-feature`

**Description**:
Create centralized validation layer that validates contracts at node load time.

**Location**: `src/omnibase_core/services/service_contract_validator.py`

**Validations Required**:
- Input/output shape validation
- Contract version compatibility checks
- Required handler capability verification
- Runtime-schema alignment
- Node contract hash computation

**Acceptance Criteria**:
- [ ] Validates input/output shapes on node load
- [ ] Validates version compatibility (semver-aware)
- [ ] Validates required handler capabilities exist
- [ ] Computes deterministic contract hash
- [ ] Returns structured `ValidationResult` with errors/warnings
- [ ] Validator phases: structural -> semantic -> capability -> fingerprint (in order)
- [ ] Error format: `ERR_CODE: message (path.to.field)` - e.g., `CONTRACT_INVALID_TYPE: Expected string (input.name)`
- [ ] Validators MUST NOT raise Pydantic `ValidationError` directly - wrap in declarative errors
- [ ] Contract normalization pipeline runs before fingerprint computation
- [ ] mypy --strict passes
- [ ] pyright passes
- [ ] Unit tests with >90% coverage
- [ ] Integration tests with real contracts
- [ ] Adapters MUST assume contracts have passed Core validation; they may not re-implement structural checks
- [ ] Any contract shape validation belongs in `contract_validator.py`, not in adapters

---

#### Issue 3.6: Introduce error taxonomy for declarative nodes 🔗 core+spi+infra

**Title**: Create canonical error classes for declarative node validation
**Type**: Feature
**Priority**: High (2)
**Labels**: `architecture`, `errors`, `new-feature`

**Description**:
Define canonical error classes for the validation and adapter logic. Makes debugging tolerable and stack traces meaningful.

**Location**: `src/omnibase_core/errors/declarative_errors.py`

**Acceptance Criteria**:
- [ ] `ContractValidationError` - invalid contract structure
- [ ] `AdapterBindingError` - adapter cannot bind to contract
- [ ] `PurityViolationError` - node contains I/O or impure code
- [ ] `NodeExecutionError` - runtime execution failure
- [ ] `UnsupportedCapabilityError` - contract demands unavailable capability
- [ ] Every contract validator uses these error classes
- [ ] Every adapter wraps raw exceptions into these
- [ ] mypy --strict passes
- [ ] Unit tests for error serialization
- [ ] Declarative errors MUST be serializable into core RuntimeError types used by infra (e.g., `HandlerNotFoundError`, `EnvelopeValidationError`) or be easily mapped by infra

**Canonical Error Example**:
```python
raise ContractValidationError(
    code="CONTRACT_INVALID_TYPE",
    message="Expected string",
    path="input.name",
)

# Serialized format:
# "CONTRACT_INVALID_TYPE: Expected string (input.name)"
```

---

> **Contract Fingerprint Invariants**: See INV-4 in "Global Architectural Invariants" section.

#### Issue 3.7: Add contract fingerprint specification 🔗 core+spi+infra

**Title**: Require contract fingerprints with defined format
**Type**: Feature
**Priority**: High (2)
**Labels**: `architecture`, `contracts`, `new-feature`

**Description**:
Contract hashes are mentioned but fingerprint formats and propagation rules are not defined.

**Dependencies**: Uses `ModelContractVersion` (Issue 0.6) and `hash_registry` (Issue 0.7) from Phase 0.

**Specification**: See `docs/architecture/CONTRACT_STABILITY_SPEC.md` for full specification.

**Contract Fingerprint Spec**: `<semver>:<sha256(first 12 bytes)>`

**Acceptance Criteria**:
- [ ] Contract fingerprint format: `<semver>:<sha256(first 12 bytes)>`
- [ ] Example fingerprint format: `0.4.0:8fa1e2b4c9d1` (semver + first 12 hex chars of SHA256)
- [ ] Fingerprints appear in node metadata
- [ ] Fingerprints returned by adapters
- [ ] Fingerprints logged when binding contracts
- [ ] mypy --strict passes
- [ ] Unit tests for fingerprint generation

---

#### Issue 3.8: Add adapter fuzzing tests

**Title**: Create fuzz tests for malformed contracts
**Type**: Task
**Priority**: High (2)
**Labels**: `testing`, `adapters`, `security`

**Description**:
Adapters are created for four node types but malformed contracts are not tested. Critical for user-created nodes.

**Acceptance Criteria**:
- [ ] Fuzz tests for random field drops
- [ ] Fuzz tests for random type mismatches
- [ ] Fuzz tests for random illegal transitions
- [ ] Validators catch errors gracefully
- [ ] Adapters reject malformed contracts cleanly
- [ ] Coverage of all adapter types (compute, effect, reducer, orchestrator)

---

#### Issue 3.9: Add strict shape enforcement for compute nodes

**Title**: Enforce structural type equivalence on compute nodes
**Type**: Feature
**Priority**: High (2)
**Labels**: `architecture`, `validation`, `compute`

**Description**:
Compute nodes should enforce structural type equivalence (not duck typing). Eliminates subtle mismatches when users update workflow steps or contracts.

**Acceptance Criteria**:
- [ ] During adapter validation: compare input/output Pydantic models by structural identity
- [ ] Compare fields, order, and types
- [ ] Fail on missing fields
- [ ] Fail on extra fields
- [ ] Fail on type mismatches (including `Optional` vs non-optional)
- [ ] mypy --strict passes
- [ ] Unit tests for shape enforcement

---

#### Issue 3.10: Add FSM simulation tooling for reducers

**Title**: Create FSM analysis module for reducer validation
**Type**: Feature
**Priority**: High (2)
**Labels**: `architecture`, `reducer`, `validation`

**Description**:
Reducer adapters translate FSMs but lack rule visualization, state reachability analysis, and dead transition detection.

**Location**: `src/omnibase_core/validation/fsm_analysis.py`

**Acceptance Criteria**:
- [ ] Detect unreachable states
- [ ] Detect cycles without exit
- [ ] Detect missing transitions
- [ ] Detect ambiguous transitions (state + event → multiple targets)
- [ ] Detect terminal states missing final emissions (if required by contract)
- [ ] Validate state names are unique within FSM
- [ ] Report all validation failures, not just first
- [ ] Deterministic FSM simulation tests
- [ ] mypy --strict passes
- [ ] Unit tests for FSM analysis

---

#### Issue 3.11: Add workflow validation with topological sorting

**Title**: Create workflow validator with DAG correctness checks
**Type**: Feature
**Priority**: High (2)
**Labels**: `architecture`, `orchestrator`, `validation`

**Description**:
Orchestrators are validated generically but DAG correctness, cycles, and referenced step existence are not verified.

**Location**: `src/omnibase_core/validation/workflow_validator.py`

**Acceptance Criteria**:
- [ ] Runs Kahn's algorithm for topological sorting
- [ ] Detects cycles with step names
- [ ] Verifies all dependencies exist
- [ ] Detect isolated steps (no incoming AND no outgoing edges)
- [ ] Validate unique step names within workflow
- [ ] Validate all referenced dependencies exist before topological sort
- [ ] Report cycle participants with step names, not just "cycle detected"
- [ ] Tests for range of malformed workflows
- [ ] mypy --strict passes
- [ ] Unit tests with >90% coverage

---

> **Behavior Equivalence Definition**: See "Behavior Equivalence Rules" section above.

---

## Phase 4: Migration Verification Tests

**Priority**: HIGH
**Duration Estimate**: 2-3 days
**Dependencies**: Phase 3 complete
**Related docs**: `PROJECT_REFACTORING_PLAN.md`

### Phase 4 Risk Matrix

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Behavior differences missed | High | Medium | Exhaustive input generation |
| Non-determinism in tests | Medium | Medium | Seed all RNGs |
| Legacy behavior undocumented | Medium | High | Capture before refactoring |

### Epic: Verify Migration Correctness

Explicit verification that the migration preserves backward compatibility and behavior.

#### Issue 4.1: Create legacy import verification tests

**Title**: Verify legacy imports work with deprecation warnings
**Type**: Task
**Priority**: High (2)
**Labels**: `testing`, `migration`, `compatibility`

**Description**:
Create tests that verify legacy imports still work but produce deprecation warnings.

**Acceptance Criteria**:
- [ ] All 4 legacy imports work with warnings
- [ ] Old declarative names (`NodeReducerDeclarative`, etc.) work with warnings
- [ ] Warnings include migration guidance
- [ ] Tests run in CI

---

#### Issue 4.2: Create declarative import override tests

**Title**: Verify declarative imports are now defaults
**Type**: Task
**Priority**: High (2)
**Labels**: `testing`, `migration`

**Description**:
Create tests that verify default imports resolve to declarative implementations.

**Acceptance Criteria**:
- [ ] Default `NodeCompute` is declarative
- [ ] Default `NodeEffect` is declarative
- [ ] Default `NodeReducer` is declarative
- [ ] Default `NodeOrchestrator` is declarative
- [ ] No warnings on default imports

---

#### Issue 4.3: Create behavior equivalence tests

**Title**: Verify behavior identical between versions
**Type**: Task
**Priority**: High (2)
**Labels**: `testing`, `migration`, `compatibility`

**Description**:
Create tests that verify legacy and declarative nodes produce identical outputs for identical inputs.

**Acceptance Criteria**:
- [ ] Same input → same output for compute operations
- [ ] Same input → same state transitions for reducers
- [ ] Same input → same workflow steps for orchestrators
- [ ] Contract binding behavior unchanged
- [ ] Error handling behavior unchanged
- [ ] Where randomness is used, tests must seed RNGs or override random-dependent behaviors to ensure deterministic legacy vs declarative comparisons
- [ ] Tests follow "Behavior Equivalence Definition" section exactly
- [ ] Non-deterministic tests use fixed seeds or mocks
- [ ] Partial contract tests verify error/silent behavior per definition

---

#### Issue 4.4: Create contract binding verification tests

**Title**: Verify contract binding unchanged after migration
**Type**: Task
**Priority**: High (2)
**Labels**: `testing`, `migration`

**Description**:
Create tests that verify contracts bind correctly to both legacy and declarative nodes.

**Acceptance Criteria**:
- [ ] YAML contracts load correctly
- [ ] Contract validation passes for declarative nodes
- [ ] Contract hash computation is deterministic
- [ ] Version compatibility checks work

---

#### Issue 4.5: Add contract compatibility matrix tests

**Title**: Create table-driven contract compatibility tests
**Type**: Task
**Priority**: High (2)
**Labels**: `testing`, `migration`, `contracts`

**Description**:
Legacy and declarative equivalence is validated but not contract-by-contract. Avoids regressions between contract iterations.

**Acceptance Criteria**:
- [ ] Table-driven tests for each contract: legacy binds, declarative binds, hash matches
- [ ] Version-compatibility rules: reject older versions lacking required fields
- [ ] Warn on newer semver requirements
- [ ] Test coverage for all four node types

---

#### Issue 4.6: Add cross-version behavioral comparison tests

**Title**: Create regression suite for error and edge case equivalence
**Type**: Task
**Priority**: High (2)
**Labels**: `testing`, `migration`, `compatibility`

**Description**:
Behavior comparison skips error equivalence, edge case equivalence, and partial contract equivalence.

**Acceptance Criteria**:
- [ ] Same error in v0.3.x fails in same shape in v0.4.0 declarative nodes
- [ ] Same edge case produces identical output
- [ ] Partial contracts (missing non-critical fields) handled consistently
- [ ] Regression tests documented and automated
- [ ] Comparison targets: last v0.3.x release vs v0.4.0
- [ ] If v0.3.x line changes after v0.4.0 development starts, tests must be updated with explicit rationale in the changelog

---

#### Issue 4.7: Add adapter round-trip consistency tests

**Title**: Verify adapter round-trip consistency for all node types
**Type**: Task
**Priority**: High (2)
**Labels**: `testing`, `adapters`, `consistency`

**Description**:
For a contract: validate → adapt → emit canonical internal representation → convert back through adapter → compare equivalence.

**Acceptance Criteria**:
- [ ] Round-trip tests for Compute adapter
- [ ] Round-trip tests for Effect adapter
- [ ] Round-trip tests for Reducer adapter
- [ ] Round-trip tests for Orchestrator adapter
- [ ] Fail if order of fields changes unexpectedly
- [ ] Fail if required metadata is lost

---

## Phase 5: Test Updates

**Priority**: MEDIUM
**Duration Estimate**: 3-4 days
**Dependencies**: Phase 4 complete

> **Sequencing Requirement**: Phase 5 **must not start** until Phase 4 verifies behavioral equivalence across legacy and declarative nodes (Issues 4.1-4.7). Test renaming without verification will mask regressions.

**Related docs**: `PROJECT_REFACTORING_PLAN.md`

### Epic: Update Existing Tests for New Naming Convention

Update all existing test files to use new import paths and class names.

#### Issue 5.1: Update unit test imports for legacy nodes

**Title**: Update unit test imports for legacy node classes
**Type**: Task
**Priority**: Medium (3)
**Labels**: `testing`, `refactoring`

**Description**:
Update all test files in `tests/unit/nodes/` to use new import paths for legacy nodes.

**Files to Update**:
- `tests/unit/test_thread_safety.py`
- `tests/unit/nodes/test_declarative_nodes.py`
- `tests/unit/nodes/test_rollback_failure_handling.py`
- `tests/unit/nodes/test_retry_count_tracking.py`
- `tests/unit/infrastructure/test_node_base.py`
- `tests/unit/infrastructure/test_node_config_provider.py`

**Acceptance Criteria**:
- [ ] All imports updated to use `NodeComputeLegacy`, etc. from `nodes.legacy`
- [ ] Tests using declarative nodes use new names
- [ ] All unit tests pass
- [ ] No import errors
- [ ] Test coverage ≥ baseline (60%)

---

#### Issue 5.2: Update integration test imports

**Title**: Update integration test imports for legacy nodes
**Type**: Task
**Priority**: Medium (3)
**Labels**: `testing`, `refactoring`

**Description**:
Update integration tests to use legacy imports where testing legacy behavior.

**Files to Update**:
- `tests/integration/test_rollback_failure_integration.py`
- `tests/integration/test_cache_config_integration.py`

**Acceptance Criteria**:
- [ ] Integration tests use correct import paths
- [ ] All integration tests pass
- [ ] No deprecation warnings in declarative-only tests
- [ ] Deprecation warnings expected in legacy tests

---

#### Issue 5.3: Update service model tests

**Title**: Update service model tests for new class names
**Type**: Task
**Priority**: Medium (3)
**Labels**: `testing`, `refactoring`

**Description**:
Update 16 service model test files for new class names and MRO references.

**Acceptance Criteria**:
- [ ] All 16 service model test files updated
- [ ] MRO references updated where applicable
- [ ] All service model tests pass
- [ ] Test coverage ≥ baseline (60%)

---

#### Issue 5.4: Remove deprecated class name references ✅ COMPLETE

**Title**: Remove NodeReducerDeclarative/NodeOrchestratorDeclarative from tests
**Type**: Task
**Priority**: Medium (3)
**Labels**: `testing`, `refactoring`
**Status**: ✅ **COMPLETE** (v0.4.0)

**Description**:
Search and replace all remaining deprecated class name references in tests.

**Acceptance Criteria**:
- [x] No `NodeReducerDeclarative` references in tests (now use `NodeReducer`)
- [x] No `NodeOrchestratorDeclarative` references in tests (now use `NodeOrchestrator`)
- [x] All tests pass
- [x] No unexpected deprecation warnings

**Note**: The class names `NodeReducer` and `NodeOrchestrator` are now the PRIMARY implementations. Documentation has been updated to reflect this change.

---

## Phase 6: Documentation Updates

**Priority**: MEDIUM
**Duration Estimate**: 2 days
**Dependencies**: Phase 5 complete
**Related docs**: `docs/INDEX.md`, `CLAUDE.md`, `CONTRIBUTING.md`

### Epic: Update Documentation for v0.4.0

Update all documentation with version markers and breaking change notices.

#### Issue 6.1: Update CLAUDE.md with node class changes

**Title**: Update CLAUDE.md with v0.4.0 node class changes
**Type**: Documentation
**Priority**: Medium (3)
**Labels**: `documentation`

**Description**:
Add comprehensive section documenting default (declarative) vs legacy node classes.

**Acceptance Criteria**:
- [ ] CLAUDE.md updated with node class section
- [ ] Links to migration documentation
- [ ] Version info accurate (v0.4.0, v1.0.0 removal)
- [ ] Cross-repo dependency rules documented

---

#### Issue 6.2: Update ONEX_FOUR_NODE_ARCHITECTURE.md

**Title**: Update ONEX architecture documentation
**Type**: Documentation
**Priority**: Medium (3)
**Labels**: `documentation`

**Description**:
Update architecture documentation to reflect declarative nodes as default.

**Acceptance Criteria**:
- [ ] All node examples use declarative pattern
- [ ] Legacy pattern documented as deprecated
- [ ] `.. versionchanged:: 0.4.0` markers added
- [ ] Diagrams updated if applicable

---

#### Issue 6.3: Update node-building tutorials

**Title**: Update node-building tutorials for declarative-first
**Type**: Documentation
**Priority**: Medium (3)
**Labels**: `documentation`

**Description**:
Update all node-building tutorials to use declarative nodes as primary examples.

**Acceptance Criteria**:
- [ ] All tutorials use declarative patterns
- [ ] Import statements reflect new paths
- [ ] Legacy mentioned only as deprecated alternative
- [ ] `.. versionchanged:: 0.4.0` markers added
- [ ] All code examples compile/run

---

#### Issue 6.4: Add breaking change notice to INDEX.md

**Title**: Add v0.4.0 breaking change notice
**Type**: Documentation
**Priority**: Medium (3)
**Labels**: `documentation`

**Description**:
Add prominent breaking change notice to documentation index.

**Acceptance Criteria**:
- [ ] Breaking change callout box in INDEX.md
- [ ] Link to PROJECT_REFACTORING_PLAN.md
- [ ] Clear migration steps
- [ ] Timeline (v0.4.0 → v1.0.0) visible

---

#### Issue 6.5: Add mixin classification mapping table

**Title**: Add mixin→classification→destination mapping table
**Type**: Documentation
**Priority**: Medium (3)
**Labels**: `documentation`

**Description**:
Add comprehensive mapping table showing where each mixin goes in the new architecture.

**Acceptance Criteria**:
- [ ] All 40 mixins listed
- [ ] Classification (R/H/D) for each
- [ ] Destination path for each
- [ ] Migration phase noted

---

#### Issue 6.6: Add contract-to-handler data flow diagram

**Title**: Create architecture diagram showing contract → handler flow
**Type**: Documentation
**Priority**: Low (4)
**Labels**: `documentation`, `architecture`

**Description**:
Add visual diagram showing exact data flow through the system.

**Diagram Flow**:
```text
Contract (YAML)
    → Validator (structural → semantic → capability → fingerprint)
    → Adapter (pure transformation)
    → Request Model
    → [Runtime Host boundary]
    → Handler (I/O execution)
    → Response
    → [Optional: Adapter response transformation]
```

**Acceptance Criteria**:
- [ ] Diagram in docs/architecture/ as SVG and PNG
- [ ] Shows clear core/infra boundary
- [ ] Referenced from ONEX_FOUR_NODE_ARCHITECTURE.md
- [ ] Includes legend explaining each component

---

## Phase 7: Deprecation & CI Enforcement

**Priority**: MEDIUM
**Duration Estimate**: 2 days
**Dependencies**: Phase 6 complete
**Related docs**: `PROJECT_REFACTORING_PLAN.md`, `.github/workflows/`

### Epic: Add Deprecation Warnings and CI Rules

Implement deprecation warnings and CI enforcement for architectural rules.

#### Issue 7.1: Add module-level deprecation warning

**Title**: Add deprecation warning to legacy/__init__.py
**Type**: Task
**Priority**: Medium (3)
**Labels**: `architecture`, `deprecation`

**Description**:
Emit single `DeprecationWarning` on legacy module import.

**Acceptance Criteria**:
- [ ] Single warning on `from omnibase_core.nodes.legacy import ...`
- [ ] No double-warnings on class instantiation
- [ ] Warning includes version info and migration path
- [ ] `stacklevel=2` for correct caller display

---

#### Issue 7.2: Configure pytest for deprecation warnings

**Title**: Configure pytest deprecation warning capture
**Type**: Task
**Priority**: Medium (3)
**Labels**: `testing`, `configuration`

**Description**:
Update `pyproject.toml` to capture deprecation warnings.

**Acceptance Criteria**:
- [ ] pytest configuration updated
- [ ] Warnings displayed during test runs
- [ ] Path to `error::DeprecationWarning` documented for v0.5.0

---

#### Issue 7.3: Add CI strict typing enforcement

**Title**: Enable --strict typing in CI
**Type**: Task
**Priority**: Medium (3)
**Labels**: `ci`, `typing`

**Description**:
Ensure CI runs mypy and pyright in strict mode.

**Acceptance Criteria**:
- [ ] `mypy --strict` in CI
- [ ] `pyright` in CI
- [ ] `__all__` exports verified
- [ ] Pydantic plugin enabled

---

#### Issue 7.4: Add CI import violation checks

**Title**: Add CI checks for architectural violations
**Type**: Task
**Priority**: Medium (3)
**Labels**: `ci`, `architecture`

**Description**:
Add CI checks that prevent architectural violations.

**Acceptance Criteria**:
- [ ] Infra import check in CI
- [ ] Direct I/O check in declarative nodes
- [ ] Deprecation warning check for legacy imports
- [ ] All checks run on PRs

---

#### Issue 7.5: Add migration guide to legacy class docstrings

**Title**: Add migration guides to legacy docstrings
**Type**: Documentation
**Priority**: Low (4)
**Labels**: `documentation`, `deprecation`

**Description**:
Add detailed migration guides in each legacy class docstring.

**Acceptance Criteria**:
- [ ] All 4 legacy classes have migration guide
- [ ] Version info accurate
- [ ] Step-by-step instructions
- [ ] Cross-references using Sphinx syntax

---

#### Issue 7.6: Add pure node static analysis before promotion

**Title**: Create AST-based purity linter for declarative nodes
**Type**: Task
**Priority**: Medium (3)
**Labels**: `ci`, `architecture`, `quality`

**Description**:
Before lifting declarative nodes to default, statically check they do not import: `typing.Any`, `Dict[str, Any]`, legacy mixins, or event bus components.

**Acceptance Criteria**:
- [ ] AST walker blocks `Any`/`Dict[Any]` imports
- [ ] AST walker blocks legacy mixin imports
- [ ] AST walker blocks event bus component imports
- [ ] Pure-node linter rule included in CI
- [ ] Documentation of allowed/disallowed imports

---

#### Issue 7.7: Add future removal simulation mode

**Title**: Create SIMULATE_LEGACY_REMOVAL environment variable
**Type**: Feature
**Priority**: Medium (3)
**Labels**: `architecture`, `testing`, `deprecation`

**Description**:
Avoid surprises in v1.0.0 removal. Allow testing the codebase as if legacy nodes were already removed.

**Acceptance Criteria**:
- [ ] Environment variable `SIMULATE_LEGACY_REMOVAL=true`
- [ ] All legacy imports raise errors instead of warnings when enabled
- [ ] Legacy code paths disabled when enabled
- [ ] Tests ensure no part of core fails when legacy is disabled
- [ ] Documentation for using simulation mode

---

#### Issue 7.8: Create core-purity-failure documentation

**Title**: Create core-purity-failure.md for CI failure interpretation
**Type**: Documentation
**Priority**: Medium (3)
**Labels**: `documentation`, `ci`, `contributor-experience`

**Description**:
Create documentation explaining how to interpret and fix CI purity failures. Prevents contributor thrash.

**Location**: `docs/ci/CORE_PURITY_FAILURE.md`

**Acceptance Criteria**:
- [ ] Explains each purity check (AST scan, import check, inheritance check)
- [ ] Provides examples of failing code and how to fix
- [ ] Links to Core Purity Rules section in MVP doc
- [ ] Included in CONTRIBUTING.md references

---

## Future Phases (Post v0.4.0)

> **IMPORTANT - Repository Boundaries**:
> - **Issues F.1-F.4 (Mixin Migration)**: Remain in `omnibase_core` scope - these are internal refactoring tasks
> - **Issues F.5-F.10 (Runtime Host MVP)**: **DEPRECATED** - Moved to `omnibase_infra` v0.1.0 plan. These are retained here as legacy planning context only. **Do not implement these in `omnibase_core`**
> - **Issues F.11-F.13 (Developer Tooling)**: Remain in `omnibase_core` scope - CLI tools for core development
> **Repository Scope Distinction**:
> - `omnibase_core`: Foundational models, protocols, base classes, and core utilities (no infrastructure dependencies)
> - `omnibase_spi`: Protocol definitions and interfaces (pure abstractions)
> - `omnibase_infra`: Infrastructure implementations - Runtime Host, Kafka/Redis handlers, database adapters, deployment tooling

The following issues are lower priority and should be addressed after the core v0.4.0 refactoring is complete.

### Epic: Mixin Migration (R/H/D Classification)

**Priority**: LOW
**Dependencies**: v0.4.0 release complete

#### Issue F.1: Extract Domain libraries from mixins

**Title**: Extract D-class mixins to pure functions
**Type**: Feature
**Priority**: Low (4)
**Labels**: `architecture`, `refactoring`

**Description**:
Extract 16 D-class (Domain) mixins to pure functions in `utils/` and `domain/`.

---

#### Issue F.2: Create NodeRuntime with core services

**Title**: Implement NodeRuntime absorbing R-class mixins
**Type**: Feature
**Priority**: Low (4)
**Labels**: `architecture`, `new-feature`

**Description**:
Implement `NodeRuntime` class that absorbs 22 R-class (Runtime) mixins as injected services.

---

#### Issue F.3: Create handler protocols in omnibase_spi 🔗 core+spi

**Title**: Define handler protocols in omnibase_spi
**Type**: Feature
**Priority**: Low (4)
**Labels**: `architecture`, `protocol`

**Description**:
Define `ProtocolDiscoveryService`, `ProtocolServiceRegistry`, `ProtocolCLIHandler`, `ProtocolHealthService` in SPI.

---

#### Issue F.4: Move handler implementations to omnibase_infra 🔗 core+spi+infra

**Title**: Move H-class mixins to omnibase_infra
**Type**: Feature
**Priority**: Low (4)
**Labels**: `architecture`, `refactoring`

**Description**:
Move `MixinDiscovery`, `MixinServiceRegistry`, `MixinCLIHandler` implementations to `omnibase_infra/handlers/`.

---

### Epic: Minimal Runtime Host MVP [DEPRECATED - See omnibase_infra]

> **NOTE**: This entire epic has been moved to `omnibase_infra` v0.1.0. Issues F.5-F.10 below are retained for historical context only and should NOT be implemented in `omnibase_core`.

**Priority**: LOW (DEPRECATED)
**Dependencies**: Mixin Migration complete
**Canonical Location**: `omnibase_infra/docs/RUNTIME_HOST_PLAN.md`

#### Issue F.5: Add EnumNodeKind.RUNTIME_HOST enum 🔗 core+spi+infra [DEPRECATED]

**Title**: Add RUNTIME_HOST to EnumNodeKind enum
**Type**: Feature
**Priority**: Low (4)
**Labels**: `architecture`, `new-feature`
**Status**: ✅ COMPLETE - RUNTIME_HOST enum value added to EnumNodeKind in `src/omnibase_core/enums/enum_node_kind.py`

---

#### Issue F.6: Create RuntimeHostContract model 🔗 core+spi+infra [DEPRECATED]

**Title**: Implement RuntimeHostContract Pydantic model
**Type**: Feature
**Priority**: Low (4)
**Labels**: `architecture`, `new-feature`

---

#### Issue F.7: Implement NodeInstance class 🔗 core+spi+infra [DEPRECATED]

**Title**: Create NodeInstance execution wrapper
**Type**: Feature
**Priority**: Low (4)
**Labels**: `architecture`, `new-feature`

---

#### Issue F.8: Implement NodeRuntime class 🔗 core+spi+infra [DEPRECATED]

**Title**: Create NodeRuntime event loop coordinator
**Type**: Feature
**Priority**: Low (4)
**Labels**: `architecture`, `new-feature`

---

#### Issue F.9: Create file-based contract registry 🔗 core+spi+infra [DEPRECATED]

**Title**: Implement FileRegistry for MVP
**Type**: Feature
**Priority**: Low (4)
**Labels**: `architecture`, `new-feature`

---

#### Issue F.10: Create CLI entry point for runtime host 🔗 core+spi+infra [DEPRECATED]

**Title**: Add omninode-runtime-host CLI command
**Type**: Feature
**Priority**: Low (4)
**Labels**: `architecture`, `cli`

---

### Epic: Developer Tooling & Quality of Life

**Priority**: LOW
**Dependencies**: v0.4.0 release complete

#### Issue F.11: Add node build report generator

**Title**: Create omninode-core-report CLI for node status
**Type**: Feature
**Priority**: Low (4)
**Labels**: `cli`, `tooling`, `devex`

**Description**:
After refactoring, contributors need visibility into which nodes are legacy, which are declarative, which contracts are valid, and which adapters applied.

**CLI**: `omninode-core-report`

**Acceptance Criteria**:
- [ ] List of declarative nodes
- [ ] List of legacy nodes
- [ ] Contract version map
- [ ] Contract hash fingerprint table
- [ ] Adapter coverage table
- [ ] JSON and human-readable output formats

---

#### Issue F.12: Add declarative node template generator

**Title**: Create omninode-generate-node CLI for scaffolding
**Type**: Feature
**Priority**: Low (4)
**Labels**: `cli`, `tooling`, `devex`

**Description**:
Use Pydantic + AST generation to generate new node templates. Dramatically reduces cognitive load and enforces consistency.

**CLI**: `omninode-generate-node --type compute --name SummationNode`

**Acceptance Criteria**:
- [ ] Generates contract file
- [ ] Generates node file
- [ ] Generates adapter stub
- [ ] Generates test scaffold
- [ ] Supports all four node types
- [ ] Template follows current conventions

---

#### Issue F.13: Add exhaustive migration readiness checklist

**Title**: Create v0.4.0 release gate checklist
**Type**: Task
**Priority**: Low (4)
**Labels**: `release`, `quality`

**Description**:
Before shipping v0.4.0, require explicit verification of all migration requirements.

**Must-Check Items**:
- [ ] All declarative nodes pure-checked (AST)
- [ ] All tests pass with strict typing
- [ ] All adapters validated with fuzz tests
- [ ] All contracts have fingerprints
- [ ] No legacy symbols leak into declarative namespace
- [ ] Cross-repo compatibility verified

---

#### Issue F.14: Create declarative contract examples library

**Title**: Add curated example contracts under examples/contracts/
**Type**: Documentation
**Priority**: Low (4)
**Labels**: `documentation`, `examples`, `devex`

**Description**:
Curated library of example contracts for onboarding and avoiding tribal knowledge bloat.

**Location**: `examples/contracts/`

**Acceptance Criteria**:
- [ ] Compute contract examples
- [ ] Effect contract examples
- [ ] Reducer FSM contract examples
- [ ] Workflow orchestrator contract examples
- [ ] All example contracts load
- [ ] All example contracts validate
- [ ] All example contracts bind to declarative nodes
- [ ] Tests for all examples

---

## Issue Creation Guidelines

When creating these issues in Linear:

1. **Team**: Omninode
2. **Project**: MVP - OmniNode Platform Foundation
3. **Labels**: Apply as indicated
4. **Priority**: 1=Urgent, 2=High, 3=Normal, 4=Low
5. **Dependencies**: Link related issues
6. **Cross-repo impact**: Tag issues appropriately:

| Impact Level | Description | Example Issues |
|--------------|-------------|----------------|
| `core-only` | No cross-repo dependencies | 0.1-0.5, 1.1-1.5, 5.1-5.4 |
| `core+spi` | Requires SPI protocol alignment | 2.7, 3.1-3.5, F.3 |
| `core+spi+infra` | Requires all three repos | 3.6 (error mapping), F.4-F.10 |

---

## Release Blockers

Not all 71 issues are equally critical for v0.4.0 to ship. The following MUST land before release:

**Phase 0 (All blocking)**:
- 0.1-0.9: Stabilization, versioning, hash registry, purity tests, meta-model

**Phase 1 (All blocking)**:
- 1.1-1.5: Legacy node migration

**Phase 2 (Core blocking)**:
- 2.1-2.6: Declarative node promotion (2.7 handler capabilities is strongly recommended)

**Phase 3 (Core blocking)**:
- 3.1-3.7: Adapters, validators, error taxonomy, fingerprints
- 3.8-3.11: Strongly recommended but not strictly blocking

**Phase 4 (Core blocking)**:
- 4.1-4.4: Migration verification

**Phase 7 (CI blocking)**:
- 7.1-7.4: Deprecation warnings and CI enforcement

**Strongly Recommended (not blocking)**:
- 4.5-4.7, 5.1-5.4, 6.1-6.5, 7.5-7.7, all Future issues

---

## Execution Order

```text
Phase 0 (Stabilization)
    └── Issues 0.1-0.9: Freeze APIs, baseline tests, CI checks,
                        contract versioning, hash registry, purity tests,
                        meta-model specification
            │
            ▼
Phase 1 (Legacy Migration)
    └── Issues 1.1-1.5: Move nodes to legacy/
            │
            ▼
Phase 2 (Declarative Promotion)
    └── Issues 2.1-2.7: Rename, create declarative nodes,
                        handler capability mapping
            │
            ▼
Phase 3 (Contract Adapters)
    └── Issues 3.1-3.11: Create adapters and validators,
                         error taxonomy, fingerprints,
                         fuzz tests, shape enforcement,
                         FSM analysis, workflow validation
            │
            ▼
Phase 4 (Migration Verification)
    └── Issues 4.1-4.7: Verify backward compatibility,
                        contract matrix tests, cross-version comparison,
                        adapter round-trip consistency
            │
            ▼
Phase 5 (Test Updates)
    └── Issues 5.1-5.4: Update all test imports
            │
            ▼
Phase 6 (Documentation)
    └── Issues 6.1-6.5: Update docs with version markers
            │
            ▼
Phase 7 (Deprecation & CI)
    └── Issues 7.1-7.7: Warnings, CI enforcement,
                        purity linter, removal simulation
            │
            ▼
      v0.4.0 RELEASE
            │
            ▼
Future Phases (Post-Release)
    └── F.1-F.10: Mixin migration, Runtime MVP
    └── F.11-F.14: Developer tooling, examples library
```

---

## Clarifications

### NodeCoreBase Status
`NodeCoreBase` remains the abstract foundation for all nodes. It is NOT being renamed or split in v0.4.0. Future consideration may split into:
- Base logic (pure)
- Contract-based logic (validation)

### Declarative Node Dependencies
Declarative nodes depend on:
- `ModelNodeContract` (via constructor)
- Handler protocols (via method injection)
- NOT `RuntimeHostContract` (that's for runtime host only)

---

## Glossary

| Term | Definition |
|------|------------|
| **Declarative Node** | A node implementation that is pure (no I/O), receives contracts via constructor, and relies on adapters for external interactions |
| **Legacy Node** | Pre-v0.4.0 node implementation that may contain I/O and mixins; deprecated and moved to `nodes/legacy/` |
| **Adapter** | Pure transformation layer that converts validated contracts into handler request models |
| **Handler** | Infrastructure component that performs actual I/O operations; lives in `omnibase_infra` |
| **Contract** | YAML/Pydantic model defining a node's interface, inputs, outputs, and capabilities |
| **Fingerprint** | Stable hash of a normalized contract: `<semver>:<sha256-first-12-chars>` |
| **Contract Normalization** | Process of resolving defaults, removing nulls, and applying canonical ordering before fingerprint computation |
| **Handler Capability** | A declared I/O capability (e.g., `http`, `db`, `kv`) that a node requires from the runtime |
| **Purity** | Property of code having no side effects, no I/O, and deterministic outputs |
| **Behavior Equivalence** | Requirement that legacy and declarative nodes produce identical outputs for identical inputs |
| **Runtime Host** | Infrastructure process (`omnibase_infra`) that provides event loop, scheduling, and handler execution |
| **NodeRuntime** | Core orchestrator for node execution; pure, no event loop |

---

**Last Updated**: 2026-01-01 (v9 - MVP Complete, Beta Active)
**Document Owner**: OmniNode Architecture Team
**Linear Project URL**: https://linear.app/omninode/project/mvp-omninode-platform-foundation-d447d3041f8d
**Beta Project URL**: https://linear.app/omninode/project/beta-omninode-platform-hardening-2e713bf49655

---

## v0.4.0 Pre-Flight Checklist

**Use this checklist before cutting the v0.4.0 release.**

### CI Gates (All Must Pass)

- [ ] `mypy --strict` passes on all source files
- [ ] All purity AST checks pass (no logging, caching, threading, etc.)
- [ ] No `omnibase_infra` imports in core
- [ ] No legacy imports outside `nodes/legacy/`
- [ ] No private symbols in `__all__` exports
- [ ] All snapshot tests pass

### Test Coverage

- [ ] Contract validator: >90% coverage
- [ ] Adapters (all 4): >90% coverage
- [ ] Error taxonomy: >90% coverage
- [ ] Legacy compatibility shims: >=60% coverage
- [ ] Overall coverage: >=60%

### Behavior Equivalence

- [ ] All legacy vs declarative equivalence tests pass
- [ ] All partial contract tests pass
- [ ] All error equivalence tests pass
- [ ] `SIMULATE_LEGACY_REMOVAL=true` runs cleanly

### Contract Stability

- [ ] All contracts have fingerprints
- [ ] Fingerprint stability verified across Python 3.10, 3.11, 3.12
- [ ] Contract hash registry populated
- [ ] No fingerprint drift detected in migration

### Documentation

- [ ] CLAUDE.md updated with v0.4.0 changes
- [ ] Node-building tutorials updated
- [ ] Breaking change notice in INDEX.md
- [ ] Upgrade guide created

### Cross-Repo Coordination

- [ ] SPI protocol surfaces frozen
- [ ] Infra team notified of adapter request model shapes
- [ ] omniintelligence migration path documented

### Final Sign-Off

- [ ] Release branch created
- [ ] Version bumped in pyproject.toml
- [ ] Changelog updated
- [ ] All release blockers resolved

---

## Changelog

### v9 (2026-01-01) - MVP Complete, Beta Active

**Project Status Update**:
- **MVP - OmniNode Platform Foundation** marked **COMPLETED** in Linear
- All 71 MVP issues addressed and closed
- Project transitioned to **Beta - OmniNode Platform Hardening** phase
- Updated Linear Backlog Summary with current issue counts
- Added Beta Phase Active Work section with current PRs

**Beta Phase Highlights (42 issues completed)**:
- Type safety improvements: Removing `Any` types across repositories
- OMN-1173: Epic for Tech Debt Audit - Cross-Repository Type Safety & Standards Compliance
- Handler Contract Model & YAML Schema (OMN-1117)
- Pipeline Runner & Hook Registry (OMN-1114)
- Capability Resolution Infrastructure (OMN-1155, OMN-1156)
- Contract Validation Event Schema (OMN-1146)
- Security: SAFE_FIELD_PATTERN validation (OMN-549)

**Current Active Work**:
- 3 PRs in review (OMN-1178, OMN-1176, OMN-1073)
- 6 issues in progress including ModelProjectorContract work
- 25 issues in backlog for Beta phase

---

### v8 (2025-12-03) - Consolidated Architecture

**Executive Summary**:
- Added comprehensive Executive Summary with release criteria and high-risk items
- Added Priority Visual Legend for issue prioritization

**Architectural Invariants Consolidation**:
- Created "Global Architectural Invariants" section with 6 invariant groups (INV-1 through INV-6)
- INV-1: Core Purity Rules (8 rules with IDs P1-P8)
- INV-2: Legacy vs Declarative Separation (4 rules with IDs S1-S4)
- INV-3: Adapter Boundaries (4 rules with IDs A1-A4)
- INV-4: Contract Stability (4 rules with IDs C1-C4)
- INV-5: Cross-Repo Constraints (4 rules with IDs X1-X4)
- INV-6: NodeRuntime Constraints (3 rules with IDs R1-R3)

**Behavior Equivalence Rules**:
- Elevated "Behavior Equivalence Rules" to top-level section
- Consolidated partial contract handling and test environment specifications

**Removed Redundant Sections** (replaced with references):
- Removed standalone "Core Purity Rules" section (now INV-1)
- Removed standalone "Legacy vs Declarative Separation" section (now INV-2)
- Removed standalone "NodeRuntime Constraints" subsection (now INV-6)
- Removed standalone "Adapter Boundary Rules" section (now INV-3)
- Removed standalone "Contract Fingerprint Invariants" section (now INV-4)
- Removed duplicated "Behavior Equivalence Definition" in Phase 3 (now top-level)

**Document Size Reduction**:
- Reduced document by ~15-20% through consolidation
- All phases now reference canonical invariant sections instead of restating rules

---

### v7 (2025-12-03) - Document Restructuring & Navigation

**New Sections**:
- API Stability Contract (public/semi-public/internal modules)
- Minimal Contract Templates (4 contract examples)
- Declarative Node Examples (good/bad patterns)
- Glossary (12 term definitions)
- v0.4.0 Pre-Flight Checklist

**Supporting Documents**:
- Created CONTRACT_STABILITY_SPEC.md for cross-repo contract specification

---

### v6 (2025-12-03) - Architectural Hardening

Added explicit rules and constraints to prevent core pollution:

**Cross-Repo Coordination** - Added:
- Cross-Repo Synchronization Points section with blocking dependencies table
- Release Sequencing Rule: core v0.4.0 must precede infra v0.1.0
- SPI/Core Synchronization table with sync points and timing
- Repository Source of Truth table (8 components mapped to repos)

**Testing Clarity** - Added:
- Behavior Equivalence Definition section before Phase 4
- Formal definitions for output/error/state/non-deterministic equivalence
- Partial Contract Handling rules
- Legacy Test Environment requirements

**Issue Updates**:
- Issue 4.3 updated with formal definition reference (3 new acceptance criteria)
- Issue 6.6 created for contract-to-handler data flow diagram

**Contract Fingerprint & Adapter Boundary Rules**:

**Contract Fingerprint Invariants section** - Added before Issue 3.7:
- Fingerprint stability rules table (4 rules with rationale)
- Normalization Pipeline (4 steps executed before fingerprint computation)

**Adapter Boundary Rules section** - Added after Phase 3 "Source of Truth":
- Adapter constraints table (4 rules with rationale)
- Adapter Responsibility Chain diagram
- Forbidden patterns list: handler.execute() calls, capability checks, URL manipulation, state normalization

**Issue 3.5 (contract validation layer)** - Updated acceptance criteria:
- Validator phases: structural -> semantic -> capability -> fingerprint (in order)
- Error format: `ERR_CODE: message (path.to.field)`
- Validators MUST NOT raise Pydantic `ValidationError` directly
- Contract normalization pipeline runs before fingerprint computation

**Issues 3.1-3.4 (adapters)** - Updated acceptance criteria with forbidden patterns:
- Adapter MUST NOT call handlers directly
- Adapter MUST NOT perform capability inference
- Adapter MUST NOT perform data transformation beyond structural mapping

---

### v5 (2025-12-03) - Core Purity & Legacy Separation Rules

Added explicit core purity rules and declarative/legacy separation rules:

**Core Purity Rules section** - Added after v0.4.0 Non-Goals:
- Declarative Node Constraints table (6 rules with CI enforcement strategy)
- Contract Binding Pattern documentation with code example
- Forbidden patterns: `bind_contract()`, contract mutation, direct handler instantiation

**Legacy vs Declarative Separation section** - Added:
- Import Isolation Rules table (4 directional rules)
- Legacy Namespace Rules (3 requirements)
- Purity Exceptions table (4 component types)

**Issue 0.8 (NodeCoreBase purity contract tests)** - Updated acceptance criteria:
- AST scan blocks: `import logging`, class-level mutable data, caching decorators (`@lru_cache`, `@cache`)
- Inheritance check: only `NodeCoreBase` and `Generic` allowed as base classes

**Issue 1.1 (Create nodes/legacy/ directory structure)** - Updated acceptance criteria:
- `__all__ = []` in `legacy/__init__.py` with explicit dictionary re-exports
- CI check blocks imports of legacy names from outside `nodes/legacy/`

### v4 (2025-12-03) - Workflow/FSM Validation Hardening

Enhanced validation rules and CI enforcement:

**Issue 3.10 (FSM validation)** - Added acceptance criteria:
- Detect ambiguous transitions (state + event -> multiple targets)
- Detect terminal states missing final emissions (if required by contract)
- Validate state names are unique within FSM
- Report all validation failures, not just first

**Issue 3.11 (workflow validation)** - Added acceptance criteria:
- Detect isolated steps (no incoming AND no outgoing edges)
- Validate unique step names within workflow
- Validate all referenced dependencies exist before topological sort
- Report cycle participants with step names, not just "cycle detected"

**CI Enforcement Overview** - Added 4 new checks:
- No top-level executable code (module-level side effects)
- Import-time purity scan (sys, asyncio loops, threading, multiprocessing, path ops)
- Private symbol leak check (no `_private` objects in `__all__`)
- Legacy import isolation (no legacy imports outside nodes/legacy/)

**NodeRuntime Constraints** - Added new section:
- Documents NodeRuntime as pure orchestrator with strict boundaries
- Lists forbidden primitives: asyncio.create_task, threading.Thread, multiprocessing.Process, etc.

**Phase 7 Additions** (Issue 7.8):
- Core purity failure documentation for CI failure interpretation

### v3 (2025-12-03) - Hardening & Validation Additions

Added 20 new issues based on structural risk review:

**Phase 0 Additions** (Issues 0.6-0.9):
- ModelContractVersion with semver semantics
- Contract hash registry module
- NodeCoreBase purity contract tests
- Declarative node meta-model specification

**Phase 2 Additions** (Issue 2.7):
- Required handler capability mapping

**Phase 3 Additions** (Issues 3.6-3.11):
- Error taxonomy for declarative nodes
- Contract fingerprint specification
- Adapter fuzzing tests
- Strict shape enforcement for compute nodes
- FSM simulation tooling for reducers
- Workflow validation with topological sorting

**Phase 4 Additions** (Issues 4.5-4.7):
- Contract compatibility matrix tests
- Cross-version behavioral comparison tests
- Adapter round-trip consistency tests

**Phase 7 Additions** (Issues 7.6-7.7):
- Pure node static analysis before promotion
- Future removal simulation mode

**Future Additions** (Issues F.11-F.14):
- Node build report generator CLI
- Declarative node template generator CLI
- Exhaustive migration readiness checklist
- Declarative contract examples library

### v2 (2025-12-03) - Full Rewrite
- Complete restructure with 49 issues across 7 phases
- Added cross-repository contract rules
- Added deprecation timeline
- Added execution order diagram

### v1 (2025-12-02) - Initial Draft
- Initial issue proposal based on architecture planning documents
