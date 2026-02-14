> **Navigation**: [Home](../../INDEX.md) > [Reference](../README.md) > API > Nodes

# Nodes API Reference - omnibase_core

**Status**: ✅ Complete

## Overview

This document provides comprehensive API reference for all node classes in omnibase_core. The ONEX framework provides four core node types: COMPUTE, EFFECT, REDUCER, and ORCHESTRATOR.

## Core Node Classes

### NodeCompute

**Location**: `omnibase_core.nodes.node_compute`

**Purpose**: Pure computation nodes for business logic and data transformation.

```
from omnibase_core.nodes.node_compute import NodeCompute
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class MyComputeNode(NodeCompute):
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # Your computation logic here
        return {"result": "computed_value"}
```

#### Key Methods

- `__init__(container: ModelONEXContainer)` - Initialize with dependency injection container
- `async process(input_data: Dict[str, Any]) -> Dict[str, Any]` - Main processing method
- `get_metrics() -> Dict[str, Any]` - Get performance metrics
- `health_check() -> Dict[str, Any]` - Health status check

#### Properties

- `container: ModelONEXContainer` - Dependency injection container
- `computation_cache: ModelComputeCache` - LRU cache for results
- `performance_metrics: Dict[str, Any]` - Performance tracking data

### NodeEffect

**Location**: `omnibase_core.nodes.node_effect`

**Purpose**: Side effect nodes for external interactions (databases, APIs, file systems).

```
from omnibase_core.nodes.node_effect import NodeEffect
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class DatabaseEffectNode(NodeEffect):
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # Your side effect logic here
        return {"status": "completed"}
```

#### Key Methods

- `__init__(container: ModelONEXContainer)` - Initialize with dependency injection container
- `async process(input_data: Dict[str, Any]) -> Dict[str, Any]` - Main processing method
- `async transaction_context(operation_id: UUID)` - Transaction management context
- `get_circuit_breaker_status() -> Dict[str, Any]` - Circuit breaker status

#### Properties

- `container: ModelONEXContainer` - Dependency injection container
- `circuit_breakers: Dict[str, ModelCircuitBreaker]` - Circuit breaker instances
- `transaction_manager: ModelEffectTransaction` - Transaction management

### NodeReducer

**Location**: `omnibase_core.nodes.node_reducer`

**Purpose**: State management nodes for data aggregation and state transitions.

```
from omnibase_core.nodes.node_reducer import NodeReducer
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class MetricsReducerNode(NodeReducer):
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # Your state management logic here
        return {"state": "updated"}
```

#### Key Methods

- `__init__(container: ModelONEXContainer)` - Initialize with dependency injection container
- `async process(input_data: Dict[str, Any]) -> Dict[str, Any]` - Main processing method
- `get_current_state() -> Dict[str, Any]` - Get current state
- `emit_intent(intent: ModelIntent)` - Emit intent for side effects (import from `omnibase_core.models.reducer.model_intent`)

#### Properties

- `container: ModelONEXContainer` - Dependency injection container
- `current_state: Dict[str, Any]` - Current state data
- `state_history: List[Dict[str, Any]]` - State change history

### NodeOrchestrator

**Location**: `omnibase_core.nodes.node_orchestrator`

**Purpose**: Workflow coordination nodes for managing complex business processes.

```
from omnibase_core.nodes.node_orchestrator import NodeOrchestrator
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class WorkflowOrchestratorNode(NodeOrchestrator):
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # Your orchestration logic here
        return {"workflow": "completed"}
```

#### Key Methods

- `__init__(container: ModelONEXContainer)` - Initialize with dependency injection container
- `async process(input_data: Dict[str, Any]) -> Dict[str, Any]` - Main processing method
- `async coordinate_workflow(workflow_data: Dict[str, Any])` - Coordinate workflow execution
- `get_workflow_status(workflow_id: str) -> Dict[str, Any]` - Get workflow status

#### Properties

- `container: ModelONEXContainer` - Dependency injection container
- `active_workflows: Dict[str, Dict[str, Any]]` - Active workflow instances
- `workflow_templates: Dict[str, Dict[str, Any]]` - Workflow templates

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

### Basic Node Implementation

```
from omnibase_core.nodes.node_compute import NodeCompute
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from typing import Dict, Any

class MyBusinessLogicNode(NodeCompute):
    """Example COMPUTE node implementation."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        # Initialize your business logic components

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main processing method."""
        try:
            # Validate input
            validated_input = self._validate_input(input_data)

            # Process business logic
            result = await self._execute_business_logic(validated_input)

            # Return result
            return {"success": True, "result": result}

        except Exception as e:
            # Handle errors
            return {"success": False, "error": str(e)}

    def _validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate input data."""
        # Add validation logic
        return input_data

    async def _execute_business_logic(self, input_data: Dict[str, Any]) -> Any:
        """Execute core business logic."""
        # Add business logic
        return "processed_result"
```

### Error Handling Pattern

```
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # Your logic here
        return {"result": "success"}
    except ValueError as e:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Validation failed: {str(e)}",
            context={"input_data": input_data}
        ) from e
    except Exception as e:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.PROCESSING_ERROR,
            message=f"Processing failed: {str(e)}",
            context={"input_data": input_data}
        ) from e
```

### Health Check Pattern

```
async def health_check(self) -> Dict[str, Any]:
    """Implement health check."""
    try:
        # Check dependencies
        container_healthy = self.container is not None

        # Check internal state
        internal_healthy = self._check_internal_state()

        return {
            "status": "healthy" if container_healthy and internal_healthy else "unhealthy",
            "components": {
                "container": "healthy" if container_healthy else "unhealthy",
                "internal_state": "healthy" if internal_healthy else "unhealthy"
            },
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }
```

## Thread Safety

**Important**: Most ONEX node components are **NOT thread-safe by default**. See [Threading Guide](../../guides/THREADING.md) for details.

### Thread-Safe Usage

```
import threading

# Option 1: Per-thread instances
thread_local = threading.local()

def get_node_instance(container):
    if not hasattr(thread_local, 'node'):
        thread_local.node = MyComputeNode(container)
    return thread_local.node

# Option 2: Use service wrappers with thread-safe mixins
from omnibase_core.models.services.model_service_compute import ModelServiceCompute
service = ModelServiceCompute(container)  # May include thread-safe patterns
```

## Performance Considerations

### Caching

```
# COMPUTE nodes include built-in caching
class MyComputeNode(NodeCompute):
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # Check cache first
        cache_key = self._generate_cache_key(input_data)
        cached_result = self.computation_cache.get(cache_key)
        if cached_result:
            return cached_result

        # Compute result
        result = await self._compute(input_data)

        # Cache result
        self.computation_cache.put(cache_key, result)
        return result
```

### Metrics Collection

```
# All nodes support metrics collection
class MyNode(NodeCompute):
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()

        try:
            result = await self._process(input_data)

            # Record success metrics
            self.record_metric("processing_time", time.time() - start_time)
            self.record_metric("success_count", 1)

            return result
        except Exception as e:
            # Record error metrics
            self.record_metric("error_count", 1)
            raise
```

## Related Documentation

- [Node Building Guide](../../guides/node-building/README.md) - Complete tutorials
- [Threading Guide](../../guides/THREADING.md) - Thread safety considerations
- [Error Handling](../../conventions/ERROR_HANDLING_BEST_PRACTICES.md) - Error handling patterns
- [Architecture Overview](../../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) - System design
