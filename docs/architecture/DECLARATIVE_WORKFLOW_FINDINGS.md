# Declarative Workflow Architecture - Findings and Recommendations

> **Date**: 2025-11-16
> **Version**: v0.3.2
> **Correlation ID**: `doc-review-declarative-workflows-2025-11-16`
> **Status**: ARCHITECTURE REVIEW

---

## Executive Summary

This document summarizes findings from a comprehensive review of omnibase_core's declarative workflow and FSM capabilities. **UPDATED (v0.3.2)**: The review confirms that **YAML contract infrastructure AND mixin-based runtime execution are both complete**, but **current node implementations don't fully leverage these declarative patterns yet**.

### Key Finding: Runtime Implemented, Adoption Pending

✅ **Infrastructure EXISTS**: Complete Pydantic models for FSM and workflow subcontracts
✅ **Runtime IMPLEMENTED (v0.3.2)**: Mixin-based execution via `MixinFSMExecution` and `MixinWorkflowExecution`
⚠️ **Adoption GAP**: NodeOrchestrator and NodeReducer still primarily use imperative Python code
📝 **Documentation NEEDS**: Emphasize mixin-based declarative patterns with comprehensive examples

---

## Table of Contents

1. [Infrastructure Review](#infrastructure-review)
2. [Current Node Implementations](#current-node-implementations)
3. [Mixin System Review](#mixin-system-review)
4. [Gap Analysis](#gap-analysis)
5. [Recommendations](#recommendations)
6. [Implementation Roadmap](#implementation-roadmap)

---

## Infrastructure Review

### ✅ YAML Contract System - COMPLETE

The omnibase_core codebase has **comprehensive YAML contract support** for declarative workflows and FSMs:

#### 1. FSM Subcontract Infrastructure

**File**: `src/omnibase_core/models/contracts/subcontracts/model_fsm_subcontract.py`

```python
class ModelFSMSubcontract(BaseModel):
    """FSM (Finite State Machine) subcontract model."""

    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Complete FSM definition
    state_machine_name: str
    states: list[ModelFSMStateDefinition]
    initial_state: str
    terminal_states: list[str]
    error_states: list[str]
    transitions: list[ModelFSMStateTransition]
    operations: list[ModelFSMOperation]

    # Persistence and recovery
    persistence_enabled: bool = True
    recovery_enabled: bool = True
    rollback_enabled: bool = True
    checkpoint_interval_ms: int = 30000
    max_checkpoints: int = 10

    # Conflict resolution
    conflict_resolution_strategy: str = "priority_based"
    concurrent_transitions_allowed: bool = False
    transition_timeout_ms: int = 5000

    # Validation and monitoring
    strict_validation_enabled: bool = True
    state_monitoring_enabled: bool = True
    event_logging_enabled: bool = True
```

**Capabilities**:
- Complete state machine definitions
- State entry/exit actions
- Transition conditions and guards
- Atomic operations with rollback support
- Persistence and checkpoint management
- Conflict resolution strategies
- Comprehensive validation

#### 2. Workflow Coordination Subcontract

**File**: `src/omnibase_core/models/contracts/subcontracts/model_workflow_definition.py`

```python
class ModelWorkflowDefinition(BaseModel):
    """Complete workflow definition."""

    workflow_metadata: ModelWorkflowDefinitionMetadata
    execution_graph: ModelExecutionGraph
    coordination_rules: ModelCoordinationRules
```

**Supporting Models**:
- `ModelWorkflowConfig` - Execution modes (sequential, parallel, mixed)
- `ModelExecutionGraph` - DAG of workflow steps
- `ModelCoordinationRules` - Inter-step coordination
- `ModelWorkflowStep` - Individual step definitions

#### 3. Subcontract Composition Pattern

**File**: `src/omnibase_core/models/contracts/model_contract_reducer.py`

```python
class ModelContractReducer(ModelContractBase):
    """Contract model for NodeReducer implementations."""

    # Subcontract composition - CLEAN SEPARATION
    state_transitions: object | None  # FSM subcontract
    event_type: ModelEventTypeSubcontract | None
    aggregation: ModelAggregationSubcontract | None
    state_management: ModelStateManagementSubcontract | None
    caching: ModelCachingSubcontract | None
    workflow_coordination: ModelWorkflowCoordinationSubcontract | None
```

**Pattern**: Nodes compose subcontracts instead of implementing custom logic.

### ✅ Validation and Type Safety

All subcontract models include:
- **Pydantic v2 validation** with strict mode
- **Interface versioning** (INTERFACE_VERSION) for code generation stability
- **Zero tolerance for Any types** - strong typing throughout
- **UUID correlation tracking** for full traceability
- **Comprehensive error handling** with ModelOnexError

---

## Current Node Implementations

### ⚠️ NodeOrchestrator - CODE-HEAVY IMPLEMENTATION

**File**: `src/omnibase_core/nodes/node_orchestrator.py`

**Current State**: Primarily imperative Python code

**Key Methods**:
```python
async def process(self, input_data: ModelOrchestratorInput) -> ModelOrchestratorOutput:
    """Execute workflow coordination with thunk emission."""
    # Lines 142-267: Imperative workflow execution
    if input_data.execution_mode == EnumExecutionMode.SEQUENTIAL:
        result = await self._execute_sequential_workflow(...)
    elif input_data.execution_mode == EnumExecutionMode.PARALLEL:
        result = await self._execute_parallel_workflow(...)
    # ...
```

**Built-in Methods** (Hardcoded Logic):
- `_execute_sequential_workflow()` (lines 651-753)
- `_execute_parallel_workflow()` (lines 755-900)
- `_execute_batch_workflow()` (lines 902-935)
- `orchestrate_rsd_ticket_lifecycle()` (lines 274-331)
- `emit_action()` (lines 333-404)
- `register_condition_function()` (lines 406-447)

**Observation**: While the infrastructure exists for declarative workflows, NodeOrchestrator currently implements workflow logic imperatively in Python.

### ⚠️ NodeReducer - CODE-HEAVY IMPLEMENTATION

**File**: `src/omnibase_core/nodes/node_reducer.py`

**Current State**: Primarily imperative Python code with custom reduction functions

**Key Patterns**:
```python
def __init__(self, container: ModelONEXContainer) -> None:
    """PURE FSM PATTERN: No mutable instance state."""
    super().__init__(container)

    # Configuration
    self.reduction_functions: dict[EnumReductionType, Callable] = {}
    self.reduction_metrics: dict[str, dict[str, float]] = defaultdict(...)
```

**Built-in Methods** (Hardcoded Logic):
- `aggregate_rsd_tickets()` (lines 254-297)
- `normalize_priority_scores()` (lines 299-330)
- `resolve_dependency_cycles()` (lines 332-358)
- `register_reduction_function()` (lines 360-401)
- `_process_batch()`, `_process_incremental()`, `_process_windowed()` (lines 505-677)

**Positive**: Uses ModelIntent pattern (lines 164-220) for side effect emission - shows FSM thinking!

**Observation**: While reduction logic is more generic, it still requires custom Python functions instead of YAML-driven configuration.

---

## Mixin System Review

### ✅ Mixins Provide Cross-Cutting Concerns

**File**: `src/omnibase_core/mixins/mixin_metadata.yaml` (2463 lines)

**Available Mixins**:
- `MixinRetry` - Retry logic with backoff strategies
- `MixinHealthCheck` - Health monitoring
- `MixinCaching` - Caching with TTL and eviction
- `MixinEventBus` - Event publishing
- `MixinCircuitBreaker` - Failure protection
- `MixinLogging` - Structured logging
- `MixinMetrics` - Performance tracking
- `MixinSecurity` - Security and validation
- `MixinSerialization` - Data serialization

**File**: `src/omnibase_core/mixins/mixin_workflow_support.py`

```python
class MixinDagSupport:
    """Mixin providing Workflow event support for ONEX tools."""

    def emit_dag_completion_event(self, result, status, error_message=None):
        """Emit Workflow completion event for workflow coordination."""
```

### ✅ FSM/Workflow Execution Mixins - IMPLEMENTED (v0.3.2)

**Implemented** (Mixin-based approach):
- ✅ `MixinFSMExecution` - FSM execution from subcontract (`mixins/mixin_fsm_execution.py`)
- ✅ `MixinWorkflowExecution` - Workflow execution from subcontract (`mixins/mixin_workflow_execution.py`)
- ✅ FSM Runtime - Pure functions in `utils/fsm_executor.py`
- ✅ Workflow Runtime - Pure functions in `utils/workflow_executor.py`

**Pattern**: Mixins delegate to pure utility functions for execution. Nodes compose mixins instead of implementing custom FSM/workflow logic.

**Also Available**: `MixinDagSupport` for workflow EVENT participation.

---

## Gap Analysis

### Infrastructure vs. Implementation

| Component | Infrastructure | Implementation | Gap |
|-----------|---------------|----------------|-----|
| **FSM Subcontracts** | ✅ Complete | ⚠️ Available (v0.3.2) | MEDIUM |
| **Workflow Subcontracts** | ✅ Complete | ⚠️ Available (v0.3.2) | MEDIUM |
| **Pydantic Validation** | ✅ Complete | ✅ Working | NONE |
| **Contract Composition** | ✅ Complete | ⚠️ Partial | MEDIUM |
| **FSM Runtime** | ✅ **IMPLEMENTED** (v0.3.2) | ✅ **Mixin-based** | LOW |
| **Workflow Runtime** | ✅ **IMPLEMENTED** (v0.3.2) | ✅ **Mixin-based** | LOW |
| **Declarative Examples** | ⚠️ Limited | ⚠️ Limited | MEDIUM |
| **Documentation** | ⚠️ Partial | ⚠️ Needs Updates | MEDIUM |

**Note**: FSM and Workflow runtimes implemented via mixin-based approach (`MixinFSMExecution`, `MixinWorkflowExecution`) with pure utility functions (`utils/fsm_executor.py`, `utils/workflow_executor.py`).

### ✅ Implemented Components (v0.3.2)

#### 1. FSM Runtime - IMPLEMENTED via Mixin Pattern

**Status**: ✅ **COMPLETE** (Mixin-based approach)

**Implementation**:
```python
# src/omnibase_core/mixins/mixin_fsm_execution.py
class MixinFSMExecution:
    """Mixin providing FSM execution from YAML contracts."""

    # Uses pure functions from utils/fsm_executor.py
    # Delegates to: execute_transition(), validate_fsm_contract(), etc.
```

**Runtime Functions** (`utils/fsm_executor.py`):
```python
def execute_transition(
    fsm: ModelFSMSubcontract,
    current_state: str,
    trigger: str,
    context: dict[str, Any]
) -> FSMTransitionResult:
    """Execute FSM transition declaratively (pure function)."""
```

#### 2. Workflow Runtime - IMPLEMENTED via Mixin Pattern

**Status**: ✅ **COMPLETE** (Mixin-based approach)

**Implementation**:
```python
# src/omnibase_core/mixins/mixin_workflow_execution.py
class MixinWorkflowExecution:
    """Mixin providing workflow execution from YAML contracts."""

    # Uses pure functions from utils/workflow_executor.py
    # Delegates to workflow execution logic
```

**Runtime Functions** (`utils/workflow_executor.py`):
```python
# Pure functions for workflow execution
# Handles sequential, parallel, and mixed execution modes
```

#### 3. Remaining Gaps

**Partial**: Declarative Node Base Classes

**Current**: Nodes compose mixins for FSM/workflow capabilities
```python
# Current pattern (v0.3.2)
class NodeMyReducer(NodeCoreBase, MixinFSMExecution):
    """Reducer with declarative FSM support."""
    # FSM execution via mixin - no custom code needed
```

**Future** (Planned for Phase 3):
```python
# Planned declarative base classes
class NodeReducerDeclarative(NodeCoreBase):
    """Fully declarative reducer - YAML contract only."""
```

---

## Recommendations

### 1. ✅ Runtime Execution - COMPLETE (v0.3.2)

**Priority**: ~~CRITICAL~~ **COMPLETED**
**Status**: ✅ Implemented via mixin pattern

**Completed** (v0.3.2):
- ✅ Implemented `MixinFSMExecution` for FSM runtime
- ✅ Implemented `MixinWorkflowExecution` for workflow runtime
- ✅ Pure utility functions in `utils/fsm_executor.py` and `utils/workflow_executor.py`
- ✅ Unit tests for runtime functions

### 2. Update Node Implementations

**Priority**: HIGH
**Timeline**: Sprint 2

**Tasks**:
- [ ] Create `NodeOrchestratorDeclarative` base class
- [ ] Create `NodeReducerDeclarative` base class
- [ ] Migrate existing orchestrators to use declarative pattern
- [ ] Deprecate imperative methods in favor of YAML contracts

### 3. Add Declarative Examples

**Priority**: HIGH
**Timeline**: Sprint 2

**Tasks**:
- [ ] Create example YAML contracts for orchestrator workflows
- [ ] Create example YAML contracts for reducer FSMs
- [ ] Add examples to `docs/examples/`
- [ ] Update tutorials to show YAML-first approach

### 4. Update Documentation

**Priority**: HIGH
**Timeline**: Sprint 2

**Tasks**:
- [ ] Update `docs/guides/node-building/06_ORCHESTRATOR_NODE_TUTORIAL.md`
  - Emphasize YAML workflow contracts
  - Minimize custom Python code examples
  - Show declarative pattern first
- [ ] Update `docs/guides/node-building/05_REDUCER_NODE_TUTORIAL.md`
  - Emphasize FSM subcontracts
  - Show YAML-driven state management
  - Minimize custom reduction functions
- [ ] Create `docs/guides/DECLARATIVE_WORKFLOWS.md`
- [ ] Create `docs/guides/FSM_SUBCONTRACTS.md`

### 5. ✅ Workflow/FSM Mixins - COMPLETE (v0.3.2)

**Priority**: ~~MEDIUM~~ **COMPLETED**
**Status**: ✅ Implemented and available

**Completed** (v0.3.2):
- ✅ Created `MixinFSMExecution` for FSM-driven nodes
- ✅ Created `MixinWorkflowExecution` for workflow-driven nodes
- ✅ Updated mixin_metadata.yaml with new mixins
- ⚠️ Mixin examples - needs more documentation

---

## Implementation Roadmap

### ✅ Sprint 1: Runtime Services - COMPLETE (v0.3.2)

**Goal**: ~~Create the missing runtime interpreters~~ **COMPLETED**

**Status**: ✅ Implemented via mixin-based approach

1. **✅ FSM Execution - COMPLETE**
   ```python
   # src/omnibase_core/utils/fsm_executor.py
   def execute_transition(fsm: ModelFSMSubcontract, ...):
       # ✅ Validate current state
       # ✅ Check transition conditions
       # ✅ Execute entry/exit actions
       # ✅ Update state
       # ✅ Handle rollback on failure (via intents)
   ```

2. **✅ Workflow Execution - COMPLETE**
   ```python
   # src/omnibase_core/utils/workflow_executor.py
   # ✅ Build execution graph
   # ✅ Execute steps based on mode (sequential, parallel, mixed)
   # ✅ Handle dependencies
   # ✅ Coordinate with FSM executor for stateful steps
   ```

3. **✅ Mixin Pattern Implementation**
   ```python
   # Mixins provide execution capabilities
   # src/omnibase_core/mixins/mixin_fsm_execution.py
   # src/omnibase_core/mixins/mixin_workflow_execution.py
   ```

### Sprint 2: Declarative Nodes & Documentation (Week 3-4)

**Goal**: Create declarative base classes and update docs

1. **Declarative Base Classes**
   - `NodeOrchestratorDeclarative` - YAML-driven workflows
   - `NodeReducerDeclarative` - YAML-driven FSM/aggregation

2. **Documentation Updates**
   - Emphasize declarative patterns FIRST
   - Show imperative patterns as "advanced customization"
   - Add YAML contract examples to all tutorials

3. **Example YAML Contracts**
   ```yaml
   # examples/contracts/workflow_data_processing.yaml
   node_type: ORCHESTRATOR
   workflow_coordination:
     execution_mode: sequential
     steps:
       - step_name: fetch_data
         action_type: EFFECT
         target_node_type: NodeEffect
       - step_name: transform_data
         action_type: COMPUTE
         target_node_type: NodeCompute
       - step_name: aggregate_results
         action_type: REDUCE
         target_node_type: NodeReducer
   ```

### Sprint 3: Advanced Features & Examples (Week 5-6)

**Goal**: Complete the declarative ecosystem

1. **✅ Execution Mixins - COMPLETE (v0.3.2)**
   - ✅ `MixinFSMExecution`
   - ✅ `MixinWorkflowExecution`

2. **⚠️ Advanced Examples - IN PROGRESS**
   - [ ] Complex multi-branch workflows
   - [ ] FSM with conditional transitions
   - [ ] Parallel workflow execution

3. **⚠️ Testing & Validation - PARTIAL**
   - ✅ Unit tests for runtime functions
   - [ ] Integration tests for declarative patterns
   - [ ] Performance benchmarks
   - [ ] Migration guide for existing code

---

## Conclusion

The omnibase_core codebase has **excellent infrastructure** for declarative workflows and FSMs:
- ✅ Complete FSM subcontract models
- ✅ Complete workflow coordination models
- ✅ Subcontract composition pattern
- ✅ Pydantic validation and type safety

**UPDATED (v0.3.2)**: Runtime execution is now **IMPLEMENTED** via mixin-based approach:
- ✅ FSM runtime via `MixinFSMExecution` + `utils/fsm_executor.py`
- ✅ Workflow runtime via `MixinWorkflowExecution` + `utils/workflow_executor.py`
- ✅ Pure function approach for execution logic
- ✅ Intent-based pattern for side effects

**Remaining Gaps**:
- ⚠️ Nodes can use mixins but still often write imperative Python code
- ⚠️ Limited examples demonstrating declarative patterns
- ⚠️ Documentation needs updates to emphasize mixin-based approach

**Impact**: Developers now have **mixin-based declarative execution available**, but adoption needs:
- More comprehensive examples showing mixin usage
- Documentation updates emphasizing declarative YAML-first approach
- Integration tests validating declarative patterns

**Recommendation**: Prioritize creating declarative examples, updating documentation to show mixin-based patterns, and migrating existing nodes to use `MixinFSMExecution` and `MixinWorkflowExecution`.

---

**Last Updated**: 2025-11-16
**Version**: v0.3.2
**Next Review**: After Sprint 2 completion (declarative base classes)
**Related Documents**:
- [ONEX Four-Node Architecture](ONEX_FOUR_NODE_ARCHITECTURE.md)
- [Contract System](CONTRACT_SYSTEM.md)
- [Node Building Guide](../guides/node-building/README.md)
- Mixin implementations:
  - `src/omnibase_core/mixins/mixin_fsm_execution.py`
  - `src/omnibase_core/mixins/mixin_workflow_execution.py`
  - `src/omnibase_core/utils/fsm_executor.py`
  - `src/omnibase_core/utils/workflow_executor.py`
