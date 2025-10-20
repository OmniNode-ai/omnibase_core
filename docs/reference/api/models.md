# Models API Reference - omnibase_core

**Status**: 🚧 Coming Soon

## Overview

Complete API reference for all ONEX Pydantic models.

## Core Models

### ModelEventEnvelope

Event communication envelope for inter-service messaging.

```python
class ModelEventEnvelope(BaseModel):
    """Event envelope for service communication."""
    event_type: str
    payload: dict
    metadata: Optional[dict] = None
    timestamp: datetime
    correlation_id: UUID
```

### ModelHealthStatus

Health status reporting for nodes and services.

```python
class ModelHealthStatus(BaseModel):
    """Health status model."""
    status: EnumHealthStatus
    timestamp: datetime
    details: Optional[dict] = None
```

### ModelSemver

Semantic versioning model.

```python
class ModelSemver(BaseModel):
    """Semantic version model."""
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"
```

## Contract Models

### ModelContractBase

Base contract for all operations.

```python
class ModelContractBase(BaseModel):
    """Base contract."""
    name: str
    version: str
    description: Optional[str]
    node_type: EnumNodeType
```

### ModelContractEffect

Contract for EFFECT nodes.

```python
class ModelContractEffect(ModelContractBase):
    """EFFECT node contract."""
    operation_type: str
    target: str
    parameters: dict
```

### ModelContractCompute

Contract for COMPUTE nodes.

```python
class ModelContractCompute(ModelContractBase):
    """COMPUTE node contract."""
    input_data: dict
    cache_config: Optional[ModelCacheConfig] = None
```

### ModelContractReducer

Contract for REDUCER nodes.

```python
class ModelContractReducer(ModelContractBase):
    """REDUCER node contract."""
    state_key: str
    aggregation_config: dict
```

### ModelContractOrchestrator

Contract for ORCHESTRATOR nodes.

```python
class ModelContractOrchestrator(ModelContractBase):
    """ORCHESTRATOR node contract."""
    workflow_definition: dict
    execution_mode: str
```

## Container Models

### ModelONEXContainer

Protocol-driven dependency injection container.

```python
class ModelONEXContainer(BaseModel):
    """DI container."""

    def get_service(self, protocol_name: str) -> Any:
        """Get service by protocol."""
        pass

    def register_service(
        self,
        protocol_name: str,
        implementation: Any
    ) -> None:
        """Register service."""
        pass
```

## Error Models

### ModelOnexError

Structured error model.

```python
class ModelOnexError(BaseModel):
    """Error model."""
    message: str
    error_code: EnumErrorCode
    context: Optional[dict] = None
    timestamp: datetime
```

## Next Steps

- [Nodes API](nodes.md) - Node reference
- [Enums API](enums.md) - Enumeration reference
- [Contract System](../../architecture/contract-system.md)

---

**Related Documentation**:
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Type System](../../architecture/type-system.md)
