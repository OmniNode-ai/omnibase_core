> **Navigation**: [Home](../INDEX.md) > [Architecture](./overview.md) > Dependency Injection
> **Note**: For authoritative coding standards, see [CLAUDE.md](../../CLAUDE.md).

# Dependency Injection

**Status**: Current
**Last Updated**: 2026-02-14

---

## Table of Contents

1. [Overview](#overview)
2. [Container Types: The Critical Distinction](#container-types-the-critical-distinction)
3. [ModelONEXContainer](#modelonexcontainer)
4. [ServiceRegistry](#serviceregistry)
5. [Protocol-Based Service Resolution](#protocol-based-service-resolution)
6. [Service Registration Patterns](#service-registration-patterns)
7. [String-Based vs Type-Based Resolution](#string-based-vs-type-based-resolution)
8. [Handler Resolution via DI](#handler-resolution-via-di)
9. [Contract-Driven Protocol Injection](#contract-driven-protocol-injection)
10. [Container Lifecycle](#container-lifecycle)
11. [Testing Patterns](#testing-patterns)
12. [Common Mistakes](#common-mistakes)

---

## Overview

ONEX uses **protocol-based dependency injection** to decouple nodes from concrete service implementations. The DI system centers on two components:

- **ModelONEXContainer**: The primary DI container that wraps service resolution, caching, and lifecycle management.
- **ServiceRegistry**: The registration and resolution engine that maps protocol interfaces to concrete implementations.

All service dependencies are resolved by protocol type, not by class name or string identifier. This enables loose coupling, easy testing through mock implementations, and swappable backends.

---

## Container Types: The Critical Distinction

ONEX has two container types that serve **completely different purposes**. Confusing them is a common and serious mistake.

| | ModelContainer[T] | ModelONEXContainer |
|---|---|---|
| **Purpose** | Generic value wrapper with metadata | Dependency injection container |
| **Location** | `omnibase_core.models.core.model_container` | `omnibase_core.models.container.model_onex_container` |
| **Use in node `__init__`** | NEVER | ALWAYS |
| **Primary method** | `map_value()`, `validate_with()` | `get_service()`, `get_service_async()` |
| **Service resolution** | No | Yes |
| **Lifecycle management** | No | Yes |
| **Type parameter** | `Generic[T]` | N/A |

### Decision Rule

```
Writing a node class?
    YES --> ModelONEXContainer in __init__
    NO  --> Wrapping a value with metadata?
              YES --> ModelContainer[T]
              NO  --> Resolving services?
                        YES --> ModelONEXContainer
                        NO  --> You probably need neither
```

See [Container Types](CONTAINER_TYPES.md) for the complete reference with examples.

---

## ModelONEXContainer

The `ModelONEXContainer` is the primary DI container for all ONEX applications. It is defined in `src/omnibase_core/models/container/model_onex_container.py`.

### Architecture

```text
ModelONEXContainer
    |
    +-- _BaseModelONEXContainer (dependency-injector based)
    |       |
    |       +-- config (Configuration provider)
    |       +-- enhanced_logger (Factory)
    |       +-- workflow_factory (Factory)
    |       +-- workflow_coordinator (Singleton)
    |       +-- action_registry (Singleton)
    |       +-- event_type_registry (Singleton)
    |       +-- command_registry (Singleton)
    |       +-- secret_manager (Singleton)
    |
    +-- ServiceRegistry (protocol-based DI)
    |
    +-- _service_cache (dict[str, object])
    |
    +-- tool_cache (optional MemoryMappedToolCache)
    |
    +-- performance_monitor (optional)
```

### Creating a Container

```python
from omnibase_core.models.container.model_onex_container import (
    ModelONEXContainer,
    create_model_onex_container,
)

# Simple creation
container = ModelONEXContainer(enable_service_registry=True)

# Factory function with full configuration (async)
container = await create_model_onex_container(
    enable_cache=True,
    enable_service_registry=True,
)
```

### Context-Based Access

For async and multi-threaded isolation, containers are managed through `contextvars`:

```python
from omnibase_core.models.container.model_onex_container import (
    get_model_onex_container,
    get_model_onex_container_sync,
)
from omnibase_core.context import run_with_container

# Async: get or create from context
container = await get_model_onex_container()

# Sync: get or create from context
container = get_model_onex_container_sync()

# Context manager (recommended for new code)
container = await create_model_onex_container()
async with run_with_container(container):
    current = await get_model_onex_container()
    assert current is container
```

### Node Initialization

Every node receives a `ModelONEXContainer` in its constructor:

```python
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodePriceCalculator(NodeCoreBase):
    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)  # Required -- do not skip

    async def process(self, input_data: PriceInput) -> PriceOutput:
        # Business logic lives in the handler, not here
        ...
```

Nodes are thin shells. The `__init__` method calls `super().__init__(container)` and nothing else. Business logic belongs in handlers, resolved through the contract system.

---

## ServiceRegistry

The `ServiceRegistry` is the engine behind protocol-based resolution. It lives in `src/omnibase_core/container/container_service_registry.py`.

### Capabilities

- Register services by interface type, existing instance, or factory
- Lifecycle management: singleton, transient (v2.0), scoped (v2.0)
- Service resolution by protocol interface or by name
- Health monitoring and status reporting
- Performance metrics tracking

### Accessing the Registry

```python
# Through the container
registry = container.service_registry

# The registry is initialized automatically when enable_service_registry=True
# Or explicitly:
container = ModelONEXContainer(enable_service_registry=False)
registry = container.initialize_service_registry()
```

### Registration Methods

```python
from omnibase_core.enums import EnumInjectionScope, EnumServiceLifecycle

# Register by interface + implementation class
reg_id = await registry.register_service(
    interface=ProtocolLogger,
    implementation=ConcreteLogger,
    lifecycle=EnumServiceLifecycle.SINGLETON,
    scope=EnumInjectionScope.GLOBAL,
)

# Register existing instance (always singleton)
reg_id = await registry.register_instance(
    interface=ProtocolLogger,
    instance=logger_instance,
    scope=EnumInjectionScope.GLOBAL,
)
```

### Resolution Methods

```python
# Resolve by interface (raises ModelOnexError if not found)
logger = await registry.resolve_service(ProtocolLogger)

# Try resolve (returns None if not found)
logger = await registry.try_resolve_service(ProtocolLogger)

# Resolve by name
logger = await registry.resolve_named_service(ProtocolLogger, "ConsoleLogger")

# Resolve all implementations of an interface
loggers = await registry.resolve_all_services(ProtocolLogger)
```

### Registry Status

```python
status = await registry.get_registry_status()
print(f"Total registrations: {status.total_registrations}")
print(f"Active instances: {status.active_instances}")
print(f"Failed registrations: {status.failed_registrations}")
```

---

## Protocol-Based Service Resolution

The preferred resolution pattern uses protocol types, not strings:

```python
from omnibase_core.protocols.logging.protocol_minimal_logger import ProtocolMinimalLogger
from omnibase_core.protocols.event_bus.protocol_event_bus_base import ProtocolEventBusBase
from omnibase_core.protocols.infrastructure import ProtocolDatabaseConnection

# Type-based resolution (preferred)
logger = container.get_service(ProtocolMinimalLogger)
event_bus = await container.get_service_async(ProtocolEventBusBase)
database = await container.get_database()

# Optional resolution (returns None instead of raising)
cache = container.get_service_optional(ProtocolComputeCache)
```

### How Resolution Works

1. The container receives a protocol type (e.g., `ProtocolLogger`).
2. It checks the internal `_service_cache` for a cached instance.
3. If not cached, it delegates to `ServiceRegistry.resolve_service()`.
4. The registry looks up the protocol name in `_interface_map`.
5. It retrieves the registration and resolves by lifecycle (singleton returns existing instance).
6. The resolved instance is cached in `_service_cache` for future calls.
7. The typed instance is returned.

### Resolution Flow

```text
container.get_service(ProtocolLogger)
    |
    +-- Check _service_cache["ProtocolLogger:default"]
    |       |
    |       +-- HIT: return cached instance
    |       +-- MISS: continue
    |
    +-- registry.resolve_service(ProtocolLogger)
    |       |
    |       +-- _interface_map["ProtocolLogger"] -> [registration_id]
    |       +-- _resolve_by_lifecycle(registration_id, ...)
    |       +-- return instance
    |
    +-- Cache instance in _service_cache
    |
    +-- Return typed instance
```

---

## Service Registration Patterns

### Singleton (Default for Instances)

Services registered via `register_instance` are always singletons. The same instance is returned on every resolution:

```python
logger = ConcreteLogger(level="INFO")
await registry.register_instance(
    interface=ProtocolLogger,
    instance=logger,
    scope=EnumInjectionScope.GLOBAL,
)

# Same instance every time
resolved_1 = await registry.resolve_service(ProtocolLogger)
resolved_2 = await registry.resolve_service(ProtocolLogger)
assert resolved_1 is resolved_2
```

### Class-Based Registration

Register an interface with its implementation class. The registry creates the instance:

```python
await registry.register_service(
    interface=ProtocolLogger,
    implementation=ConcreteLogger,
    lifecycle=EnumServiceLifecycle.SINGLETON,
    scope=EnumInjectionScope.GLOBAL,
)
```

### Multiple Implementations

Multiple implementations can be registered for the same interface:

```python
await registry.register_instance(
    interface=ProtocolLogger,
    instance=ConsoleLogger(),
)
await registry.register_instance(
    interface=ProtocolLogger,
    instance=FileLogger("/var/log/app.log"),
)

# resolve_service returns the first registration
primary = await registry.resolve_service(ProtocolLogger)

# resolve_all_services returns all implementations
all_loggers = await registry.resolve_all_services(ProtocolLogger)
assert len(all_loggers) == 2
```

### Unregistration

```python
success = await registry.unregister_service(registration_id)
```

---

## String-Based vs Type-Based Resolution

ONEX supports both resolution styles but enforces consistency rules.

### Type-Based Resolution (Preferred)

```python
# Pass the protocol type directly
logger = container.get_service(ProtocolLogger)
event_bus = await container.get_service_async(ProtocolEventBusBase)
```

Advantages:
- Full mypy type checking on the return value
- IDE autocompletion
- Refactoring safety
- No magic strings

### String-Based Resolution (Allowed for Late-Binding)

String-based resolution is permitted for plugins or late-binding scenarios where the protocol type is not known at import time:

```python
# String-based via service name
service = container.get_service(object, service_name="contract_validator_registry")
```

### Consistency Rule

**Never mix resolution styles within the same module.** Pick one approach per module and use it consistently. Type-based is the default; string-based is the exception for late-binding plugins.

---

## Handler Resolution via DI

Handlers are resolved through the contract system, not through direct DI container calls. The flow is:

1. A node's YAML contract specifies its handler binding.
2. `NodeCoreBase.__init__` loads the contract and calls `resolve_handler()`.
3. `resolve_handler()` returns a `HandlerCallable` or `LazyLoader`.
4. The handler callable receives the container for its own service resolution.

```python
from omnibase_core.resolution.resolver_handler import resolve_handler, HandlerCallable

# Called internally by NodeCoreBase during initialization
handler: HandlerCallable = resolve_handler(contract_data, container)
```

Handlers themselves may use the container to resolve their own dependencies:

```python
class PriceCalculatorHandler:
    def __init__(self, container: ModelONEXContainer) -> None:
        self.cache = container.get_service_optional(ProtocolComputeCache)

    async def execute(self, input_data: PriceInput) -> PriceOutput:
        # Handler owns all business logic
        if self.cache:
            cached = self.cache.get(input_data.product_id)
            if cached:
                return cached
        result = self._calculate_price(input_data)
        return result
```

---

## Contract-Driven Protocol Injection

Contracts can declare protocol dependencies that are automatically resolved and bound to the node's `self.protocols` namespace. This is defined via the `protocol_dependencies` field in YAML contracts.

```yaml
protocol_dependencies:
  - name: ProtocolEventBus
    protocol: "omnibase_core.protocols.event_bus:ProtocolEventBus"
    required: true
  - name: ProtocolLogger
    protocol: "omnibase_core.protocols.logging:ProtocolMinimalLogger"
    required: false
```

At node initialization, the framework calls `resolve_protocol_dependencies()`, which:

1. Iterates over `contract.protocol_dependencies`.
2. Resolves each protocol from the `ModelONEXContainer`.
3. Binds resolved instances to `self.protocols.<bind_name>`.
4. Raises `ModelOnexError` for required protocols that cannot be resolved.
5. Sets `None` for optional protocols that are unavailable.

```python
# After initialization, access resolved protocols
event_bus = self.protocols.ProtocolEventBus
logger = self.protocols.ProtocolLogger
```

The `ModelProtocolDependency` model is defined in `src/omnibase_core/models/contracts/subcontracts/model_protocol_dependency.py`:

```python
from omnibase_core.models.contracts.subcontracts.model_protocol_dependency import (
    ModelProtocolDependency,
)

dep = ModelProtocolDependency(
    name="ProtocolEventBus",
    protocol="omnibase_core.protocols.event_bus:ProtocolEventBus",
    required=True,
)
```

---

## Container Lifecycle

### Creation and Configuration

```python
# Factory function sets up configuration, warms caches
container = await create_model_onex_container(
    enable_cache=True,
    enable_service_registry=True,
)
```

The factory function loads configuration from environment variables and populates the base container's `config` provider with settings for logging, Consul, workflows, and database circuit breakers.

### Performance Monitoring

When `enable_performance_cache=True`, the container initializes:

- `MemoryMappedToolCache` for fast tool metadata lookups
- `PerformanceMonitor` for tracking resolution times and cache hit rates

```python
stats = container.get_performance_stats()
# Returns: container_type, cache_enabled, base_metrics, tool_cache stats

checkpoint = await container.run_performance_checkpoint("production")
```

### Cleanup

```python
container.close()  # Releases memory-mapped files and logs shutdown
```

### Thread Safety

`ModelONEXContainer` is **NOT thread-safe**. Use separate instances per thread, or use the context-based management functions (`get_model_onex_container()`) which provide proper isolation through `contextvars`.

---

## Testing Patterns

### Creating a Test Container

```python
import pytest
from omnibase_core.models.container.model_onex_container import ModelONEXContainer


@pytest.fixture
def container() -> ModelONEXContainer:
    return ModelONEXContainer(enable_service_registry=True)
```

### Registering Mock Services

```python
class MockLogger:
    def info(self, message: str) -> None:
        pass

    def error(self, message: str, exc_info: bool = False) -> None:
        pass


@pytest.fixture
async def container_with_mocks(container: ModelONEXContainer) -> ModelONEXContainer:
    await container.service_registry.register_instance(
        interface=ProtocolLogger,
        instance=MockLogger(),
    )
    return container
```

### Testing Node Initialization

```python
@pytest.mark.unit
async def test_node_initialization(container_with_mocks: ModelONEXContainer) -> None:
    node = MyNode(container_with_mocks)
    assert node.container is container_with_mocks
```

### Testing Service Resolution

```python
@pytest.mark.unit
async def test_service_resolution(container_with_mocks: ModelONEXContainer) -> None:
    logger = await container_with_mocks.get_service_async(ProtocolLogger)
    assert logger is not None
    assert isinstance(logger, MockLogger)
```

### Testing Optional Services

```python
@pytest.mark.unit
def test_optional_service_returns_none(container: ModelONEXContainer) -> None:
    result = container.get_service_optional(ProtocolComputeCache)
    assert result is None
```

---

## Common Mistakes

### Using ModelContainer in Node __init__

```python
# WRONG
class MyNode(NodeCoreBase):
    def __init__(self, container: ModelContainer) -> None:  # Wrong type
        super().__init__(container)  # Will fail

# CORRECT
class MyNode(NodeCoreBase):
    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
```

### Skipping super().__init__

```python
# WRONG
class MyNode(NodeCoreBase):
    def __init__(self, container: ModelONEXContainer) -> None:
        self.container = container  # Missing super().__init__

# CORRECT
class MyNode(NodeCoreBase):
    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)  # Required
```

### Mixing Resolution Styles in One Module

```python
# WRONG -- mixing string-based and type-based in one module
logger = container.get_service(ProtocolLogger)
cache = container.get_service(object, service_name="cache_registry")

# CORRECT -- pick one style per module (prefer type-based)
logger = container.get_service(ProtocolLogger)
cache = container.get_service(ProtocolComputeCache)
```

### Putting Business Logic in Nodes

```python
# WRONG -- logic in node
class NodePriceCalculator(NodeCoreBase):
    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)

    async def process(self, input_data: PriceInput) -> PriceOutput:
        # All this logic should be in a handler
        base_price = input_data.price
        discount = base_price * 0.1
        return PriceOutput(final_price=base_price - discount)

# CORRECT -- delegate to handler
class NodePriceCalculator(NodeCoreBase):
    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)

    async def process(self, input_data: PriceInput) -> PriceOutput:
        handler = resolve_handler(self.contract_data, self.container)
        return await handler(input_data)
```

### Using get_service_sync in Async Code

```python
# WRONG -- blocks the event loop
async def my_async_function(container: ModelONEXContainer) -> None:
    logger = container.get_service(ProtocolLogger)  # Calls asyncio.run() internally

# CORRECT -- use async variant
async def my_async_function(container: ModelONEXContainer) -> None:
    logger = await container.get_service_async(ProtocolLogger)
```

---

## Related Documentation

- [Container Types](CONTAINER_TYPES.md) -- ModelContainer[T] vs ModelONEXContainer with full examples
- [Contract System](CONTRACT_SYSTEM.md) -- YAML contract definitions and validation
- [Type System](TYPE_SYSTEM.md) -- Type conventions and protocol typing
- [ONEX Four-Node Architecture](ONEX_FOUR_NODE_ARCHITECTURE.md) -- Node kinds and their roles
- [Node Building Guide](../guides/node-building/README.md) -- How to build nodes
- [Error Handling Best Practices](../conventions/ERROR_HANDLING_BEST_PRACTICES.md)
