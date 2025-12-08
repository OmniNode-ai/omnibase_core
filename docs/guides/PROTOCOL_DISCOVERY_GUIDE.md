# Protocol Discovery Guide

> **Version**: 0.4.0
> **Last Updated**: 2025-12-08
> **Related**: [CLAUDE.md](../../CLAUDE.md), [Node Building Guide](node-building/README.md)

---

## Table of Contents

1. [Overview](#overview)
2. [Protocol-Driven Development in ONEX](#protocol-driven-development-in-onex)
3. [Decision Tree: Choosing the Right Protocol](#decision-tree-choosing-the-right-protocol)
4. [Protocol Categories](#protocol-categories)
5. [Common Patterns](#common-patterns)
6. [Quick Reference Table](#quick-reference-table)
7. [Implementation Examples](#implementation-examples)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Overview

This guide helps developers discover and choose the appropriate protocols when building ONEX components. The protocol system in `omnibase_core` provides Core-native protocol definitions that establish contracts for components without external dependencies.

### Design Principles

All protocols in `omnibase_core` follow these principles:

- **Protocol-first**: Use `typing.Protocol` with `@runtime_checkable` for duck typing support
- **Minimal interfaces**: Only define what Core actually needs
- **Complete type hints**: Full mypy strict mode compliance
- **Literal types**: Use `Literal` types for enumerated values
- **Forward references**: Use forward references to avoid circular imports

### Module Organization

```
src/omnibase_core/protocols/
    base/           # Common type aliases and base protocols
    container/      # DI container and service registry protocols
    event_bus/      # Event-driven messaging protocols
    types/          # Behavioral type protocols (Configurable, Executable, etc.)
    schema/         # Schema loading protocols
    validation/     # Validation and compliance protocols
    core.py         # Core operation protocols (CanonicalSerializer)
```

---

## Protocol-Driven Development in ONEX

ONEX uses protocol-driven development to achieve loose coupling and high testability. Instead of depending on concrete implementations, components depend on protocol interfaces.

### Key Benefits

1. **Loose Coupling**: Components depend on interfaces, not implementations
2. **Testability**: Easy to mock protocols in unit tests
3. **Flexibility**: Swap implementations without changing consumers
4. **Type Safety**: Full mypy support with runtime checking
5. **Duck Typing**: Any object implementing the protocol works

### The Protocol Pattern

```python
from omnibase_core.protocols import ProtocolEventBus

# Depend on protocol, not implementation
class MyNode:
    def __init__(self, event_bus: ProtocolEventBus):
        self.event_bus = event_bus

    async def process(self):
        # Use protocol interface
        await self.event_bus.publish("topic", None, b"message")
```

### Runtime Checking

All protocols are `@runtime_checkable`, enabling duck typing:

```python
from omnibase_core.protocols import ProtocolConfigurable

def configure_if_possible(obj: object) -> None:
    if isinstance(obj, ProtocolConfigurable):
        obj.configure(setting="value")
```

---

## Decision Tree: Choosing the Right Protocol

Use this decision tree to find the right protocol category for your use case:

```
START: What do you need?
    |
    +-- Need to register/resolve services?
    |       |
    |       +-- YES --> Container Protocols (ProtocolServiceRegistry, etc.)
    |       |
    |       +-- NO --> Continue
    |
    +-- Need to publish/subscribe to events?
    |       |
    |       +-- YES --> Event Bus Protocols (ProtocolEventBus, etc.)
    |       |
    |       +-- NO --> Continue
    |
    +-- Need to validate data or compliance?
    |       |
    |       +-- YES --> Validation Protocols (ProtocolValidator, etc.)
    |       |
    |       +-- NO --> Continue
    |
    +-- Need to load YAML/JSON schemas?
    |       |
    |       +-- YES --> Schema Protocols (ProtocolSchemaLoader)
    |       |
    |       +-- NO --> Continue
    |
    +-- Need behavioral capabilities (configurable, executable, etc.)?
    |       |
    |       +-- YES --> Types Protocols (ProtocolConfigurable, etc.)
    |       |
    |       +-- NO --> Continue
    |
    +-- Need base type definitions (ContextValue, SemVer, etc.)?
            |
            +-- YES --> Base Protocols and Type Aliases
```

### Quick Category Selection

| Question | Protocol Category |
|----------|-------------------|
| "How do I inject dependencies?" | `container/` |
| "How do I send events between nodes?" | `event_bus/` |
| "How do I validate data/implementations?" | `validation/` |
| "How do I mark my class as configurable/executable?" | `types/` |
| "How do I load node metadata/schemas?" | `schema/` |
| "What type should I use for context values?" | `base/` |

---

## Protocol Categories

### 1. Base Protocols (`base/`)

**Purpose**: Common type aliases, literal types, and foundational protocols used across all other protocols.

**When to Use**:
- Defining method parameters that accept various value types
- Working with semantic versioning
- Using standardized literal values for status, levels, etc.

**Key Exports**:

| Export | Description |
|--------|-------------|
| `ContextValue` | Type alias for JSON-compatible values |
| `ProtocolSemVer` | Semantic versioning protocol |
| `ProtocolDateTime` | DateTime type alias |
| `ProtocolHasModelDump` | Protocol for Pydantic-like model dumps |
| `LiteralLogLevel` | Log levels: TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL, FATAL |
| `LiteralNodeType` | Node types: COMPUTE, EFFECT, REDUCER, ORCHESTRATOR |
| `LiteralHealthStatus` | Health statuses: healthy, degraded, unhealthy, etc. |
| `LiteralServiceLifecycle` | Lifecycles: singleton, transient, scoped, pooled, lazy, eager |
| `LiteralInjectionScope` | Scopes: request, session, thread, process, global, custom |
| `LiteralValidationLevel` | Levels: BASIC, STANDARD, COMPREHENSIVE, PARANOID |

**Example**:

```python
from omnibase_core.protocols.base import (
    ContextValue,
    LiteralLogLevel,
    LiteralHealthStatus,
)

def log_with_context(
    level: LiteralLogLevel,
    message: str,
    context: dict[str, ContextValue]
) -> None:
    """Log a message with structured context."""
    pass

def check_health() -> LiteralHealthStatus:
    """Check component health."""
    return "healthy"
```

---

### 2. Container Protocols (`container/`)

**Purpose**: Dependency injection, service registration, and lifecycle management.

**When to Use**:
- Building a service registry
- Implementing dependency injection containers
- Managing service lifecycles (singleton, transient, scoped)
- Resolving services by interface

**Key Exports**:

| Protocol | Description |
|----------|-------------|
| `ProtocolServiceRegistry` | Main DI container for registering/resolving services |
| `ProtocolServiceRegistration` | Individual service registration metadata |
| `ProtocolServiceFactory` | Factory for creating service instances |
| `ProtocolDependencyGraph` | Dependency graph for service relationships |
| `ProtocolInjectionContext` | Context for scoped injection |
| `ProtocolServiceValidator` | Validates service registrations |
| `ProtocolManagedServiceInstance` | Wrapper for managed service instances |

**Example**:

```python
from omnibase_core.protocols import ProtocolServiceRegistry
from omnibase_core.protocols.base import LiteralServiceLifecycle, LiteralInjectionScope

class MyServiceRegistry:
    """Custom service registry implementation."""

    async def register_service(
        self,
        interface: type[TInterface],
        implementation: type[TImplementation],
        lifecycle: LiteralServiceLifecycle,
        scope: LiteralInjectionScope,
        configuration: dict[str, ContextValue] | None = None,
    ) -> UUID:
        """Register a service implementation."""
        # Implementation here
        pass

    async def resolve_service(
        self,
        interface: type[TInterface],
        scope: LiteralInjectionScope | None = None,
        context: dict[str, ContextValue] | None = None,
    ) -> TInterface:
        """Resolve a service by interface."""
        # Implementation here
        pass
```

---

### 3. Event Bus Protocols (`event_bus/`)

**Purpose**: Event-driven messaging infrastructure for distributed communication.

**When to Use**:
- Publishing events between nodes
- Subscribing to event topics
- Broadcasting commands across environments
- Implementing Kafka-based messaging

**Key Exports**:

| Protocol | Description |
|----------|-------------|
| `ProtocolEventBus` | Main event bus for publish/subscribe |
| `ProtocolEventBusBase` | Base protocol for event bus implementations |
| `ProtocolSyncEventBus` | Synchronous event bus variant |
| `ProtocolAsyncEventBus` | Asynchronous event bus variant |
| `ProtocolEventMessage` | Event message structure |
| `ProtocolEventEnvelope` | Envelope wrapper for events |
| `ProtocolEventBusHeaders` | Headers for event metadata |
| `ProtocolKafkaEventBusAdapter` | Kafka-specific adapter |
| `ProtocolEventBusRegistry` | Registry for event bus instances |
| `ProtocolEventBusLogEmitter` | Log emission via event bus |

**Example**:

```python
from omnibase_core.protocols import ProtocolEventBus, ProtocolEventMessage
from collections.abc import Awaitable, Callable

class MyEventBus:
    """Custom event bus implementation."""

    async def publish(
        self,
        topic: str,
        key: bytes | None,
        value: bytes,
        headers: ProtocolEventBusHeaders | None = None,
    ) -> None:
        """Publish a message to a topic."""
        # Implementation here
        pass

    async def subscribe(
        self,
        topic: str,
        group_id: str,
        on_message: Callable[[ProtocolEventMessage], Awaitable[None]],
    ) -> Callable[[], Awaitable[None]]:
        """Subscribe to a topic, return unsubscribe function."""
        # Implementation here
        pass

    async def broadcast_to_environment(
        self,
        command: str,
        payload: dict[str, ContextValue],
        target_environment: str | None = None,
    ) -> None:
        """Broadcast a command to all nodes in an environment."""
        # Implementation here
        pass
```

---

### 4. Types Protocols (`types/`)

**Purpose**: Behavioral capabilities and type constraints for objects.

**When to Use**:
- Marking objects as configurable, executable, identifiable
- Providing metadata from objects
- Implementing workflow reducers
- Defining node metadata structures

**Key Exports**:

| Protocol | Description |
|----------|-------------|
| `ProtocolIdentifiable` | Objects with unique IDs |
| `ProtocolNameable` | Objects with names |
| `ProtocolConfigurable` | Objects that can be configured |
| `ProtocolExecutable` | Objects that can be executed |
| `ProtocolValidatable` | Objects that can be validated |
| `ProtocolSerializable` | Objects that can be serialized |
| `ProtocolMetadataProvider` | Objects that provide metadata |
| `ProtocolLogEmitter` | Objects that emit logs |
| `ProtocolNodeMetadata` | Node metadata structure |
| `ProtocolNodeMetadataBlock` | Complete node metadata block |
| `ProtocolAction` | Action definition for orchestrators |
| `ProtocolState` | State definition for reducers |
| `ProtocolWorkflowReducer` | Workflow reduction operations |
| `ProtocolServiceInstance` | Service instance representation |
| `ProtocolServiceMetadata` | Service metadata |

**Example**:

```python
from omnibase_core.protocols import (
    ProtocolConfigurable,
    ProtocolExecutable,
    ProtocolIdentifiable,
)
from omnibase_core.protocols.base import ContextValue
from typing import Literal
from uuid import UUID, uuid4

class MyService:
    """Service implementing multiple behavioral protocols."""

    # Required marker for ProtocolConfigurable
    __omnibase_configurable_marker__: Literal[True] = True

    # Required marker for ProtocolExecutable
    __omnibase_executable_marker__: Literal[True] = True

    # Required marker for ProtocolIdentifiable
    __omnibase_identifiable_marker__: Literal[True] = True

    def __init__(self):
        self._id = uuid4()
        self._config: dict[str, ContextValue] = {}

    @property
    def id(self) -> UUID:
        """Get the object's unique identifier."""
        return self._id

    def configure(self, **kwargs: ContextValue) -> None:
        """Apply configuration to the object."""
        self._config.update(kwargs)

    async def execute(self) -> object:
        """Execute the object and return a result."""
        return {"status": "completed", "config": self._config}
```

---

### 5. Schema Protocols (`schema/`)

**Purpose**: Loading and managing ONEX YAML metadata and JSON schemas.

**When to Use**:
- Loading node metadata from YAML files
- Loading JSON schema definitions
- Parsing ONEX contract files

**Key Exports**:

| Protocol | Description |
|----------|-------------|
| `ProtocolSchemaLoader` | Loads ONEX YAML and JSON schemas |
| `ProtocolSchemaModel` | Represents a loaded schema |

**Example**:

```python
from omnibase_core.protocols import ProtocolSchemaLoader, ProtocolSchemaModel
from omnibase_core.protocols.types import ProtocolNodeMetadataBlock

class MySchemaLoader:
    """Custom schema loader implementation."""

    async def load_onex_yaml(self, path: str) -> ProtocolNodeMetadataBlock:
        """Load an ONEX YAML metadata file."""
        # Implementation here
        pass

    async def load_json_schema(self, path: str) -> ProtocolSchemaModel:
        """Load a JSON schema file."""
        # Implementation here
        pass

    async def load_schema_for_node(
        self, node: ProtocolNodeMetadataBlock
    ) -> ProtocolSchemaModel:
        """Load the schema associated with a node."""
        # Implementation here
        pass
```

---

### 6. Validation Protocols (`validation/`)

**Purpose**: Data validation, protocol compliance, and ONEX standards enforcement.

**When to Use**:
- Validating protocol implementations
- Checking ONEX naming conventions
- Enforcing architectural compliance
- Generating validation reports

**Key Exports**:

| Protocol | Description |
|----------|-------------|
| `ProtocolValidator` | Validates implementations against protocols |
| `ProtocolValidationResult` | Result of a validation operation |
| `ProtocolValidationError` | Individual validation error |
| `ProtocolValidationDecorator` | Decorator for validation |
| `ProtocolComplianceValidator` | ONEX compliance validation |
| `ProtocolComplianceReport` | Compliance report structure |
| `ProtocolComplianceRule` | Custom compliance rule |
| `ProtocolComplianceViolation` | Compliance violation details |
| `ProtocolONEXStandards` | ONEX standard definitions |
| `ProtocolArchitectureCompliance` | Architecture compliance rules |
| `ProtocolQualityValidator` | Quality validation |

**Example**:

```python
from omnibase_core.protocols import (
    ProtocolValidator,
    ProtocolValidationResult,
)

class MyProtocolValidator:
    """Custom protocol validator implementation."""

    strict_mode: bool = True

    async def validate_implementation(
        self, implementation: T, protocol: type[P]
    ) -> ProtocolValidationResult:
        """Validate that an implementation conforms to a protocol."""
        result = MyValidationResult(
            is_valid=True,
            protocol_name=protocol.__name__,
            implementation_name=type(implementation).__name__,
            errors=[],
            warnings=[],
        )

        # Check for required methods
        for method_name in dir(protocol):
            if not method_name.startswith("_"):
                if not hasattr(implementation, method_name):
                    result.add_error(
                        error_type="missing_method",
                        message=f"Missing method: {method_name}",
                    )

        return result
```

---

### 7. Core Protocols (`core.py`)

**Purpose**: Core operations like canonical serialization.

**Key Exports**:

| Protocol | Description |
|----------|-------------|
| `ProtocolCanonicalSerializer` | Canonical serialization operations |

---

## Common Patterns

### Pattern 1: Protocol Composition

Combine multiple protocols for rich object capabilities:

```python
from omnibase_core.protocols import (
    ProtocolConfigurable,
    ProtocolExecutable,
    ProtocolMetadataProvider,
    ProtocolValidatable,
)
from typing import Literal

class MyConfigurableExecutableNode:
    """Node that is configurable, executable, and provides metadata."""

    __omnibase_configurable_marker__: Literal[True] = True
    __omnibase_executable_marker__: Literal[True] = True
    __omnibase_metadata_provider_marker__: Literal[True] = True

    def configure(self, **kwargs: ContextValue) -> None:
        """Apply configuration."""
        self._config = kwargs

    async def execute(self) -> object:
        """Execute the node."""
        return {"result": "success"}

    async def get_metadata(self) -> dict[str, str | int | bool | float]:
        """Get node metadata."""
        return {"name": "MyNode", "version": 1}

    async def get_validation_context(self) -> dict[str, ContextValue]:
        """Get context for validation."""
        return {"config": self._config}

    async def get_validation_id(self) -> UUID:
        """Get unique ID for validation."""
        return self._id
```

### Pattern 2: Container-Based Service Resolution

Use container protocols for dependency injection:

```python
from omnibase_core.protocols import ProtocolServiceRegistry, ProtocolEventBus

class MyNode:
    """Node that resolves dependencies from container."""

    def __init__(self, registry: ProtocolServiceRegistry):
        self.registry = registry

    async def initialize(self) -> None:
        """Initialize by resolving dependencies."""
        self.event_bus = await self.registry.resolve_service(ProtocolEventBus)
        self.logger = await self.registry.resolve_service(ProtocolLogger)

    async def process(self, data: dict) -> None:
        """Process data using resolved services."""
        await self.logger.info("Processing data")
        await self.event_bus.publish("data.processed", None, json.dumps(data).encode())
```

### Pattern 3: Event-Driven Communication

Use event bus protocols for decoupled messaging:

```python
from omnibase_core.protocols import ProtocolEventBus, ProtocolEventMessage

class MyEventHandler:
    """Handler that subscribes to and publishes events."""

    def __init__(self, event_bus: ProtocolEventBus):
        self.event_bus = event_bus

    async def start(self) -> None:
        """Start listening for events."""
        self._unsubscribe = await self.event_bus.subscribe(
            topic="input.events",
            group_id="my-handler-group",
            on_message=self._handle_message,
        )

    async def _handle_message(self, message: ProtocolEventMessage) -> None:
        """Handle incoming message."""
        # Process message
        result = await self._process(message)

        # Publish result
        await self.event_bus.publish(
            topic="output.events",
            key=message.key,
            value=json.dumps(result).encode(),
        )

    async def stop(self) -> None:
        """Stop listening."""
        if self._unsubscribe:
            await self._unsubscribe()
```

### Pattern 4: Validation Pipeline

Use validation protocols for comprehensive checking:

```python
from omnibase_core.protocols import (
    ProtocolComplianceValidator,
    ProtocolValidator,
    ProtocolValidationResult,
)

class MyValidationPipeline:
    """Pipeline for comprehensive validation."""

    def __init__(
        self,
        protocol_validator: ProtocolValidator,
        compliance_validator: ProtocolComplianceValidator,
    ):
        self.protocol_validator = protocol_validator
        self.compliance_validator = compliance_validator

    async def validate_node(
        self, node: object, protocol: type, file_path: str
    ) -> list[ProtocolValidationResult]:
        """Run full validation pipeline on a node."""
        results = []

        # Protocol validation
        protocol_result = await self.protocol_validator.validate_implementation(
            node, protocol
        )
        results.append(protocol_result)

        # Compliance validation
        compliance_report = await self.compliance_validator.validate_file_compliance(
            file_path
        )
        compliance_result = await self.compliance_validator.aggregate_compliance_results(
            [compliance_report]
        )
        results.append(compliance_result)

        return results
```

---

## Quick Reference Table

### All Protocols by Use Case

| Use Case | Protocol | Module |
|----------|----------|--------|
| **Dependency Injection** | | |
| Register services | `ProtocolServiceRegistry` | `container` |
| Create service instances | `ProtocolServiceFactory` | `container` |
| Track dependencies | `ProtocolDependencyGraph` | `container` |
| Scope injection | `ProtocolInjectionContext` | `container` |
| **Event Messaging** | | |
| Publish/subscribe | `ProtocolEventBus` | `event_bus` |
| Async messaging | `ProtocolAsyncEventBus` | `event_bus` |
| Sync messaging | `ProtocolSyncEventBus` | `event_bus` |
| Kafka integration | `ProtocolKafkaEventBusAdapter` | `event_bus` |
| Message structure | `ProtocolEventMessage` | `event_bus` |
| Event wrapping | `ProtocolEventEnvelope` | `event_bus` |
| **Behavioral Types** | | |
| Has unique ID | `ProtocolIdentifiable` | `types` |
| Has name | `ProtocolNameable` | `types` |
| Can be configured | `ProtocolConfigurable` | `types` |
| Can be executed | `ProtocolExecutable` | `types` |
| Can be validated | `ProtocolValidatable` | `types` |
| Can be serialized | `ProtocolSerializable` | `types` |
| Provides metadata | `ProtocolMetadataProvider` | `types` |
| Emits logs | `ProtocolLogEmitter` | `types` |
| **Validation** | | |
| Validate protocols | `ProtocolValidator` | `validation` |
| Validation results | `ProtocolValidationResult` | `validation` |
| ONEX compliance | `ProtocolComplianceValidator` | `validation` |
| Custom rules | `ProtocolComplianceRule` | `validation` |
| Quality checks | `ProtocolQualityValidator` | `validation` |
| **Schema Loading** | | |
| Load YAML/JSON | `ProtocolSchemaLoader` | `schema` |
| Schema representation | `ProtocolSchemaModel` | `schema` |
| **Base Types** | | |
| JSON-compatible values | `ContextValue` | `base` |
| Semantic versioning | `ProtocolSemVer` | `base` |
| Model serialization | `ProtocolHasModelDump` | `base` |

### Literal Types Quick Reference

| Literal Type | Values |
|--------------|--------|
| `LiteralLogLevel` | TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL, FATAL |
| `LiteralNodeType` | COMPUTE, EFFECT, REDUCER, ORCHESTRATOR |
| `LiteralHealthStatus` | healthy, degraded, unhealthy, critical, unknown, warning, unreachable, available, unavailable, initializing, disposing, error |
| `LiteralOperationStatus` | success, failed, in_progress, cancelled, pending |
| `LiteralServiceLifecycle` | singleton, transient, scoped, pooled, lazy, eager |
| `LiteralInjectionScope` | request, session, thread, process, global, custom |
| `LiteralValidationLevel` | BASIC, STANDARD, COMPREHENSIVE, PARANOID |
| `LiteralValidationMode` | strict, lenient, smoke, regression, integration |
| `LiteralValidationSeverity` | error, warning, info |
| `LiteralEventPriority` | low, normal, high, critical |

---

## Implementation Examples

### Example 1: Implementing ProtocolConfigurable

```python
from omnibase_core.protocols import ProtocolConfigurable
from omnibase_core.protocols.base import ContextValue
from typing import Literal

class ConfigurableProcessor:
    """A processor that can be configured at runtime."""

    __omnibase_configurable_marker__: Literal[True] = True

    def __init__(self):
        self._timeout_ms: int = 5000
        self._retry_count: int = 3
        self._debug_mode: bool = False

    def configure(self, **kwargs: ContextValue) -> None:
        """Apply configuration to the processor."""
        if "timeout_ms" in kwargs:
            self._timeout_ms = int(kwargs["timeout_ms"])
        if "retry_count" in kwargs:
            self._retry_count = int(kwargs["retry_count"])
        if "debug_mode" in kwargs:
            self._debug_mode = bool(kwargs["debug_mode"])

# Usage
processor = ConfigurableProcessor()
processor.configure(timeout_ms=10000, debug_mode=True)
```

### Example 2: Implementing ProtocolValidatable

```python
from omnibase_core.protocols import ProtocolValidatable
from omnibase_core.protocols.base import ContextValue
from uuid import UUID, uuid4

class ValidatableDocument:
    """A document that can be validated."""

    def __init__(self, content: str, author: str):
        self._id = uuid4()
        self._content = content
        self._author = author

    async def get_validation_context(self) -> dict[str, ContextValue]:
        """Get context for validation rules."""
        return {
            "content_length": len(self._content),
            "author": self._author,
            "has_content": bool(self._content.strip()),
        }

    async def get_validation_id(self) -> UUID:
        """Get unique identifier for validation reporting."""
        return self._id

# Usage with a validator
async def validate_document(
    doc: ProtocolValidatable,
    validator: ProtocolValidator
) -> ProtocolValidationResult:
    context = await doc.get_validation_context()
    doc_id = await doc.get_validation_id()
    # Perform validation using context
    return await validator.validate_implementation(doc, ProtocolValidatable)
```

### Example 3: Implementing a Complete Service

```python
from omnibase_core.protocols import (
    ProtocolConfigurable,
    ProtocolExecutable,
    ProtocolIdentifiable,
    ProtocolMetadataProvider,
    ProtocolSerializable,
)
from omnibase_core.protocols.base import ContextValue
from typing import Literal
from uuid import UUID, uuid4
import json

class CompleteService:
    """A service implementing multiple protocols."""

    # Protocol markers
    __omnibase_configurable_marker__: Literal[True] = True
    __omnibase_executable_marker__: Literal[True] = True
    __omnibase_identifiable_marker__: Literal[True] = True
    __omnibase_metadata_provider_marker__: Literal[True] = True
    __omnibase_serializable_marker__: Literal[True] = True

    def __init__(self, name: str):
        self._id = uuid4()
        self._name = name
        self._config: dict[str, ContextValue] = {}
        self._execution_count = 0

    # ProtocolIdentifiable
    @property
    def id(self) -> UUID:
        return self._id

    # ProtocolConfigurable
    def configure(self, **kwargs: ContextValue) -> None:
        self._config.update(kwargs)

    # ProtocolExecutable
    async def execute(self) -> object:
        self._execution_count += 1
        return {
            "id": str(self._id),
            "name": self._name,
            "execution_count": self._execution_count,
        }

    # ProtocolMetadataProvider
    async def get_metadata(self) -> dict[str, str | int | bool | float]:
        return {
            "name": self._name,
            "execution_count": self._execution_count,
            "configured": bool(self._config),
        }

    # ProtocolSerializable
    def serialize(self) -> bytes:
        return json.dumps({
            "id": str(self._id),
            "name": self._name,
            "config": self._config,
            "execution_count": self._execution_count,
        }).encode()

    @classmethod
    def deserialize(cls, data: bytes) -> "CompleteService":
        obj = json.loads(data.decode())
        service = cls(obj["name"])
        service._id = UUID(obj["id"])
        service._config = obj["config"]
        service._execution_count = obj["execution_count"]
        return service
```

---

## Best Practices

### 1. Use Protocol Imports from Top-Level

Always import protocols from `omnibase_core.protocols`:

```python
# Recommended
from omnibase_core.protocols import ProtocolEventBus, ProtocolServiceRegistry

# Also valid for specific categories
from omnibase_core.protocols.container import ProtocolServiceRegistry
from omnibase_core.protocols.event_bus import ProtocolEventBus
```

### 2. Add Protocol Markers

Include the sentinel marker for runtime type checking:

```python
class MyConfigurable:
    __omnibase_configurable_marker__: Literal[True] = True  # Required!

    def configure(self, **kwargs: ContextValue) -> None:
        pass
```

### 3. Use Literal Types for Type Safety

Prefer literal types over plain strings:

```python
from omnibase_core.protocols.base import LiteralHealthStatus

def set_health(status: LiteralHealthStatus) -> None:
    pass  # Type checker ensures valid values

set_health("healthy")    # OK
set_health("invalid")    # Type error!
```

### 4. Depend on Protocols, Not Implementations

```python
# Good: Depend on protocol
def process(event_bus: ProtocolEventBus) -> None:
    pass

# Avoid: Depend on concrete class
def process(event_bus: KafkaEventBus) -> None:
    pass
```

### 5. Use TYPE_CHECKING for Forward References

Avoid circular imports with TYPE_CHECKING:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.protocols.validation import ProtocolValidationResult

class MyValidator:
    async def validate(self) -> "ProtocolValidationResult":
        pass
```

---

## Troubleshooting

### Issue: "Protocol marker not found"

**Cause**: Missing sentinel marker attribute.

**Solution**: Add the marker to your class:

```python
class MyClass:
    __omnibase_configurable_marker__: Literal[True] = True  # Add this
```

### Issue: "isinstance check fails"

**Cause**: Protocol not `@runtime_checkable` or marker missing.

**Solution**: All omnibase_core protocols are runtime_checkable. Ensure your class has the required marker and methods.

### Issue: "Cannot resolve service"

**Cause**: Service not registered with correct interface.

**Solution**: Register using the protocol type:

```python
# Register with protocol interface
await registry.register_service(
    interface=ProtocolEventBus,  # Use protocol type
    implementation=MyEventBus,
    lifecycle="singleton",
    scope="global",
)

# Resolve by protocol
bus = await registry.resolve_service(ProtocolEventBus)
```

### Issue: "Circular import error"

**Cause**: Direct import of protocol in module body.

**Solution**: Use TYPE_CHECKING guard:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.protocols import ProtocolEventBus
```

---

## Additional Resources

- **CLAUDE.md**: [Project instructions and conventions](../../CLAUDE.md)
- **Node Building Guide**: [How to build ONEX nodes](node-building/README.md)
- **Threading Guide**: [Thread safety in ONEX](THREADING.md)
- **Migration Guide**: [Migrating to v0.4.0](MIGRATING_TO_DECLARATIVE_NODES.md)

---

**Last Updated**: 2025-12-08
**Version**: 0.4.0
**Maintainer**: ONEX Framework Team
