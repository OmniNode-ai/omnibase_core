# Declarative Workflow Architecture - Findings and Recommendations

> **Date**: 2025-11-16
> **Correlation ID**: `doc-review-declarative-workflows-2025-11-16`
> **Status**: ARCHITECTURE REVIEW

---

## Executive Summary

This document summarizes findings from a comprehensive review of omnibase_core's declarative workflow and FSM capabilities. The review confirms that **YAML contract infrastructure for declarative workflows and FSMs exists and is complete**, but **current node implementations don't fully leverage these declarative patterns yet**.

### Key Finding: Infrastructure vs. Implementation Gap

✅ **Infrastructure EXISTS**: Complete Pydantic models for FSM and workflow subcontracts
⚠️ **Implementation GAP**: NodeOrchestrator and NodeReducer still use imperative Python code
📝 **Documentation NEEDS**: Emphasize declarative patterns over custom code

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

### ⚠️ Missing: FSM/Workflow Execution Mixins

**Not Found**:
- `MixinFSM` - FSM execution from subcontract
- `MixinWorkflowExecution` - Workflow execution from subcontract
- `MixinStateTransition` - State machine transition handling

**Current**: `MixinDagSupport` focuses on workflow EVENT participation, not declarative workflow EXECUTION.

---

## Gap Analysis

### Infrastructure vs. Implementation

| Component | Infrastructure | Implementation | Gap |
|-----------|---------------|----------------|-----|
| **FSM Subcontracts** | ✅ Complete | ❌ Not used | HIGH |
| **Workflow Subcontracts** | ✅ Complete | ❌ Not used | HIGH |
| **Pydantic Validation** | ✅ Complete | ✅ Working | NONE |
| **Contract Composition** | ✅ Complete | ⚠️ Partial | MEDIUM |
| **FSM Runtime** | ❌ Missing | ❌ Missing | **CRITICAL** |
| **Workflow Runtime** | ❌ Missing | ❌ Missing | **CRITICAL** |
| **Declarative Examples** | ❌ Missing | ❌ Missing | HIGH |
| **Documentation** | ⚠️ Partial | ❌ Wrong Focus | HIGH |

### Critical Missing Components

#### 1. FSM Runtime Interpreter

**Need**: Service that executes FSM from YAML subcontract definition

```python
# MISSING - Should exist
class ServiceFSMExecutor:
    """Execute FSM transitions from ModelFSMSubcontract."""

    async def execute_transition(
        self,
        fsm: ModelFSMSubcontract,
        current_state: str,
        trigger: str,
        context: dict[str, Any]
    ) -> FSMTransitionResult:
        """Execute FSM transition declaratively."""
```

#### 2. Workflow Runtime Interpreter

**Need**: Service that executes workflows from YAML definition

```python
# MISSING - Should exist
class ServiceWorkflowExecutor:
    """Execute workflows from ModelWorkflowDefinition."""

    async def execute_workflow(
        self,
        workflow: ModelWorkflowDefinition,
        initial_context: dict[str, Any]
    ) -> WorkflowExecutionResult:
        """Execute workflow declaratively."""
```

#### 3. Declarative Node Base Classes

**Need**: Base classes that consume YAML contracts

```python
# MISSING - Should exist
class NodeOrchestratorDeclarative(NodeCoreBase):
    """Orchestrator driven entirely by YAML workflow contracts."""

    def __init__(self, container: ModelONEXContainer, contract: ModelContractOrchestrator):
        super().__init__(container)
        self.workflow_executor = container.get_service("ServiceWorkflowExecutor")
        self.contract = contract

    async def process(self, input_data: ModelOrchestratorInput) -> ModelOrchestratorOutput:
        """Execute workflow from contract - NO custom code required."""
        return await self.workflow_executor.execute_workflow(
            self.contract.workflow_coordination,
            input_data
        )
```

---

## Recommendations

### 1. Create Runtime Execution Services

**Priority**: CRITICAL
**Timeline**: Sprint 1

**Tasks**:
- [ ] Implement `ServiceFSMExecutor` for FSM runtime
- [ ] Implement `ServiceWorkflowExecutor` for workflow runtime
- [ ] Add DI registration in container
- [ ] Create unit tests for runtime services

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

### 5. Create Workflow/FSM Mixins

**Priority**: MEDIUM
**Timeline**: Sprint 3

**Tasks**:
- [ ] Create `MixinFSMExecution` for FSM-driven nodes
- [ ] Create `MixinWorkflowExecution` for workflow-driven nodes
- [ ] Update mixin_metadata.yaml with new mixins
- [ ] Add mixin examples

---

## Implementation Roadmap

### Sprint 1: Runtime Services (Week 1-2)

**Goal**: Create the missing runtime interpreters

1. **ServiceFSMExecutor Implementation**
   ```python
   # src/omnibase_core/services/service_fsm_executor.py
   class ServiceFSMExecutor:
       async def execute_transition(self, fsm: ModelFSMSubcontract, ...):
           # Validate current state
           # Check transition conditions
           # Execute entry/exit actions
           # Update state
           # Handle rollback on failure
   ```

2. **ServiceWorkflowExecutor Implementation**
   ```python
   # src/omnibase_core/services/service_workflow_executor.py
   class ServiceWorkflowExecutor:
       async def execute_workflow(self, workflow: ModelWorkflowDefinition, ...):
           # Build execution graph
           # Execute steps based on mode (sequential, parallel, mixed)
           # Handle dependencies
           # Coordinate with FSM executor for stateful steps
   ```

3. **Container Registration**
   ```python
   # Register services
   container.register_service("ServiceFSMExecutor", ServiceFSMExecutor())
   container.register_service("ServiceWorkflowExecutor", ServiceWorkflowExecutor())
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

### Sprint 3: Mixins & Advanced Features (Week 5-6)

**Goal**: Complete the declarative ecosystem

1. **Execution Mixins**
   - `MixinFSMExecution`
   - `MixinWorkflowExecution`

2. **Advanced Examples**
   - Complex multi-branch workflows
   - FSM with conditional transitions
   - Parallel workflow execution

3. **Testing & Validation**
   - Integration tests for declarative patterns
   - Performance benchmarks
   - Migration guide for existing code

---

## Conclusion

The omnibase_core codebase has **excellent infrastructure** for declarative workflows and FSMs through:
- ✅ Complete FSM subcontract models
- ✅ Complete workflow coordination models
- ✅ Subcontract composition pattern
- ✅ Pydantic validation and type safety

However, there is a **critical gap** in runtime execution:
- ❌ No FSM runtime interpreter
- ❌ No workflow runtime interpreter
- ❌ Nodes still use imperative Python code
- ❌ Documentation emphasizes custom code over YAML

**Impact**: Developers are currently writing custom Python code for orchestrator and reducer logic instead of using declarative YAML contracts.

**Recommendation**: Prioritize creating runtime execution services (`ServiceFSMExecutor`, `ServiceWorkflowExecutor`) and updating documentation to emphasize the declarative YAML-first approach.

---

**Last Updated**: 2025-11-16
**Next Review**: After Sprint 1 completion
**Related Documents**:
- [ONEX Four-Node Architecture](ONEX_FOUR_NODE_ARCHITECTURE.md)
- [Contract System](CONTRACT_SYSTEM.md)
- [Node Building Guide](../guides/node-building/README.md)
