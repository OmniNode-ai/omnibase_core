> **Navigation**: [Home](../../INDEX.md) > [Reference](../README.md) > API > Nodes

# Nodes API Reference - omnibase_core

**Status**: ✅ Complete

## Overview

This document provides comprehensive API reference for all node classes in omnibase_core. The ONEX framework provides four core node types: COMPUTE, EFFECT, REDUCER, and ORCHESTRATOR.

## Core Node Classes

**Architectural invariant**: Nodes are thin coordination shells. Business logic belongs in handlers. Each node example below shows the correct pattern: a thin node that delegates to a handler.

### NodeCompute

**Location**: `omnibase_core.nodes.node_compute`

**Purpose**: Pure computation nodes. Business logic lives in handlers.

**Output constraints**: `result` (required). Forbidden: `events[]`, `intents[]`, `projections[]`.

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.nodes import NodeCompute

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class MyComputeNode(NodeCompute):
    """Thin shell -- computation logic lives in handler."""

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
```

#### Key Methods

- `__init__(container: ModelONEXContainer)` - Initialize with dependency injection container
- `async process(input_data)` - Delegates to handler for computation
- `async get_computation_metrics() -> dict[str, dict[str, float]]` - Get detailed computation performance metrics
- `register_computation(computation_type: str, computation_func: Callable) -> None` - Register custom computation function

#### Properties

- `container: ModelONEXContainer` - Dependency injection container
- `computation_cache: ProtocolComputeCache` - Computation cache (lazily created via protocol injection)

### NodeEffect

**Location**: `omnibase_core.nodes.node_effect`

**Purpose**: Side effect nodes for external interactions. Business logic lives in handlers.

**Output constraints**: `events[]`. Forbidden: `intents[]`, `projections[]`, `result`.

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.nodes import NodeEffect

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class DatabaseEffectNode(NodeEffect):
    """Thin shell -- I/O logic lives in handler."""

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
```

#### Key Methods

- `__init__(container: ModelONEXContainer)` - Initialize with dependency injection container
- `async process(input_data)` - Delegates to handler for I/O operations
- `get_circuit_breaker(operation_id: UUID) -> ModelCircuitBreaker` - Get or create circuit breaker for an operation
- `reset_circuit_breakers() -> None` - Reset all circuit breakers to closed state

#### Properties

- `container: ModelONEXContainer` - Dependency injection container
- `_circuit_breakers: dict[UUID, ModelCircuitBreaker]` - Circuit breaker instances keyed by operation ID
- `effect_subcontract: ModelEffectSubcontract | None` - Effect subcontract for contract-driven execution

### NodeReducer

**Location**: `omnibase_core.nodes.node_reducer`

**Purpose**: FSM-driven state management. Business logic lives in handlers.

**Output constraints**: `projections[]`. Forbidden: `events[]`, `intents[]`, `result`.

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.nodes import NodeReducer

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class MetricsReducerNode(NodeReducer):
    """Thin shell -- reduction logic lives in handler."""

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
```

#### Key Methods

- `__init__(container: ModelONEXContainer)` - Initialize with dependency injection container
- `async process(input_data: ModelReducerInput[T_Input]) -> ModelReducerOutput[T_Output]` - Process input using FSM-driven state transitions
- `get_current_state() -> str | None` - Get current FSM state name, or `None` if FSM not initialized
- `get_state_history() -> list[str]` - Get FSM state transition history in chronological order
- `is_complete() -> bool` - Check if FSM has reached a terminal state
- `async validate_contract() -> list[str]` - Validate FSM contract for correctness (empty list if valid)
- `snapshot_state(*, deep_copy: bool = False) -> ModelFSMStateSnapshot | None` - Return current FSM state as a strongly-typed snapshot model
- `restore_state(snapshot: ModelFSMStateSnapshot, *, validate: bool = True, allow_terminal_state: bool = False) -> None` - Restore FSM state from a snapshot
- `get_state_snapshot(*, deep_copy: bool = False) -> dict[str, object] | None` - Return FSM state as a JSON-serializable dictionary

#### Properties

- `container: ModelONEXContainer` - Dependency injection container
- `fsm_contract: ModelFSMSubcontract | None` - Loaded FSM subcontract reference

### NodeOrchestrator

**Location**: `omnibase_core.nodes.node_orchestrator`

**Purpose**: Workflow coordination. Business logic lives in handlers. Cannot return results.

**Output constraints**: `events[]`, `intents[]`. Forbidden: `projections[]`, `result`.

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.nodes import NodeOrchestrator

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class WorkflowOrchestratorNode(NodeOrchestrator):
    """Thin shell -- coordination logic lives in handler."""

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
```

#### Key Methods

- `__init__(container: ModelONEXContainer)` - Initialize with dependency injection container
- `async process(input_data: ModelOrchestratorInput) -> ModelOrchestratorOutput` - Process workflow using workflow-driven coordination
- `async validate_contract() -> list[str]` - Validate workflow contract for correctness (empty list if valid)
- `async validate_workflow_steps(steps: list[ModelWorkflowStep]) -> list[str]` - Validate workflow steps against contract
- `get_execution_order_for_steps(steps: list[ModelWorkflowStep]) -> list[UUID]` - Get topological execution order for workflow steps
- `snapshot_workflow_state(*, deep_copy: bool = False) -> ModelWorkflowStateSnapshot | None` - Return current workflow state as a strongly-typed snapshot model
- `restore_workflow_state(snapshot: ModelWorkflowStateSnapshot) -> None` - Restore workflow state from a snapshot (validates schema version, timestamps, step ID overlaps)
- `get_workflow_snapshot(*, deep_copy: bool = False) -> dict[str, object] | None` - Return workflow state as a JSON-serializable dictionary

#### Properties

- `container: ModelONEXContainer` - Dependency injection container
- `workflow_definition: ModelWorkflowDefinition | None` - Injected workflow definition for coordination

## Service Wrapper Classes

> Tip: For comprehensive guidance and examples, see `src/omnibase_core/models/nodes/node_services/README.md`.

### ModelServiceCompute

**Location**: `omnibase_core.models.services.model_service_compute`

**Purpose**: Pre-composed COMPUTE node with common mixins.

```
from omnibase_core.models.services.model_service_compute import ModelServiceCompute
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

# Pre-composed with MixinNodeService, NodeCompute, MixinHealthCheck, MixinCaching, MixinMetrics
service = ModelServiceCompute(container)
```

### ModelServiceEffect

**Location**: `omnibase_core.models.services.model_service_effect`

**Purpose**: Pre-composed EFFECT node with common mixins.

```
from omnibase_core.models.services.model_service_effect import ModelServiceEffect
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

# Pre-composed with MixinNodeService, NodeEffect, MixinHealthCheck, MixinEventBus, MixinMetrics
service = ModelServiceEffect(container)
```

### ModelServiceReducer

**Location**: `omnibase_core.models.services.model_service_reducer`

**Purpose**: Pre-composed REDUCER node with common mixins.

```
from omnibase_core.models.services.model_service_reducer import ModelServiceReducer
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

# Pre-composed with MixinNodeService, NodeReducer, MixinHealthCheck, MixinCaching, MixinMetrics
service = ModelServiceReducer(container)
```

### ModelServiceOrchestrator

**Location**: `omnibase_core.models.services.model_service_orchestrator`

**Purpose**: Pre-composed ORCHESTRATOR node with common mixins.

```
from omnibase_core.models.services.model_service_orchestrator import ModelServiceOrchestrator
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

# Pre-composed with MixinNodeService, NodeOrchestrator, MixinHealthCheck, MixinEventBus, MixinMetrics
service = ModelServiceOrchestrator(container)
```

## Base Infrastructure Classes

### NodeCoreBase

**Location**: `omnibase_core.infrastructure.node_core_base`

**Purpose**: Abstract base class providing common infrastructure for all nodes.

```
from omnibase_core.infrastructure.node_core_base import NodeCoreBase

class MyCustomNode(NodeCoreBase):
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
```

#### Key Methods

- `__init__(container: ModelONEXContainer)` - Initialize with container
- `load_contracts()` - Load node contracts
- `emit_event(event: ModelEventEnvelope)` - Emit events
- `handle_error(error: Exception)` - Error handling

## Common Patterns

### Basic Node + Handler Implementation

Nodes are thin shells. Business logic belongs in handlers.

**Node** (`node.py`):
```python
from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.nodes import NodeCompute

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class MyBusinessLogicNode(NodeCompute):
    """Thin shell -- logic lives in HandlerBusinessLogic."""

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
```

**Handler** (`handlers/handler_business_logic.py`):
```python
from typing import Any
from uuid import UUID

from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode


class HandlerBusinessLogic:
    """COMPUTE handler -- returns result (required)."""

    async def handle(self, input_data: dict[str, Any], input_envelope_id: UUID, correlation_id: UUID) -> ModelHandlerOutput[dict[str, Any]]:
        """Process business logic and return result."""
        try:
            validated = self._validate(input_data)
            result = self._execute(validated)
            return ModelHandlerOutput.for_compute(
                input_envelope_id=input_envelope_id,
                correlation_id=correlation_id,
                handler_id="handler-business-logic",
                result=result,
            )
        except ValueError as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Validation failed: {e}",
            ) from e

    def _validate(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Validate input data."""
        return input_data

    def _execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute core business logic."""
        return {"result": "processed"}
```

### Error Handling Pattern

```python
from typing import Any
from uuid import UUID

from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode


class HandlerWithErrors:
    async def handle(self, input_data: dict[str, Any], input_envelope_id: UUID, correlation_id: UUID) -> ModelHandlerOutput[dict[str, Any]]:
        try:
            result = self._process(input_data)
            return ModelHandlerOutput.for_compute(
                input_envelope_id=input_envelope_id,
                correlation_id=correlation_id,
                handler_id="handler-with-errors",
                result=result,
            )
        except ValueError as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Validation failed: {e}",
            ) from e
        except Exception as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.PROCESSING_ERROR,
                message=f"Processing failed: {e}",
            ) from e
```

## Thread Safety

**Important**: ONEX node instances are **NOT thread-safe**. Do not share node instances across threads. See [Threading Guide](../../guides/THREADING.md) for details.

### Per-Request Instance Pattern (Recommended)

Create a fresh node instance for each request or thread. Do not use `threading.local()` as it leaks state across requests.

```python
# CORRECT: Per-request instance
async def handle_request(container: ModelONEXContainer, input_data: dict[str, Any]):
    node = MyComputeNode(container)  # Fresh instance per request
    return await node.process(input_data)
```

```python
# WRONG: Sharing node across threads
shared_node = MyComputeNode(container)  # NOT thread-safe
```

## Performance Considerations

### Caching

COMPUTE nodes include built-in caching via `ModelServiceCompute`. Caching is handled by the base class and does not require custom logic in the node or handler. Use `ModelServiceCompute` (Tier 1) for automatic caching.

### Metrics Collection

Metrics tracking is handled automatically by `MixinMetrics` when using `ModelServiceCompute` or `ModelServiceEffect`. No manual metric recording is required in handlers.

## Related Documentation

- [Node Building Guide](../../guides/node-building/README.md) - Complete tutorials
- [Threading Guide](../../guides/THREADING.md) - Thread safety considerations
- [Error Handling](../../conventions/ERROR_HANDLING_BEST_PRACTICES.md) - Error handling patterns
- [Architecture Overview](../../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) - System design
