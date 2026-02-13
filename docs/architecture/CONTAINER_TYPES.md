> **Navigation**: [Home](../INDEX.md) > [Architecture](./overview.md) > Container Types
> **Note**: For authoritative coding standards, see [CLAUDE.md](../../CLAUDE.md).

# Container Types in omnibase_core

**Status**: ✅ Complete
**Version**: 0.4.0
**Last Updated**: 2025-12-13

---

## Overview

omnibase_core uses TWO distinct container types that serve completely different purposes. Confusing these types is a common mistake that can lead to incorrect implementations.

**CRITICAL**: `ModelContainer[T]` and `ModelONEXContainer` are NOT interchangeable!

---

## The Two Container Types

### 1. ModelContainer[T] - Generic Value Wrapper

**Location**: `omnibase_core.models.core.model_container`

**Purpose**: Generic container for single values with metadata and validation.

**Use Cases**:
- Wrapping values with validation metadata
- Adding source tracking to data
- Implementing value transformation pipelines
- Type-safe value passing with context

**Example**:
```
from omnibase_core.models.core.model_container import ModelContainer

# Create a value container
config_value = ModelContainer.create(
    value="production",
    container_type="environment",
    source="env_var",
    is_validated=True
)

# Transform the value
new_value = config_value.map_value(lambda x: x.upper())

# Validate the value
config_value.validate_with(
    validator=lambda x: x in ["production", "development"],
    error_message="Invalid environment"
)
```

**Key Characteristics**:
- Generic type parameter `T` for the wrapped value
- Pydantic BaseModel for validation
- Includes metadata: `source`, `is_validated`, `validation_notes`
- Provides transformation methods: `map_value()`, `validate_with()`
- **NOT used for dependency injection**
- **NOT used in node constructors**

---

### 2. ModelONEXContainer - Dependency Injection Container

**Location**: `omnibase_core.models.container.model_onex_container`

**Purpose**: Dependency injection container for service resolution and lifecycle management.

**Use Cases**:
- Service resolution in nodes (`container.get_service()`)
- Workflow orchestration
- Configuration management
- Lifecycle management
- Service caching and performance monitoring

**Example**:
```
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
# v0.3.6+: Core-native protocol imports
from omnibase_core.protocols import ProtocolLogger

# Create DI container
container = ModelONEXContainer(
    enable_performance_cache=True,
    enable_service_registry=True
)

# Resolve services by protocol
logger = container.get_service(ProtocolLogger)

# Use in node initialization
from omnibase_core.infrastructure.node_core_base import NodeCoreBase

class MyNode(NodeCoreBase):
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)  # ✅ Correct usage

        # Resolve dependencies
        self.logger = container.get_service(ProtocolLogger)
```

**Key Characteristics**:
- Provides service resolution via `get_service()`
- Manages service lifecycle and caching
- Integrates with workflow orchestration
- Performance monitoring and metrics
- **Always used in node constructors**
- **Used for dependency injection**

---

## Side-by-Side Comparison

| Feature | ModelContainer[T] | ModelONEXContainer |
|---------|-------------------|-------------------|
| **Purpose** | Value wrapper | Dependency injection |
| **Type Parameter** | `Generic[T]` | N/A |
| **Base Class** | `BaseModel` | Plain class |
| **Primary Method** | `map_value()`, `validate_with()` | `get_service()` |
| **Use in Nodes** | ❌ Never in `__init__` | ✅ Always in `__init__` |
| **Service Resolution** | ❌ No | ✅ Yes |
| **Metadata Tracking** | ✅ Yes (source, validation) | ✅ Yes (metrics, performance) |
| **Lifecycle Management** | ❌ No | ✅ Yes |
| **Caching** | ❌ No | ✅ Yes (service cache) |

---

## Common Mistakes

### ❌ WRONG: Using ModelContainer in Node Constructor

```
from omnibase_core.models.core.model_container import ModelContainer

class MyNode(NodeCoreBase):
    def __init__(self, container: ModelContainer):  # ❌ WRONG!
        super().__init__(container)  # Will fail!
```

**Problem**: `ModelContainer` is a value wrapper, not a DI container. It doesn't have `get_service()` method.

**Error**: `AttributeError: 'ModelContainer' object has no attribute 'get_service'`

### ✅ CORRECT: Using ModelONEXContainer in Node Constructor

```
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class MyNode(NodeCoreBase):
    def __init__(self, container: ModelONEXContainer):  # ✅ Correct!
        super().__init__(container)
```

---

### ❌ WRONG: Using ModelONEXContainer as Value Wrapper

```
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

# Trying to wrap a value
container = ModelONEXContainer()
container.value = "my_data"  # ❌ WRONG!
```

**Problem**: `ModelONEXContainer` is for dependency injection, not value wrapping.

**Better**: Use `ModelContainer[T]` for value wrapping.

### ✅ CORRECT: Using ModelContainer for Value Wrapping

```
from omnibase_core.models.core.model_container import ModelContainer

# Wrap a value with metadata
wrapped_value = ModelContainer.create(
    value="my_data",
    container_type="config",
    source="user_input"
)
```

---

## Decision Tree: Which Container to Use?

```
Are you writing a node class?
├─ Yes → Use ModelONEXContainer in __init__
│         def __init__(self, container: ModelONEXContainer)
│
└─ No → Are you wrapping a value with metadata?
        ├─ Yes → Use ModelContainer[T]
        │         ModelContainer.create(value=..., container_type=...)
        │
        └─ No → Are you resolving services?
                ├─ Yes → Use ModelONEXContainer
                │         container.get_service(ProtocolLogger)
                │
                └─ No → You probably don't need either container type
```

---

## Protocol Compliance (omnibase_core.protocols)

> **Note (v0.3.6+)**: Protocol definitions are now Core-native in `omnibase_core.protocols`.

### ModelContainer[T] Protocol Implementations

`ModelContainer` implements these Core-native protocols:
- `ProtocolConfigurable` - Configuration management
- `ProtocolSerializable` - Data serialization
- `ProtocolValidatable` - Validation interface
- `ProtocolNameable` - Name management

### ModelONEXContainer Protocol Implementations

`ModelONEXContainer` implements:
- `ProtocolServiceResolver` - Service resolution
- `ProtocolLifecycleManager` - Lifecycle management
- `ProtocolServiceRegistry` - Service registration

---

## Real-World Examples

### Example 1: Node Implementation (Use ModelONEXContainer)

```
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
# v0.3.6+: Core-native protocol imports
from omnibase_core.protocols import ProtocolLogger, ProtocolEventBus

class NodeDataProcessor(NodeCoreBase):
    """Example node showing correct container usage."""

    def __init__(self, container: ModelONEXContainer):  # ✅ Correct
        super().__init__(container)

        # Resolve dependencies
        self.logger = container.get_service(ProtocolLogger)
        self.event_bus = container.get_service(ProtocolEventBus)

    async def process(self, input_data: Any) -> Any:
        self.logger.info("Processing data")
        # Process data...
        return result
```

### Example 2: Configuration Value (Use ModelContainer[T])

```
from omnibase_core.models.core.model_container import ModelContainer

class ConfigManager:
    """Example showing value container usage."""

    def load_config(self, key: str) -> ModelContainer[str]:  # ✅ Correct
        """Load configuration value with metadata."""
        value = os.getenv(key, "default")

        return ModelContainer.create(
            value=value,
            container_type="environment_variable",
            source=f"env:{key}",
            is_validated=True,
            validation_notes="Loaded from environment"
        )

    def validate_config(self, config: ModelContainer[str]) -> bool:
        """Validate configuration value."""
        return config.validate_with(
            validator=lambda x: len(x) > 0,
            error_message="Config value cannot be empty"
        )
```

### Example 3: Service Factory (Use ModelONEXContainer)

```
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

async def create_service_layer(
    container: ModelONEXContainer  # ✅ Correct
) -> dict[str, Any]:
    """Create service layer with dependency injection."""

    # Resolve all services from container
    logger = container.get_service(ProtocolLogger)
    event_bus = container.get_service(ProtocolEventBus)

    return {
        "logger": logger,
        "event_bus": event_bus,
        "container": container  # Pass container for further resolution
    }
```

---

## Migration Guide

### If You're Using ModelContainer Instead of ModelONEXContainer

**Symptom**: Node initialization fails with `AttributeError: 'ModelContainer' object has no attribute 'get_service'`

**Fix**:
```
# Before (❌ Wrong)
from omnibase_core.models.core.model_container import ModelContainer

class MyNode(NodeCoreBase):
    def __init__(self, container: ModelContainer):  # ❌
        super().__init__(container)

# After (✅ Correct)
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class MyNode(NodeCoreBase):
    def __init__(self, container: ModelONEXContainer):  # ✅
        super().__init__(container)
```

---

## Type Hints and IDE Support

### Correct Type Hints

```
from typing import TypeVar
from omnibase_core.models.core.model_container import ModelContainer
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

T = TypeVar("T")

# Value container type hint
def process_value(value_container: ModelContainer[str]) -> str:
    return value_container.get_value()

# DI container type hint
def create_node(di_container: ModelONEXContainer) -> NodeCoreBase:
    return MyNode(di_container)
```

### mypy Strict Compliance

Both container types are fully compatible with `mypy --strict`:
- All methods have type annotations
- No `Any` types in public APIs (except where required by protocols)
- Full Pydantic validation support

---

## Testing Patterns

### Testing with ModelContainer[T]

```
def test_value_container():
    """Test value container functionality."""

    # Create container
    container = ModelContainer.create(
        value=42,
        container_type="test_value",
        source="test"
    )

    # Verify value
    assert container.get_value() == 42
    assert container.container_type == "test_value"

    # Transform value
    doubled = container.map_value(lambda x: x * 2)
    assert doubled.get_value() == 84
```

### Testing with ModelONEXContainer

```
async def test_service_resolution():
    """Test DI container functionality."""

    # Create DI container
    container = ModelONEXContainer()

    # Resolve service
    logger = container.get_service(ProtocolLogger)
    assert logger is not None

    # Create node with container
    node = MyNode(container)
    assert node.container is container
```

---

## Related Documentation

- [Dependency Injection Architecture](DEPENDENCY_INJECTION.md) - Full DI patterns
- [Models API Reference](../reference/api/models.md) - Complete model API
- [Node Building Guide](../guides/node-building/README.md) - Node construction patterns
- [Error Handling Best Practices](../conventions/ERROR_HANDLING_BEST_PRACTICES.md)

---

## Summary

**Remember**:
- `ModelContainer[T]` = **Value wrapper** with metadata
- `ModelONEXContainer` = **Dependency injection** container

**Rule of Thumb**:
- In node `__init__` → Always `ModelONEXContainer`
- For wrapping values → Always `ModelContainer[T]`
- For service resolution → Always `ModelONEXContainer`

**Never confuse the two!** They serve completely different purposes in the ONEX architecture.

---

**Version History**:
- **v0.4.0** (2025-12-13): Updated documentation metadata, refined examples
- v0.1.0 (2025-10-30) - Initial documentation created to clarify container type distinction
