# Architecture Overview - omnibase_core

**Status**: ✅ Complete

## Overview

This document provides a high-level overview of the ONEX architecture and its core components. The ONEX framework is built on a four-node pattern that provides clear separation of concerns, type safety, and scalable architecture for building distributed systems.

## Core Architecture Principles

### 1. Four-Node Pattern

The ONEX framework is built around four distinct node types, each with specific responsibilities:

- **COMPUTE** - Pure computation and data transformation
- **EFFECT** - External interactions and side effects
- **REDUCER** - State management and data aggregation
- **ORCHESTRATOR** - Workflow coordination and business process management

### 2. Protocol-Driven Dependency Injection

All nodes use the `ModelONEXContainer` for dependency injection, providing:
- Service resolution by protocol
- Lazy loading of dependencies
- Type-safe service registration
- Lifecycle management

### 3. Contract System

The framework uses Pydantic models for:
- Input/output validation
- Type safety
- API contracts
- Serialization/deserialization

### 4. Event-Driven Communication

Nodes communicate through:
- `ModelEventEnvelope` for inter-node messaging
- `ModelIntent` for side effect requests
- `ModelAction` for state transitions
- Asynchronous processing

## System Architecture

### High-Level Components

```text
┌─────────────────────────────────────────────────────────────┐
│                    ONEX Framework                           │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────┐ │
│  │   COMPUTE   │  │    EFFECT   │  │   REDUCER   │  │ ORC │ │
│  │   Nodes     │  │   Nodes     │  │   Nodes     │  │Nodes│ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────┘ │
├─────────────────────────────────────────────────────────────┤
│              Protocol-Driven DI Container                   │
│              (ModelONEXContainer)                           │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────┐ │
│  │   Models    │  │   Events    │  │   Errors    │  │Utils│ │
│  │  (Pydantic) │  │  (Async)    │  │ (Structured)│  │     │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────┘ │
└─────────────────────────────────────────────────────────────┘
```python

### Node Responsibilities

#### COMPUTE Nodes
- **Purpose**: Pure computation and data transformation
- **Characteristics**:
  - Deterministic (same input = same output)
  - Stateless
  - Cacheable
  - Parallelizable
- **Examples**: Calculations, data validation, format conversion

#### EFFECT Nodes
- **Purpose**: External interactions and side effects
- **Characteristics**:
  - Non-deterministic
  - Stateful (external state)
  - Circuit breaker protection
  - Transaction management
- **Examples**: Database operations, API calls, file I/O

#### REDUCER Nodes
- **Purpose**: State management and data aggregation
- **Characteristics**:
  - Pure state transitions
  - Immutable state updates
  - Event sourcing support
  - Intent emission
- **Examples**: State machines, data aggregation, metrics collection

#### ORCHESTRATOR Nodes
- **Purpose**: Workflow coordination and business process management
- **Characteristics**:
  - Workflow management
  - Business logic coordination
  - Error handling and recovery
  - Monitoring and observability
- **Examples**: Business processes, workflow engines, saga patterns

## Design Principles

### 1. Zero Boilerplate
- Base classes handle common functionality
- Mixins provide optional capabilities
- Service wrappers for common patterns
- Automatic error handling and logging

### 2. Type Safety
- Pydantic models for validation
- Type hints throughout
- MyPy compatibility
- Runtime type checking

### 3. SOLID Principles
- Single Responsibility Principle (each node type has one purpose)
- Open/Closed Principle (extensible through mixins)
- Liskov Substitution Principle (interchangeable implementations)
- Interface Segregation Principle (focused interfaces)
- Dependency Inversion Principle (protocol-based DI)

### 4. Fail-Fast
- Input validation at boundaries
- Early error detection
- Circuit breaker patterns
- Graceful degradation

### 5. Testability
- Dependency injection for mocking
- Pure functions where possible
- Isolated side effects
- Comprehensive error handling

## Architecture Layers

### 1. Application Layer
- Business logic nodes
- Workflow orchestration
- Domain-specific implementations

### 2. Service Layer
- Service wrappers with mixins (prefer `ModelService*` for production nodes)
- Common patterns and utilities
- Cross-cutting concerns

> Note on terminology: "Service wrappers" are pre-composed node classes (internal to ONEX) and are not the same as external services (APIs, DBs). External services are injected via the container; service wrappers describe how nodes are composed internally.

### 3. Infrastructure Layer
- Base node classes
- Container and DI
- Event system
- Error handling

### 4. Foundation Layer
- Pydantic models
- Enums and constants
- Utility functions
- Core protocols

## Key Components

### Dependency Injection Container

```python
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

container = ModelONEXContainer()
container.register_service("DatabaseService", db_service)
container.register_service("CacheService", cache_service)

# Resolve services
db_service = container.get_service("DatabaseService")
```python

### Event System

```python
from omnibase_core.models.model_event_envelope import ModelEventEnvelope

# Emit event
event = ModelEventEnvelope(
    event_type="data_processed",
    payload={"result": "success"},
    source_node="compute_node",
    target_node="effect_node"
)
await node.emit_event(event)
```python

### Error Handling

```python
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

try:
    result = await process_data(input_data)
except Exception as e:
    raise ModelOnexError(
        error_code=EnumCoreErrorCode.PROCESSING_ERROR,
        message=f"Processing failed: {str(e)}",
        context={"input_data": input_data}
    ) from e
```python

### Circuit Breaker Pattern

```python
from omnibase_core.utils.circuit_breaker import CircuitBreaker

breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60
)

try:
    result = await breaker.call(risky_operation)
except CircuitBreakerOpenException:
    result = fallback_operation()
```python

## Benefits

### 1. Scalability
- Horizontal scaling through node distribution
- Independent node deployment
- Load balancing and failover

### 2. Maintainability
- Clear separation of concerns
- Modular architecture
- Comprehensive testing support

### 3. Reliability
- Circuit breaker patterns
- Retry mechanisms
- Graceful degradation
- Comprehensive error handling

### 4. Developer Experience
- Type safety and validation
- Clear patterns and conventions
- Comprehensive documentation
- Rich tooling support

### 5. Observability
- Structured logging
- Performance metrics
- Health checks
- Distributed tracing support

## Getting Started

### 1. Choose Your Node Type
- **COMPUTE**: For pure calculations and transformations
- **EFFECT**: For external interactions (databases, APIs)
- **REDUCER**: For state management and aggregation
- **ORCHESTRATOR**: For workflow coordination

### 2. Implement Your Node
Prefer a service wrapper to eliminate boilerplate and ensure correct mixin ordering:
```python
from omnibase_core.models.nodes.node_services import ModelServiceCompute

class MyComputeService(ModelServiceCompute):
    pass
```python

Or compose manually only when you need specialized capabilities:
```python
from omnibase_core.nodes.node_compute import NodeCompute
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class MyComputeNode(NodeCompute):
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # Your business logic here
        return {"result": "processed"}
```python

### 3. Add Error Handling
```python
from omnibase_core.utils.standard_error_handling import standard_error_handling

@standard_error_handling(
    error_class=ModelOnexError,
    component="MyComputeNode",
    operation="process"
)
async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
    # Your logic here
    return {"result": "processed"}
```python

### 4. Add Testing
```python
import pytest
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

@pytest.fixture
def container():
    return ModelONEXContainer()

@pytest.fixture
def node(container):
    return MyComputeNode(container)

@pytest.mark.asyncio
async def test_process(node):
    result = await node.process({"input": "test"})
    assert result["result"] == "processed"
```text

## Related Documentation

- [Four-Node Architecture](ONEX_FOUR_NODE_ARCHITECTURE.md) - Detailed node architecture
- [Dependency Injection](DEPENDENCY_INJECTION.md) - Container patterns
- [Contract System](CONTRACT_SYSTEM.md) - Model contracts
- [Type System](TYPE_SYSTEM.md) - Typing patterns
- [Node Building Guide](../guides/node-building/README.md) - Implementation tutorials
- [API Reference](../reference/api/) - Complete API documentation
