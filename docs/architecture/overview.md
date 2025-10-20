# Architecture Overview - omnibase_core

**Status**: 🚧 Coming Soon

## Overview

High-level overview of the ONEX framework architecture and design principles.

## Core Concepts

### 1. Four-Node Pattern

The foundation of ONEX is the four-node architecture:
- **EFFECT**: External interactions (I/O, APIs, databases)
- **COMPUTE**: Pure transformations and calculations
- **REDUCER**: State aggregation with FSM pattern
- **ORCHESTRATOR**: Workflow coordination

**See**: [ONEX Four-Node Architecture](ONEX_FOUR_NODE_ARCHITECTURE.md) for complete details.

### 2. Protocol-Driven Dependency Injection

Services are resolved by protocol interfaces, not concrete implementations:
```python
event_bus = container.get_service("ProtocolEventBus")
```

**See**: [Dependency Injection](dependency-injection.md) for patterns.

### 3. Contract System

All nodes operate on typed contracts (Pydantic models):
```python
class ModelContractCompute(BaseModel):
    input_data: dict
    cache_config: Optional[ModelCacheConfig]
```

**See**: [Contract System](contract-system.md) for architecture.

### 4. Event-Driven Communication

Nodes communicate via ModelEventEnvelope:
```python
envelope = ModelEventEnvelope(
    event_type="data_processed",
    payload=result
)
```

## Design Principles

1. **Zero Boilerplate**: Base classes eliminate repetitive code
2. **Type Safety**: Full Pydantic validation and mypy compliance
3. **SOLID Principles**: Single responsibility, dependency inversion
4. **Fail-Fast**: Early error detection with structured errors
5. **Testability**: Pure functions and dependency injection enable easy testing

## Architecture Layers

```
┌─────────────────────────────────────┐
│         Application Layer           │  Your nodes
│  (EFFECT/COMPUTE/REDUCER/ORCHESTR)  │
├─────────────────────────────────────┤
│        Framework Layer              │  omnibase_core
│    (Base classes, Container, DI)    │
├─────────────────────────────────────┤
│        Protocol Layer               │  omnibase_spi
│     (Interface definitions)          │
└─────────────────────────────────────┘
```

## Key Components

### Node Base Classes
- `NodeEffectService`
- `NodeComputeService`
- `NodeReducerService`
- `NodeOrchestratorService`

### Container
- `ModelONEXContainer` - Protocol-driven DI container

### Models
- `ModelEventEnvelope` - Event communication
- `ModelContractBase` - Base contract
- `ModelHealthStatus` - Health reporting

### Error Handling
- `OnexError` - Structured exceptions
- `@standard_error_handling` - Error decorator

## Architecture Benefits

- **Reduced Complexity**: 80+ lines less code per node
- **Type Safety**: Compile-time error detection
- **Maintainability**: Clear separation of concerns
- **Scalability**: Event-driven, stateless design
- **Testability**: Pure functions, dependency injection

## Next Steps

- [ONEX Four-Node Architecture](ONEX_FOUR_NODE_ARCHITECTURE.md) - Deep dive
- [Dependency Injection](dependency-injection.md) - DI patterns
- [Contract System](contract-system.md) - Contract architecture
- [Type System](type-system.md) - Type conventions

---

**Related Documentation**:
- [Node Building Guide](../guides/node-building/README.md)
- [Error Handling](../conventions/ERROR_HANDLING_BEST_PRACTICES.md)
- [Threading Guide](../reference/THREADING.md)
