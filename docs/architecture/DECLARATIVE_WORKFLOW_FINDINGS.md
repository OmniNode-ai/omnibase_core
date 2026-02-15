> **Navigation**: [Home](../INDEX.md) > [Architecture](./overview.md) > Declarative Workflow Findings

# Declarative Workflow Architecture - Historical Findings

> **HISTORICAL**: This document captures findings from the initial declarative workflow research conducted in late 2025. The methods and patterns described here have been superseded by the current handler + contract architecture. See [Handler Contract Guide](../contracts/HANDLER_CONTRACT_GUIDE.md) for current patterns.

---

## Current State

The declarative architecture described in this research is now fully implemented. Key outcomes:

- **Nodes are thin shells** that call `super().__init__(container)` and delegate all logic to handlers.
- **YAML contracts** define FSM state machines, workflow definitions, effect subcontracts, and handler routing.
- **Mixins** (`MixinFSMExecution`, `MixinWorkflowExecution`, `MixinEffectExecution`, `MixinHandlerRouting`) provide execution capabilities driven by contract configuration.
- **Imperative methods** referenced below (e.g., `orchestrate_rsd_ticket_lifecycle`, `aggregate_rsd_tickets`) no longer exist. They were replaced by contract-driven execution.

The canonical entry points are:

```python
from omnibase_core.nodes import (
    NodeCompute,
    NodeEffect,
    NodeOrchestrator,
    NodeReducer,
)
```

Each node type is contract-driven by default. Subclasses typically require zero custom Python code.

---

## Original Research Date

- **Date**: 2025-11-16 (initial review), 2025-12-06 (final update)
- **Versions Reviewed**: v0.3.2 through v0.4.0
- **Correlation ID**: `doc-review-declarative-workflows-2025-11-16`

---

## Historical Findings

The sections below preserve the original research findings for reference.

### Infrastructure Review

#### FSM Subcontract Infrastructure

At the time of review, the codebase had comprehensive YAML contract support for declarative workflows and FSMs.

**File**: `src/omnibase_core/models/contracts/subcontracts/model_fsm_subcontract.py`

```python
class ModelFSMSubcontract(BaseModel):
    """FSM (Finite State Machine) subcontract model."""

    state_machine_name: str
    states: list[ModelFSMStateDefinition]
    initial_state: str
    terminal_states: list[str]
    error_states: list[str]
    transitions: list[ModelFSMStateTransition]
    operations: list[ModelFSMOperation]

    persistence_enabled: bool = True
    recovery_enabled: bool = True
    rollback_enabled: bool = True
    checkpoint_interval_ms: int = 30000
    max_checkpoints: int = 10

    conflict_resolution_strategy: str = "priority_based"
    concurrent_transitions_allowed: bool = False
    transition_timeout_ms: int = 5000

    strict_validation_enabled: bool = True
    state_monitoring_enabled: bool = True
    event_logging_enabled: bool = True
```

#### Workflow Coordination Subcontract

**File**: `src/omnibase_core/models/contracts/subcontracts/model_workflow_definition.py`

```python
class ModelWorkflowDefinition(BaseModel):
    """Complete workflow definition."""

    workflow_metadata: ModelWorkflowDefinitionMetadata
    execution_graph: ModelExecutionGraph
    coordination_rules: ModelCoordinationRules
```

#### Subcontract Composition Pattern

Contracts composed subcontracts for clean separation of concerns:

```python
class ModelContractReducer(ModelContractBase):
    state_transitions: object | None  # FSM subcontract
    event_type: ModelEventTypeSubcontract | None
    aggregation: ModelAggregationSubcontract | None
    state_management: ModelStateManagementSubcontract | None
    caching: ModelCachingSubcontract | None
    workflow_coordination: ModelWorkflowCoordinationSubcontract | None
```

### Node Implementations at Time of Review

At the time of initial review (v0.3.2), both `NodeOrchestrator` and `NodeReducer` contained significant imperative Python code:

**NodeOrchestrator** had hardcoded methods including:
- `_execute_sequential_workflow()`
- `_execute_parallel_workflow()`
- `_execute_batch_workflow()`
- `orchestrate_rsd_ticket_lifecycle()` (domain-specific)
- `emit_action()`
- `register_condition_function()`

**NodeReducer** had hardcoded methods including:
- `aggregate_rsd_tickets()` (domain-specific)
- `normalize_priority_scores()`
- `resolve_dependency_cycles()`
- `register_reduction_function()`
- `_process_batch()`, `_process_incremental()`, `_process_windowed()`

These methods were all removed during the v0.4.0 refactor to the current contract-driven architecture.

### Mixin System at Time of Review

The following mixins were identified as available:

- `MixinRetry` - Retry logic with backoff strategies
- `MixinHealthCheck` - Health monitoring
- `MixinCaching` - Caching with TTL and eviction
- `MixinEventBus` - Event publishing
- `MixinCircuitBreaker` - Failure protection
- `MixinLogging` - Structured logging
- `MixinMetrics` - Performance tracking
- `MixinSecurity` - Security and validation
- `MixinSerialization` - Data serialization
- `MixinDagSupport` - Workflow event participation

The FSM and Workflow execution mixins (`MixinFSMExecution`, `MixinWorkflowExecution`) were implemented in v0.3.2 and became the primary execution mechanism in v0.4.0.

### Gap Analysis at Time of Review

| Component | v0.3.2 Status | v0.4.0 Resolution |
|-----------|---------------|-------------------|
| FSM Subcontracts | Infrastructure complete, adoption partial | Primary pattern |
| Workflow Subcontracts | Infrastructure complete, adoption partial | Primary pattern |
| FSM Runtime | Implemented via mixin | Integrated into NodeReducer |
| Workflow Runtime | Implemented via mixin | Integrated into NodeOrchestrator |
| Declarative Examples | Limited | Available in contract YAML files |
| Documentation | Partial | Updated across guides |

### Key Recommendations (Historical)

The following recommendations were made during the research. All critical items have been addressed:

1. **Runtime Execution** (COMPLETED v0.3.2): Created `MixinFSMExecution` and `MixinWorkflowExecution` with pure utility functions.

2. **Update Node Implementations** (COMPLETED v0.4.0): `NodeReducer` and `NodeOrchestrator` became the primary declarative implementations. The "Declarative" suffix was removed.

3. **Workflow/FSM Mixins** (COMPLETED v0.3.2): Created and integrated into the node base classes.

---

## Conclusion

This research identified the gap between existing contract infrastructure and its adoption in node implementations. The gap was closed in v0.4.0 when all nodes transitioned to contract-driven execution. The imperative methods documented here no longer exist in the codebase.

For current architecture documentation, see:
- [ONEX Four-Node Architecture](ONEX_FOUR_NODE_ARCHITECTURE.md)
- [Contract System](CONTRACT_SYSTEM.md)
- [Handler Contract Guide](../contracts/HANDLER_CONTRACT_GUIDE.md)
- [Node Building Guide](../guides/node-building/README.md)

---

**Originally Written**: 2025-11-16
**Last Substantive Update**: 2025-12-06
**Archived**: 2026-02-14
