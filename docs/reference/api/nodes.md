# Nodes API Reference - omnibase_core

**Status**: 🚧 Coming Soon

## Overview

Complete API reference for all ONEX node base classes.

## Node Base Classes

### NodeEffectService

**Location**: `omnibase_core.core.node_effect_service`

Base class for EFFECT nodes that handle external interactions.

```python
class NodeEffectService(NodeCoreBase):
    """Base class for EFFECT nodes."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)

    async def execute_effect(
        self,
        contract: ModelContractEffect
    ) -> ModelResult:
        """Execute external operation."""
        pass
```

### NodeComputeService

**Location**: `omnibase_core.core.node_compute_service`

Base class for COMPUTE nodes that perform pure transformations.

```python
class NodeComputeService(NodeCoreBase):
    """Base class for COMPUTE nodes."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)

    async def execute_compute(
        self,
        contract: ModelContractCompute
    ) -> ModelResult:
        """Execute computation."""
        pass
```

### NodeReducerService

**Location**: `omnibase_core.core.node_reducer_service`

Base class for REDUCER nodes that manage state with pure FSM pattern.

```python
class NodeReducerService(NodeCoreBase):
    """Base class for REDUCER nodes."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)

    async def execute_reduction(
        self,
        state: ModelState,
        action: ModelAction
    ) -> Tuple[ModelState, List[ModelIntent]]:
        """Execute state reduction (pure FSM)."""
        pass
```

### NodeOrchestratorService

**Location**: `omnibase_core.core.node_orchestrator_service`

Base class for ORCHESTRATOR nodes that coordinate workflows.

```python
class NodeOrchestratorService(NodeCoreBase):
    """Base class for ORCHESTRATOR nodes."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)

    async def execute_orchestration(
        self,
        contract: ModelContractOrchestrator
    ) -> ModelResult:
        """Execute workflow orchestration."""
        pass
```

## NodeCoreBase

Common base class for all nodes.

### Methods

#### `__init__(container: ModelONEXContainer)`

Initialize node with container.

#### `get_service(protocol_name: str) -> Any`

Resolve service by protocol name.

#### `async def health_check() -> ModelHealthStatus`

Check node health status.

## Next Steps

- [Models API](models.md) - Model reference
- [Enums API](enums.md) - Enumeration reference
- [Node Building Guide](../../guides/node-building/README.md)

---

**Related Documentation**:
- [ONEX Architecture](../../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)
- [Node Templates](../templates/)
