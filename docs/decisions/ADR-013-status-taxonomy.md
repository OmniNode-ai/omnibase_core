> **Navigation**: [Home](../index.md) > [Decisions](README.md) > ADR-013

# ADR-013: Status Taxonomy

**Status**: Accepted
**Date**: 2026-01-13
**Context**: OMN-1312 - Status Taxonomy ADR
**Correlation ID**: `adr-013-status-taxonomy`

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Context](#context)
3. [Decision](#decision)
4. [Category Definitions](#category-definitions)
   - [Execution Status](#1-execution-status)
   - [Operation Status](#2-operation-status)
   - [Workflow Status](#3-workflow-status)
   - [Health Status](#4-health-status)
   - [Lifecycle Status](#5-lifecycle-status)
   - [Registration Status](#6-registration-status)
5. [Deferred: Mapping Rules](#deferred-mapping-rules)
6. [Non-Goals](#non-goals)
7. [Consequences](#consequences)
8. [Related Documents](#related-documents)

---

## Executive Summary

**Decision**: Define six canonical status categories with designated authoritative enums for each domain.

**Key Benefits**:
- Clear separation of concerns between status domains
- Single source of truth for each status category
- Consistent helper methods across all status enums
- Enables future consolidation of ad-hoc status values

**Categories**:

| Category | Canonical Enum | Purpose |
|----------|---------------|---------|
| Execution | `EnumExecutionStatus` | Task/job lifecycle |
| Operation | `EnumOperationStatus` | API/action results |
| Workflow | `EnumWorkflowState` | Orchestration state |
| Health | `EnumNodeHealthStatus` | Component monitoring |
| Lifecycle | `EnumNodeLifecycleStatus` | Init/disposal phases |
| Registration | `EnumToolRegistrationStatus` | Registry state |

**Impact**: Establishes taxonomy for 50+ status-related enums across omnibase_core.

---

## Context

### Problem Statement

The omnibase_core codebase contains numerous status-related enums that have evolved organically. Without a clear taxonomy, developers face several challenges:

1. **Ambiguity**: When should `COMPLETED` vs `SUCCESS` vs `DONE` be used?
2. **Overlap**: Multiple enums cover similar domains with inconsistent values
3. **Discovery**: No clear guidance on which enum to use for a given scenario
4. **Inconsistency**: Some enums have helper methods, others do not

### Current State

Analysis of the codebase reveals six distinct status domains:

- **Execution**: Task/job/process lifecycle tracking (PENDING -> RUNNING -> COMPLETED/FAILED)
- **Operation**: Discrete action outcomes (SUCCESS/FAILED for API calls)
- **Workflow**: Multi-step orchestration states (includes PAUSED for long-running workflows)
- **Health**: Component health monitoring (HEALTHY -> DEGRADED -> UNHEALTHY -> CRITICAL)
- **Lifecycle**: Initialization/disposal phases (INITIALIZING -> READY, CLEANING_UP -> CLEANED_UP)
- **Registration**: Service/tool registry state (REGISTERED, DEPRECATED, DISABLED)

### Design Principles

1. **Single Canonical Enum**: Each category has ONE authoritative enum
2. **Domain Separation**: Categories do not overlap in purpose
3. **Helper Methods**: All canonical enums provide semantic helpers (is_terminal(), is_active(), etc.)
4. **Future Consolidation**: This taxonomy enables migration of ad-hoc values to canonical enums

---

## Decision

**We establish six status categories with designated canonical enums.**

Each canonical enum serves as the authoritative source for its domain. Domain-specific variants may exist for specialized contexts but should align with the canonical enum's semantics.

---

## Category Definitions

### 1. Execution Status

**Purpose**: Track task, job, or process lifecycle from initiation to completion.

**Canonical Enum**: `EnumExecutionStatus`
**Location**: `src/omnibase_core/enums/enum_execution_status.py`

**Values**:

| Value | Description |
|-------|-------------|
| `PENDING` | Task queued, not yet started |
| `RUNNING` | Task actively executing |
| `COMPLETED` | Task finished successfully (generic success) |
| `SUCCESS` | Task completed successfully (explicit success) |
| `FAILED` | Task completed with failure |
| `SKIPPED` | Task intentionally not executed |
| `CANCELLED` | Task terminated by user/system |
| `TIMEOUT` | Task exceeded time limit |
| `PARTIAL` | Some steps succeeded, others failed (terminal state) |

**COMPLETED vs SUCCESS/FAILED Relationship**:
- `COMPLETED` and `SUCCESS` are both successful outcomes (`is_successful()` returns True for both)
- Use `COMPLETED` for generic "task finished successfully" scenarios
- Use `SUCCESS` when you need explicit success/failure distinction alongside `FAILED`
- `FAILED` indicates task completed with an error (mutually exclusive with COMPLETED/SUCCESS)

**Helper Methods**:
- `is_terminal()` - Returns True for COMPLETED, SUCCESS, FAILED, SKIPPED, CANCELLED, TIMEOUT, PARTIAL
- `is_active()` - Returns True for PENDING, RUNNING
- `is_successful()` - Returns True for COMPLETED, SUCCESS
- `is_failure()` - Returns True for FAILED, TIMEOUT
- `is_skipped()` - Returns True for SKIPPED
- `is_running()` - Returns True for RUNNING (subset of is_active)
- `is_cancelled()` - Returns True for CANCELLED
- `is_partial()` - Returns True for PARTIAL

**Use Cases**:
- Node execution tracking
- Background job status
- Test execution results
- Pipeline step outcomes

---

### 2. Operation Status

**Purpose**: Report discrete action or API call outcomes.

**Canonical Enum**: `EnumOperationStatus`
**Location**: `src/omnibase_core/enums/enum_operation_status.py`

**Values**:

| Value | Description |
|-------|-------------|
| `SUCCESS` | Operation completed successfully |
| `FAILED` | Operation failed |
| `IN_PROGRESS` | Operation currently executing |
| `CANCELLED` | Operation cancelled |
| `PENDING` | Operation queued |
| `TIMEOUT` | Operation exceeded time limit |

**Helper Methods**:
- `is_terminal()` - Returns True for SUCCESS, FAILED, CANCELLED, TIMEOUT
- `is_active()` - Returns True for IN_PROGRESS
- `is_successful()` - Returns True for SUCCESS

**Use Cases**:
- API response status
- Service call outcomes
- Database operation results
- File system operations

**Distinction from Execution Status**:
- **ExecutionStatus**: Tracks lifecycle of long-running tasks (PENDING -> RUNNING -> COMPLETED)
- **OperationStatus**: Reports outcome of discrete actions (call -> SUCCESS/FAILED)

---

### 3. Workflow Status

**Purpose**: Track multi-step workflow orchestration state.

**Canonical Enum**: `EnumWorkflowState`
**Location**: `src/omnibase_core/enums/enum_orchestrator_types.py`
**Exports**: `omnibase_core.nodes`, `omnibase_core.enums`

**Values**:

| Value | Description |
|-------|-------------|
| `PENDING` | Workflow not started |
| `RUNNING` | Workflow actively executing steps |
| `PAUSED` | Workflow suspended (reserved for v1.1) |
| `COMPLETED` | Workflow finished successfully |
| `FAILED` | Workflow terminated with error |
| `CANCELLED` | Workflow terminated by user/system |

**Use Cases**:
- ORCHESTRATOR node state tracking
- Multi-step pipeline status
- Long-running workflow coordination
- Saga pattern state management

**Note**: `PAUSED` is reserved for v1.1 to support workflow suspension/resumption patterns.

---

### 4. Health Status

**Purpose**: Report component, node, or service health for monitoring and alerting.

**Canonical Enum**: `EnumNodeHealthStatus`
**Location**: `src/omnibase_core/enums/enum_node_health_status.py`

**Values**:

| Value | Description |
|-------|-------------|
| `HEALTHY` | Component operating normally |
| `DEGRADED` | Component functional but impaired |
| `UNHEALTHY` | Component not functioning correctly |
| `CRITICAL` | Component in critical failure state |
| `UNKNOWN` | Health status cannot be determined |

**Domain-Specific Variants**:

| Variant | Purpose |
|---------|---------|
| `EnumServiceHealthStatus` | External service health |
| `EnumToolHealthStatus` | Tool/plugin health |
| `EnumRegistryHealthStatus` | Registry health |

**Use Cases**:
- Health check endpoints
- Circuit breaker state
- Load balancer decisions
- Monitoring dashboards
- Alerting thresholds

**Severity Ordering**: HEALTHY > DEGRADED > UNHEALTHY > CRITICAL

---

### 5. Lifecycle Status

**Purpose**: Track initialization and disposal phases of components.

**Canonical Enum**: `EnumNodeLifecycleStatus`
**Location**: `src/omnibase_core/enums/enum_node_lifecycle_status.py`

**Values**:

| Value | Description |
|-------|-------------|
| `INITIALIZING` | Component starting up |
| `INITIALIZED` | Component initialization complete |
| `READY` | Component ready to accept work |
| `FAILED` | Initialization or operation failed |
| `CLEANING_UP` | Component shutting down |
| `CLEANED_UP` | Cleanup complete |
| `CLEANUP_FAILED` | Cleanup encountered errors |

**Helper Methods**:
- `is_terminal()` - Returns True for CLEANED_UP, CLEANUP_FAILED, FAILED
- `is_active()` - Returns True for INITIALIZING, READY, CLEANING_UP
- `is_error()` - Returns True for FAILED, CLEANUP_FAILED

**Use Cases**:
- Node initialization tracking
- Resource acquisition/release
- Graceful shutdown coordination
- Dependency injection lifecycle

**State Flow**:

```text
INITIALIZING -> INITIALIZED -> READY -> CLEANING_UP -> CLEANED_UP
                    |                        |
                    v                        v
                 FAILED              CLEANUP_FAILED
```

---

### 6. Registration Status

**Purpose**: Track service, node, or tool registration lifecycle.

**Canonical Enum**: `EnumToolRegistrationStatus`
**Location**: `src/omnibase_core/enums/enum_tool_registration_status.py`

**Values**:

| Value | Description |
|-------|-------------|
| `REGISTERED` | Successfully registered and active |
| `PENDING` | Registration in progress |
| `FAILED` | Registration failed |
| `DEPRECATED` | Registered but marked for removal |
| `DISABLED` | Registered but not active |

**Use Cases**:
- Service discovery registration
- Plugin/tool registration
- Feature flag states
- API version lifecycle

**State Transitions**:
- PENDING -> REGISTERED (success)
- PENDING -> FAILED (error)
- REGISTERED -> DEPRECATED (sunset)
- REGISTERED -> DISABLED (temporary disable)
- DEPRECATED -> DISABLED (final disable)

---

## Deferred: Mapping Rules

**Explicitly out of scope for this ADR**: Cross-category status mapping rules.

Future ADR(s) should address:

1. **Execution-to-Operation Mapping**: When an ExecutionStatus should map to an OperationStatus (e.g., `COMPLETED` + `SUCCESS` -> `SUCCESS`)

2. **Workflow-to-Execution Mapping**: How WorkflowState values relate to individual step ExecutionStatus values

3. **Health-to-Lifecycle Mapping**: How HealthStatus should change during lifecycle transitions (e.g., INITIALIZING -> UNKNOWN health)

4. **Aggregation Rules**: How to compute aggregate status from multiple component statuses

**Rationale for Deferral**:
- Mapping rules require implementation experience
- Current focus is establishing the taxonomy
- Mapping logic may vary by context

---

## Non-Goals

This ADR explicitly does NOT address:

1. **Exhaustive Enumeration**: Not all status values in the codebase are listed; only canonical enums are defined

2. **FSM Transition Rules**: Detailed state machine definitions for each category (see category-specific documentation)

3. **Implementation Details**: How status transitions are triggered or enforced in code

4. **Migration Timeline**: When existing ad-hoc status values should be consolidated

5. **Error Code Mapping**: Relationship between status values and `EnumCoreErrorCode`

6. **Persistence Schema**: Database column types or serialization formats

---

## Consequences

### Positive Consequences

1. **Clarity**
   - Developers know which enum to use for each scenario
   - Clear separation between similar-sounding concepts (Execution vs Operation)
   - Single source of truth per domain

2. **Consolidation Path**
   - Taxonomy enables future migration of ad-hoc status values
   - New code can use canonical enums from the start
   - Reduces enum proliferation

3. **Consistency**
   - All canonical enums follow same helper method pattern
   - Predictable semantics across categories
   - Easier testing and validation

4. **Documentation**
   - Self-documenting via enum docstrings
   - ADR serves as authoritative reference
   - Onboarding simplified

### Negative Consequences

1. **Migration Effort**
   - Existing code using non-canonical enums may need updates
   - Some domain-specific variants may have values not in canonical enum
   - Requires careful analysis of edge cases

2. **Learning Curve**
   - Developers must learn six categories
   - Distinction between categories may not be immediately obvious
   - Requires reading this ADR

3. **Rigidity**
   - New status values must fit into existing categories
   - May require ADR amendment for new categories
   - Could constrain future design

### Risk Mitigation

**Migration**:
- Use deprecation warnings for non-canonical enums
- Provide helper functions for mapping to canonical enums
- Document migration path in separate guide

**Learning Curve**:
- Add quick-reference table to CLAUDE.md
- Include examples in enum docstrings
- Create decision tree for enum selection

---

## Related Documents

### Internal Documentation

- See `CLAUDE.md` (project root) - Key Patterns and project conventions
- [Conventions](../conventions/) - Naming standards and guidelines
- [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) - Node lifecycle context

### Canonical Enum Locations

| Category | Path |
|----------|------|
| Execution | `src/omnibase_core/enums/enum_execution_status.py` |
| Operation | `src/omnibase_core/enums/enum_operation_status.py` |
| Workflow | `src/omnibase_core/enums/enum_orchestrator_types.py` |
| Health | `src/omnibase_core/enums/enum_node_health_status.py` |
| Lifecycle | `src/omnibase_core/enums/enum_node_lifecycle_status.py` |
| Registration | `src/omnibase_core/enums/enum_tool_registration_status.py` |

### Related ADRs

- [ADR-012: Validator Error Handling](ADR-012-VALIDATOR-ERROR-HANDLING.md) - Error handling patterns

---

**Last Updated**: 2026-01-13
**Author**: Claude Code (Polymorphic Agent)
**Context**: OMN-1312 - Status Taxonomy ADR
**Status**: Accepted
