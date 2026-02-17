> **Navigation**: [Home](../INDEX.md) > Reference > API Documentation

# ONEX Core Public API Reference

## Overview

This document describes the public API surface of `omnibase_core`, the foundational library for the ONEX Four-Node Architecture. All APIs use Python 3.12+ syntax with PEP 604 type unions (`X | None` instead of `Optional[X]`).

This is not a backwards-compatible library. Interfaces change without deprecation periods. Breaking changes are always acceptable per the [repo invariants](../architecture/overview.md).

---

## Table of Contents

- [Nodes](#nodes)
- [Input/Output Models](#inputoutput-models)
- [Handler Output Model](#handler-output-model)
- [Contracts](#contracts)
- [Container](#container)
- [Protocols](#protocols)
- [Enums](#enums)
- [Error Handling](#error-handling)

---

## Nodes

**Import**: `from omnibase_core.nodes import NodeCompute, NodeEffect, NodeReducer, NodeOrchestrator`

The `omnibase_core.nodes` module is the primary public API. It exports the four node types, their input/output models, and associated enums. The `__all__` list in `omnibase_core.nodes.__init__` defines the frozen public surface.

All nodes inherit from `NodeCoreBase` (abstract) and accept a single constructor argument: `ModelONEXContainer`.

### NodeCompute

```python
class NodeCompute[T_Input, T_Output](NodeCoreBase, MixinHandlerRouting):
    """Pure computation node for deterministic operations."""

    def __init__(self, container: ModelONEXContainer) -> None: ...

    async def process(
        self, input_data: ModelComputeInput[T_Input]
    ) -> ModelComputeOutput[T_Output]: ...

    async def execute_compute(
        self, contract: ModelContractCompute
    ) -> ModelComputeOutput[T_Output]: ...

    def register_computation(
        self, computation_type: str, computation_func: Callable[..., Any]
    ) -> None: ...

    async def get_computation_metrics(self) -> dict[str, dict[str, float]]: ...
```

**File**: `src/omnibase_core/nodes/node_compute.py`

**Output constraints**: MUST return `result`. CANNOT emit `events[]`, `intents[]`, or `projections[]`.

**Generic type parameters**:
- `T_Input`: Type of input data flowing through `ModelComputeInput[T_Input]`
- `T_Output`: Type of output result flowing through `ModelComputeOutput[T_Output]`

**Infrastructure injection** (optional via protocols):
- `ProtocolComputeCache` -- caching computation results
- `ProtocolTimingService` -- timing computation duration
- `ProtocolParallelExecutor` -- parallel execution

When no infrastructure protocols are injected, the node operates in **pure mode**: cache_hit is always `False`, processing_time_ms is `0.0`, execution is sequential.

**Handler routing**: Supports contract-driven handler dispatch via `MixinHandlerRouting`. Configure `handler_routing` in the YAML contract to route by `payload_type_match`.

---

### NodeEffect

```python
class NodeEffect(NodeCoreBase, MixinEffectExecution, MixinHandlerRouting):
    """Contract-driven effect node for external I/O operations."""

    effect_subcontract: ModelEffectSubcontract | None

    def __init__(self, container: ModelONEXContainer) -> None: ...

    async def process(self, input_data: ModelEffectInput) -> ModelEffectOutput: ...

    def get_circuit_breaker(self, operation_id: UUID) -> ModelCircuitBreaker: ...

    def reset_circuit_breakers(self) -> None: ...
```

**File**: `src/omnibase_core/nodes/node_effect.py`

**Output constraints**: Can emit `events[]`. CANNOT emit `intents[]`, `projections[]`, or `result`.

**Contract injection**: Set `effect_subcontract` after construction or via contract auto-loading. All effect operations, retry policies, circuit breakers, and transaction boundaries are defined declaratively in the subcontract YAML.

**Pattern**:
```python
class NodeMyEffect(NodeEffect):
    pass  # Zero custom code -- driven by YAML contract

node = NodeMyEffect(container)
node.effect_subcontract = ModelEffectSubcontract(...)
result = await node.process(ModelEffectInput(
    effect_type=EnumEffectType.API_CALL,
    operation_data={"name": "John Doe"},
))
```

---

### NodeReducer

```python
class NodeReducer[T_Input, T_Output](NodeCoreBase, MixinFSMExecution):
    """FSM-driven reducer node for state management."""

    fsm_contract: ModelFSMSubcontract | None

    def __init__(self, container: ModelONEXContainer) -> None: ...

    async def process(
        self, input_data: ModelReducerInput[T_Input]
    ) -> ModelReducerOutput[T_Output]: ...

    async def validate_contract(self) -> list[str]: ...

    def get_current_state(self) -> str | None: ...

    def get_state_history(self) -> list[str]: ...

    def is_complete(self) -> bool: ...

    def snapshot_state(*, deep_copy: bool = False) -> ModelFSMStateSnapshot | None: ...

    def restore_state(
        self,
        snapshot: ModelFSMStateSnapshot,
        *,
        validate: bool = True,
        allow_terminal_state: bool = False,
    ) -> None: ...

    def get_state_snapshot(*, deep_copy: bool = False) -> dict[str, object] | None: ...
```

**File**: `src/omnibase_core/nodes/node_reducer.py`

**Output constraints**: Can emit `projections[]`. CANNOT emit `events[]`, `intents[]`, or `result`.

**Generic type parameters**:
- `T_Input`: Type of input data items (from `ModelReducerInput[T_Input]`)
- `T_Output`: Type of output result (to `ModelReducerOutput[T_Output]`)

**FSM contract**: Loaded automatically from the node's contract `state_machine` field. If no FSM contract is present, FSM capabilities are inactive.

**State serialization**: Two methods for different use cases:
- `snapshot_state()` returns `ModelFSMStateSnapshot` (typed, restorable)
- `get_state_snapshot()` returns `dict[str, object]` (JSON-serializable)

---

### NodeOrchestrator

```python
class NodeOrchestrator(NodeCoreBase, MixinWorkflowExecution, MixinHandlerRouting):
    """Workflow-driven orchestrator node for coordination."""

    workflow_definition: ModelWorkflowDefinition | None

    def __init__(self, container: ModelONEXContainer) -> None: ...

    async def process(
        self, input_data: ModelOrchestratorInput
    ) -> ModelOrchestratorOutput: ...

    async def validate_contract(self) -> list[str]: ...

    async def validate_workflow_steps(
        self, steps: list[ModelWorkflowStep]
    ) -> list[str]: ...

    def get_execution_order_for_steps(
        self, steps: list[ModelWorkflowStep]
    ) -> list[UUID]: ...

    def snapshot_workflow_state(
        *, deep_copy: bool = False
    ) -> ModelWorkflowStateSnapshot | None: ...

    def restore_workflow_state(
        self, snapshot: ModelWorkflowStateSnapshot
    ) -> None: ...

    def get_workflow_snapshot(
        *, deep_copy: bool = False
    ) -> dict[str, object] | None: ...
```

**File**: `src/omnibase_core/nodes/node_orchestrator.py`

**Output constraints**: Can emit `events[]` and `intents[]`. CANNOT emit `projections[]` or `result`.

**Side-effect prohibition**: NodeOrchestrator MUST NOT write to external systems directly. It emits `ModelAction` objects for deferred execution by target EFFECT nodes.

**Workflow definition injection**: `workflow_definition` MUST be injected by the container or dispatcher layer before calling `process()`. The orchestrator does not load contracts itself.

**State serialization**: Two methods for different use cases:
- `snapshot_workflow_state()` returns `ModelWorkflowStateSnapshot` (typed, restorable)
- `get_workflow_snapshot()` returns `dict[str, object]` (JSON-serializable)

---

## Input/Output Models

**Import**: `from omnibase_core.nodes import ModelComputeInput, ModelComputeOutput, ...`

All input/output models are exported from `omnibase_core.nodes`.

| Model | Used By | Description |
|-------|---------|-------------|
| `ModelComputeInput[T]` | `NodeCompute.process()` | Computation input with data, type, cache/parallel flags |
| `ModelComputeOutput[T]` | `NodeCompute.process()` | Computation result with timing and cache metrics |
| `ModelEffectInput` | `NodeEffect.process()` | Effect input with type, operation_data, retry config |
| `ModelEffectOutput` | `NodeEffect.process()` | Effect result with transaction state and timing |
| `ModelEffectTransaction` | `NodeEffect` | Transaction model for rollback support |
| `ModelReducerInput[T]` | `NodeReducer.process()` | Reducer input with data, reduction type, metadata |
| `ModelReducerOutput[T]` | `NodeReducer.process()` | Reducer result with FSM state and intents |
| `ModelOrchestratorInput` | `NodeOrchestrator.process()` | Orchestrator input with workflow steps and execution mode |
| `ModelOrchestratorOutput` | `NodeOrchestrator.process()` | Orchestrator result with completed/failed steps and actions |

### Source Locations

| Model | File |
|-------|------|
| `ModelComputeInput` | `src/omnibase_core/models/compute/model_compute_input.py` |
| `ModelComputeOutput` | `src/omnibase_core/models/compute/model_compute_output.py` |
| `ModelEffectInput` | `src/omnibase_core/models/effect/model_effect_input.py` |
| `ModelEffectOutput` | `src/omnibase_core/models/effect/model_effect_output.py` |
| `ModelEffectTransaction` | `src/omnibase_core/models/infrastructure/model_effect_transaction.py` |
| `ModelReducerInput` | `src/omnibase_core/models/reducer/model_reducer_input.py` |
| `ModelReducerOutput` | `src/omnibase_core/models/reducer/model_reducer_output.py` |
| `ModelOrchestratorInput` | `src/omnibase_core/models/orchestrator/model_orchestrator_input.py` |
| `ModelOrchestratorOutput` | `src/omnibase_core/models/orchestrator/__init__.py` |

---

## Handler Output Model

**Import**: `from omnibase_core.models.dispatch import ModelHandlerOutput`

**File**: `src/omnibase_core/models/dispatch/model_handler_output.py`

`ModelHandlerOutput[T]` is the canonical return type for all message handlers in the ONEX dispatch engine. It enforces node-kind-specific output constraints at the Pydantic model level.

```python
class ModelHandlerOutput[T](BaseModel):
    """Unified handler output model with semantic node-kind constraints."""

    model_config = ConfigDict(frozen=True)  # Immutable after creation

    # Factory methods enforce output constraints:
    @classmethod
    def for_orchestrator(
        cls,
        input_envelope_id: UUID,
        correlation_id: UUID,
        handler_id: str,
        events: tuple[...] = (),
        intents: tuple[...] = (),
    ) -> ModelHandlerOutput[T]: ...

    @classmethod
    def for_reducer(
        cls,
        input_envelope_id: UUID,
        correlation_id: UUID,
        handler_id: str,
        projections: tuple[...] = (),
    ) -> ModelHandlerOutput[T]: ...

    @classmethod
    def for_effect(
        cls,
        input_envelope_id: UUID,
        correlation_id: UUID,
        handler_id: str,
        events: tuple[...] = (),
    ) -> ModelHandlerOutput[T]: ...

    @classmethod
    def for_compute(
        cls,
        input_envelope_id: UUID,
        correlation_id: UUID,
        handler_id: str,
        result: T,  # Required for COMPUTE
    ) -> ModelHandlerOutput[T]: ...
```

**Output constraint enforcement** (enforced at construction via Pydantic validators):

| Node Kind | Allowed | Forbidden |
|-----------|---------|-----------|
| ORCHESTRATOR | `events[]`, `intents[]` | `projections[]`, `result` |
| REDUCER | `projections[]` | `events[]`, `intents[]`, `result` |
| EFFECT | `events[]` | `intents[]`, `projections[]`, `result` |
| COMPUTE | `result` (required) | `events[]`, `intents[]`, `projections[]` |

**Causality tracking**: Every `ModelHandlerOutput` includes `input_envelope_id` and `correlation_id` for full causality tracing.

---

## Contracts

### ModelContractBase

**Import**: `from omnibase_core.models.contracts.model_contract_base import ModelContractBase`

**File**: `src/omnibase_core/models/contracts/model_contract_base.py`

Abstract base for all ONEX contract models. Uses `BaseModel` + `ABC`.

```python
class ModelContractBase(BaseModel, ABC):
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    name: str
    contract_version: ModelSemVer
    node_version: ModelSemVer | None = None
    description: str = ""
    node_type: EnumNodeType
    labels: list[str] = Field(default_factory=list)
    dependencies: list[ModelDependency] = Field(default_factory=list)
    execution_profile: ModelExecutionProfile | None = None
    performance_requirements: ModelPerformanceRequirements | None = None
    lifecycle_config: ModelLifecycleConfig | None = None
    validation_rules: ModelValidationRules | None = None
    protocol_dependencies: list[ModelProtocolDependency] = Field(default_factory=list)

    # Infrastructure extensions (OMN-1588)
    handler_routing: ModelHandlerRoutingSubcontract | None = None
    yaml_consumed_events: list[str | ModelConsumedEventEntry] = Field(default_factory=list)
    yaml_published_events: list[str | ModelPublishedEventEntry] = Field(default_factory=list)
```

### Node-Specific Contract Models

| Contract Model | File | Node Type |
|----------------|------|-----------|
| `ModelContractCompute` | `src/omnibase_core/models/contracts/model_contract_compute.py` | COMPUTE |
| `ModelContractEffect` | `src/omnibase_core/models/contracts/model_contract_effect.py` | EFFECT |
| `ModelContractReducer` | `src/omnibase_core/models/contracts/model_contract_reducer.py` | REDUCER |
| `ModelContractOrchestrator` | `src/omnibase_core/models/contracts/model_contract_orchestrator.py` | ORCHESTRATOR |

Each extends `ModelContractBase` with node-type-specific subcontracts:

- `ModelContractCompute` adds `algorithm: ModelAlgorithmConfig`, `input_state`, and algorithm configuration
- `ModelContractEffect` adds `effect_operations: ModelEffectSubcontract`
- `ModelContractReducer` adds `state_transitions: ModelFSMSubcontract`, `aggregation`, `state_management`, `caching`, `event_type`
- `ModelContractOrchestrator` adds `workflow_coordination: ModelWorkflowCoordinationSubcontract`, `consumed_events`, `published_events`

### Key Subcontract Models

| Subcontract | File | Purpose |
|-------------|------|---------|
| `ModelFSMSubcontract` | `src/omnibase_core/models/contracts/subcontracts/model_fsm_subcontract.py` | FSM state machine definition |
| `ModelWorkflowDefinition` | `src/omnibase_core/models/contracts/subcontracts/model_workflow_definition.py` | Workflow execution graph |
| `ModelEffectSubcontract` | `src/omnibase_core/models/contracts/subcontracts/model_effect_subcontract.py` | Effect operations and retry policies |
| `ModelHandlerRoutingSubcontract` | `src/omnibase_core/models/contracts/subcontracts/model_handler_routing_subcontract.py` | Handler dispatch configuration |
| `ModelAggregationSubcontract` | `src/omnibase_core/models/contracts/subcontracts/model_aggregation_subcontract.py` | Data aggregation operations |
| `ModelEventTypeSubcontract` | `src/omnibase_core/models/contracts/subcontracts/model_event_type_subcontract.py` | Event type definitions |
| `ModelStateManagementSubcontract` | `src/omnibase_core/models/contracts/subcontracts/model_state_management_subcontract.py` | State persistence configuration |
| `ModelCachingSubcontract` | `src/omnibase_core/models/contracts/subcontracts/model_caching_subcontract.py` | Caching behavior |
| `ModelProtocolDependency` | `src/omnibase_core/models/contracts/subcontracts/model_protocol_dependency.py` | Protocol-based DI declarations |

---

## Container

### ModelONEXContainer

**Import**: `from omnibase_core.models.container.model_onex_container import ModelONEXContainer`

**File**: `src/omnibase_core/models/container/model_onex_container.py`

The primary dependency injection container for the ONEX framework. All nodes accept `ModelONEXContainer` as their sole constructor argument.

```python
container = await create_model_onex_container()
service = await container.get_service_async(ProtocolLoggerLike)
```

Key capabilities:
- Protocol-based service resolution with caching
- Observable dependency injection with event emission
- Workflow orchestration via `ModelWorkflowCoordinator`
- Context-based container management for async/thread isolation

**Service resolution methods**:

| Method | Description |
|--------|-------------|
| `get_service(protocol_type)` | Resolve service by protocol type (synchronous) |
| `get_service_async(protocol_type)` | Resolve service by protocol type (async) |
| `get_service_optional(protocol_type)` | Resolve or return `None` if not registered |

**Critical**: Use `ModelONEXContainer` in node constructors, never `ModelContainer`. See [Container Types](../architecture/CONTAINER_TYPES.md).

### ServiceRegistry

**Import**: `from omnibase_core.container.container_service_registry import ServiceRegistry`

**File**: `src/omnibase_core/container/container_service_registry.py`

Implementation of `ProtocolServiceRegistry` for omnibase_core. Provides service registration, resolution, lifecycle management, and health monitoring.

```python
registry = ServiceRegistry(config)
reg_id = await registry.register_instance(
    interface=ProtocolLoggerLike,
    instance=logger,
    scope=EnumInjectionScope.GLOBAL,
)
```

---

## Protocols

**Import**: `from omnibase_core.protocols import ProtocolServiceRegistry, ProtocolEventBus, ...`

**File**: `src/omnibase_core/protocols/__init__.py`

All protocols use `typing.Protocol` with `@runtime_checkable` for duck typing support. The protocols package is organized into submodules by domain.

### Protocol Categories

**Container and DI**:

| Protocol | Purpose |
|----------|---------|
| `ProtocolServiceRegistry` | Service registration and resolution |
| `ProtocolServiceFactory` | Service instance creation |
| `ProtocolServiceValidator` | Service health validation |
| `ProtocolInjectionContext` | Scoped injection context |
| `ProtocolDependencyGraph` | Service dependency tracking |

**Event Bus**:

| Protocol | Purpose |
|----------|---------|
| `ProtocolEventBus` | Core event publishing/subscribing |
| `ProtocolAsyncEventBus` | Async event bus variant |
| `ProtocolSyncEventBus` | Sync event bus variant |
| `ProtocolEventEnvelope` | Event envelope structure |
| `ProtocolEventBusRegistry` | Event bus discovery |

**Compute Infrastructure**:

| Protocol | Purpose |
|----------|---------|
| `ProtocolComputeCache` | Computation result caching |
| `ProtocolTimingService` | Execution timing |
| `ProtocolParallelExecutor` | Parallel execution support |
| `ProtocolCircuitBreaker` | Circuit breaker pattern |
| `ProtocolToolCache` | Tool result caching |

**Handler System**:

| Protocol | Purpose |
|----------|---------|
| `ProtocolHandler` | Runtime handler interface |
| `ProtocolHandlerRegistry` | Handler lookup and registration |
| `ProtocolMessageHandler` | Message processing handler |
| `ProtocolHandlerContract` | Handler behavior contract |
| `ProtocolHandlerTypeResolver` | Handler type resolution |

**Node Architecture**:

| Protocol | Purpose |
|----------|---------|
| `ProtocolCompute` | COMPUTE node interface |
| `ProtocolEffect` | EFFECT node interface |
| `ProtocolOrchestrator` | ORCHESTRATOR node interface |
| `ProtocolAction` | Action emission interface |
| `ProtocolNodeResult` | Node execution result |

**Validation**:

| Protocol | Purpose |
|----------|---------|
| `ProtocolValidator` | General validation |
| `ProtocolValidationResult` | Validation outcome |
| `ProtocolComplianceValidator` | Architecture compliance checking |
| `ProtocolQualityValidator` | Code quality validation |

**Other**:

| Protocol | Purpose |
|----------|---------|
| `ProtocolCanonicalSerializer` | Deterministic serialization for hashing |
| `ProtocolMergeEngine` | Contract merge operations |
| `ProtocolSecretService` | Secret management |
| `ProtocolDiffStore` | Diff storage |
| `ProtocolMetricsBackend` | Metrics collection |
| `ProtocolCacheBackend` | Generic cache backend |
| `ProtocolKeyProvider` | Cryptographic key provision |

---

## Enums

**Import**: `from omnibase_core.enums import EnumNodeType, EnumCoreErrorCode, ...`

**File**: `src/omnibase_core/enums/`

The enums package contains 100+ enum definitions. Key enums for the public API:

### Node Architecture Enums

| Enum | File | Values |
|------|------|--------|
| `EnumNodeType` | `enum_architecture.py` | `COMPUTE`, `EFFECT`, `REDUCER`, `ORCHESTRATOR` |
| `EnumExecutionMode` | `enum_orchestrator_types.py` | `SEQUENTIAL`, `PARALLEL`, `BATCH` |
| `EnumActionType` | `enum_orchestrator_types.py` | Action type classifications |
| `EnumBranchCondition` | `enum_orchestrator_types.py` | Workflow branching conditions |
| `EnumReductionType` | `enum_reducer_types.py` | `AGGREGATE`, `BATCH`, `INCREMENTAL`, `WINDOWED` |
| `EnumConflictResolution` | `enum_reducer_types.py` | Conflict resolution strategies |
| `EnumStreamingMode` | `enum_reducer_types.py` | Streaming mode for reducer |
| `EnumWorkflowStatus` | `enum_workflow_status.py` | Workflow execution status |

### Error and Status Enums

| Enum | File | Purpose |
|------|------|---------|
| `EnumCoreErrorCode` | `enum_core_error_code.py` | Core error codes (VALIDATION_ERROR, OPERATION_FAILED, etc.) |
| `EnumOnexErrorCode` | `enum_onex_error_code.py` | Base error code interface |
| `EnumOnexStatus` | `enum_onex_status.py` | Operation status (SUCCESS, ERROR, etc.) |
| `EnumHealthStatus` | `enum_health_status.py` | Service health states |
| `EnumNodeLifecycleStatus` | `enum_node_lifecycle_status.py` | Node lifecycle stages |

### DI and Service Enums

| Enum | File | Purpose |
|------|------|---------|
| `EnumInjectionScope` | `enum_injection_scope.py` | `GLOBAL`, `TRANSIENT`, `SCOPED` |
| `EnumServiceLifecycle` | `enum_service_lifecycle.py` | Service lifecycle states |
| `EnumDependencyType` | `enum_dependency_type.py` | `REQUIRED`, `OPTIONAL`, `PREFERRED` |

### Execution Enums (exported from `omnibase_core.nodes`)

These enums are re-exported from `omnibase_core.nodes` for convenience:

```python
from omnibase_core.nodes import (
    EnumActionType,
    EnumBranchCondition,
    EnumConflictResolution,
    EnumExecutionMode,
    EnumReductionType,
    EnumStreamingMode,
    EnumWorkflowStatus,
)
```

---

## Error Handling

### ModelOnexError

**Import**: `from omnibase_core.models.errors.model_onex_error import ModelOnexError`

**File**: `src/omnibase_core/models/errors/model_onex_error.py`

Base exception for all ONEX errors. Combines standard Python exception behavior with structured error context.

```python
class ModelOnexError(Exception):
    def __init__(
        self,
        message: str,
        error_code: EnumOnexErrorCode | str | None = None,
        status: EnumOnexStatus = EnumOnexStatus.ERROR,
        correlation_id: UUID | None = None,
        timestamp: datetime | None = None,
        **context: Any,
    ) -> None: ...
```

**Usage pattern**:

```python
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

raise ModelOnexError(
    message="Invalid computation type",
    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
    context={
        "node_id": str(self.node_id),
        "computation_type": computation_type,
    },
)
```

### Error Handling Rules

| Use Case | Exception Type |
|----------|---------------|
| Standard Python validation at function boundaries | `ValueError` |
| Pydantic model validators | `ValueError` |
| ONEX-specific errors needing error codes | `ModelOnexError` |
| Errors that will be serialized/logged | `ModelOnexError` |
| Errors in node/workflow execution | `ModelOnexError` |

**Decorator contract**: Cancellation signals (`SystemExit`, `KeyboardInterrupt`, `asyncio.CancelledError`) always propagate. `ModelOnexError` is re-raised as-is. Other exceptions are wrapped in `ModelOnexError`.

See [Error Handling Best Practices](../conventions/ERROR_HANDLING_BEST_PRACTICES.md) for complete guidelines.

---

## Pydantic Model Standards

All models in `omnibase_core` follow these conventions:

| Model Type | Required ConfigDict |
|------------|---------------------|
| Immutable value | `ConfigDict(frozen=True, extra="forbid", from_attributes=True)` |
| Mutable internal | `ConfigDict(extra="forbid", from_attributes=True)` |
| Contract/external | `ConfigDict(extra="ignore", ...)` |

**Type annotations**: Use `X | None` (PEP 604), never `Optional[X]`. Use `list[str]`, never `List[str]`.

**Mutable defaults**: Always use `default_factory`:
```python
items: list[str] = Field(default_factory=list)
```

---

## Thread Safety

No node type is thread-safe by default. Each thread should create its own node instance. Immutable snapshots (`ModelFSMStateSnapshot`, `ModelWorkflowStateSnapshot`, `ModelHandlerOutput`) are safe to share across threads for reading.

For multi-threaded patterns, see [Threading Guide](../guides/THREADING.md).

---

**Related Documents**:
- [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)
- [Contract System](../architecture/CONTRACT_SYSTEM.md)
- [Handler Contract Guide](../contracts/HANDLER_CONTRACT_GUIDE.md)
- [Container Types](../architecture/CONTAINER_TYPES.md)
- [Dependency Injection](../architecture/DEPENDENCY_INJECTION.md)
- [Error Handling Best Practices](../conventions/ERROR_HANDLING_BEST_PRACTICES.md)
- [Pydantic Best Practices](../conventions/PYDANTIC_BEST_PRACTICES.md)
- [Threading Guide](../guides/THREADING.md)
