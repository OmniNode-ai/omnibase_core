# Dependency Injection - omnibase_core

**Status**: ✅ Complete

## Overview

Protocol-driven dependency injection patterns using ModelONEXContainer.

## Core Concept

ONEX uses **protocol-based service resolution** instead of concrete class dependencies:

```
# ❌ Wrong: Concrete dependency
from my_logger import ConcreteLogger
logger = ConcreteLogger()

# ✅ Right: Protocol-based resolution
logger = container.get_service("ProtocolLogger")
```

## Container Architecture

### ModelONEXContainer

```
class ModelONEXContainer(BaseModel):
    """Protocol-driven dependency injection container."""

    def get_service(self, protocol_name: str) -> Any:
        """Resolve service by protocol name."""
        pass

    def register_service(self, protocol_name: str, implementation: Any):
        """Register service implementation."""
        pass
```

## Service Registration

### Register Services

```
container = ModelONEXContainer()

# Register concrete implementations
container.register_service("ProtocolLogger", my_logger_instance)
container.register_service("ProtocolEventBus", event_bus_instance)
container.register_service("ProtocolCache", cache_instance)
```

### Service Resolution

```
class MyNode(ModelServiceCompute):
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)

        # Resolve dependencies by protocol
        self.logger = container.get_service("ProtocolLogger")
        self.cache = container.get_service("ProtocolCache")
```

## Protocol Definitions

Protocols define interfaces without implementation:

```
from typing import Protocol

class ProtocolLogger(Protocol):
    def info(self, message: str) -> None: ...
    def error(self, message: str, exc_info: bool = False) -> None: ...
```

## Benefits

1. **Loose Coupling**: Depend on interfaces, not implementations
2. **Testability**: Easy to mock dependencies
3. **Flexibility**: Swap implementations without changing code
4. **Type Safety**: Full mypy compliance with protocols

## Testing Patterns

### Mock Dependencies

```
class MockLogger:
    def info(self, message: str) -> None:
        print(f"MOCK: {message}")

    def error(self, message: str, exc_info: bool = False) -> None:
        print(f"MOCK ERROR: {message}")

# Use in tests
test_container = ModelONEXContainer()
test_container.register_service("ProtocolLogger", MockLogger())
```

## Common Protocols

- `ProtocolLogger` - Logging
- `ProtocolEventBus` - Event publishing
- `ProtocolCache` - Caching
- `ProtocolDatabase` - Database access
- `ProtocolMetrics` - Metrics collection

## Next Steps

- [Container Implementation](../../src/omnibase_core/models/container/model_onex_container.py)
- Protocol Definitions: See omnibase_spi repository (if available)
- [Node Building Guide](../guides/node-building/README.md)

---

**Related Documentation**:
- [Architecture Overview](OVERVIEW.md)
- [Type System](TYPE_SYSTEM.md)
- [Testing Guide](../guides/TESTING_GUIDE.md)
