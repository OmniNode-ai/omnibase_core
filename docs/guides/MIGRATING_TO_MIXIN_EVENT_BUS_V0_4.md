> **Navigation**: [Home](../INDEX.md) > Guides > Migrating to MixinEventBus v0.4

# Migrating to MixinEventBus v0.4 and v1.0 Deprecation Guide

> **Version**: 0.4.0 | **Status**: Active | **Last Updated**: 2025-12-30

This guide documents the v1.0 deprecations planned for `MixinEventBus` and provides migration paths for each deprecated pattern. All deprecations are marked with `TODO(v1.0)` comments in the source code.

---

## Table of Contents

1. [Overview](#overview)
2. [Timeline](#timeline)
3. [Deprecation Categories](#deprecation-categories)
   - [Lazy Initialization Fallbacks](#1-lazy-initialization-fallbacks)
   - [Event Bus Protocol hasattr Checks](#2-event-bus-protocol-hasattr-checks)
   - [ProtocolFromEvent Fallback](#3-protocolfrom_event-fallback)
   - [Topic Validation Additions](#4-topic-validation-additions-feature)
4. [Migration Checklist](#migration-checklist)
5. [Code References](#code-references)

---

## Overview

`MixinEventBus` in v0.4.0 supports flexible binding patterns and legacy event bus implementations through fallback mechanisms. These fallbacks will be removed in v1.0 to:

1. **Enforce explicit binding**: Require `bind_*()` calls in `__init__` for predictable initialization
2. **Standardize event bus protocol**: Require all event bus implementations to conform to `ProtocolEventBus`
3. **Improve type safety**: Require `ProtocolFromEvent` conformance for input state classes
4. **Enable topic validation**: Add message-topic alignment validation for event publishing

---

## Timeline

| Version | Status | Description |
|---------|--------|-------------|
| **v0.4.0** | Current | Fallbacks supported with deprecation warnings in docs |
| **v0.5.0** | Planned | Runtime warnings emitted for deprecated patterns |
| **v1.0.0** | Planned | Fallbacks removed, strict protocol enforcement |

**Migration Window**: v0.4.0 through v0.5.x (recommended to migrate before v1.0)

---

## Deprecation Categories

### 1. Lazy Initialization Fallbacks

**What's Deprecated**: Automatic creation of runtime state and listener handles when accessed without explicit binding.

**Why It's Being Removed**:
- Lazy initialization masks missing `bind_*()` calls
- Makes debugging harder when bindings are forgotten
- Violates explicit-over-implicit design principles

**Source Locations**:
- `src/omnibase_core/mixins/mixin_event_bus.py`, property `_event_bus_runtime_state`
- `src/omnibase_core/mixins/mixin_event_bus.py`, property `_event_bus_listener_handle`

#### Before (v0.4.0 - Deprecated Pattern)

```python
class MyNode(MixinEventBus[MyInput, MyOutput]):
    def __init__(self, event_bus: ProtocolEventBus):
        # Missing: super().__init__() or explicit state initialization
        # Lazy initialization creates state on first access
        self.bind_event_bus(event_bus)

    def do_something(self):
        # Runtime state is lazily created here if not initialized
        node_name = self.get_node_name()  # Works due to fallback
```

#### After (v1.0 - Required Pattern)

```python
from omnibase_core.models.event_bus import ModelEventBusRuntimeState

class MyNode(MixinEventBus[MyInput, MyOutput]):
    def __init__(self, event_bus: ProtocolEventBus):
        # Explicit state initialization REQUIRED
        object.__setattr__(
            self,
            "_mixin_event_bus_state",
            ModelEventBusRuntimeState.create_unbound()
        )

        # Now bind event bus and other configuration
        self.bind_event_bus(event_bus)
        self.bind_node_name("MyNode")

    def do_something(self):
        # State was explicitly initialized - no fallback needed
        node_name = self.get_node_name()
```

#### Alternative: Use a Base Class

```python
class BaseEventBusNode(MixinEventBus[MyInput, MyOutput]):
    """Base class that handles state initialization."""

    def __init__(self):
        from omnibase_core.models.event_bus import ModelEventBusRuntimeState
        object.__setattr__(
            self,
            "_mixin_event_bus_state",
            ModelEventBusRuntimeState.create_unbound()
        )

class MyNode(BaseEventBusNode):
    def __init__(self, event_bus: ProtocolEventBus):
        super().__init__()  # Initialize state
        self.bind_event_bus(event_bus)
```

---

### 2. Event Bus Protocol hasattr Checks

**What's Deprecated**: Runtime `hasattr()` checks for event bus methods (`publish`, `publish_async`, `subscribe`, `unsubscribe`).

**Why It's Being Removed**:
- Event bus implementations should conform to `ProtocolEventBus`
- `hasattr` checks add runtime overhead
- Protocol-based type checking provides compile-time safety

**Source Locations** (search for `TODO(v1.0)` comments in the file):
- `src/omnibase_core/mixins/mixin_event_bus.py`, method `_get_event_bus`
- `src/omnibase_core/mixins/mixin_event_bus.py`, method `publish_event`
- `src/omnibase_core/mixins/mixin_event_bus.py`, method `publish_completion_event`
- `src/omnibase_core/mixins/mixin_event_bus.py`, method `apublish_completion_event`
- `src/omnibase_core/mixins/mixin_event_bus.py`, method `stop_event_listener`
- `src/omnibase_core/mixins/mixin_event_bus.py`, method `_event_listener_loop`

#### Before (v0.4.0 - Deprecated Pattern)

```python
# Legacy event bus with non-standard interface
class LegacyEventBus:
    def send(self, event):  # Non-standard method name
        """Publish event."""
        pass

    def add_listener(self, handler, pattern):  # Non-standard
        """Subscribe to events."""
        pass

# MixinEventBus uses hasattr to support this
bus = LegacyEventBus()
node.bind_event_bus(bus)  # Works but deprecated
```

#### After (v1.0 - Required Pattern)

```python
from omnibase_core.protocols.event_bus import ProtocolEventBus

class StandardEventBus(ProtocolEventBus):
    """Event bus conforming to ProtocolEventBus."""

    def publish(self, event: Any) -> None:
        """Synchronous publish - REQUIRED."""
        pass

    async def publish_async(self, envelope: ProtocolEventEnvelope) -> None:
        """Asynchronous publish - REQUIRED."""
        pass

    def subscribe(self, handler: Callable, event_type: str) -> Any:
        """Subscribe to events - REQUIRED."""
        pass

    def unsubscribe(self, subscription: Any) -> None:
        """Unsubscribe from events - REQUIRED."""
        pass

# Standard event bus - works in v1.0
bus = StandardEventBus()
node.bind_event_bus(bus)
```

#### ProtocolEventBus Required Methods (v1.0)

| Method | Signature | Purpose |
|--------|-----------|---------|
| `publish` | `(event: Any) -> None` | Synchronous event publishing |
| `publish_async` | `(envelope: ProtocolEventEnvelope) -> Awaitable[None]` | Asynchronous event publishing |
| `subscribe` | `(handler: Callable, event_type: str) -> Any` | Subscribe to event patterns |
| `unsubscribe` | `(subscription: Any) -> None` | Unsubscribe from events |

---

### 3. ProtocolFromEvent Fallback

**What's Deprecated**: `getattr()` fallback for `from_event` class method on input state classes.

**Why It's Being Removed**:
- Input state classes should implement `ProtocolFromEvent`
- Protocol-based checking provides type safety
- Removes need for runtime `getattr` calls

**Source Location**:
- `src/omnibase_core/mixins/mixin_event_bus.py`, method `_event_to_input_state`

#### Before (v0.4.0 - Deprecated Pattern)

```python
class MyInputState:
    """Input state without ProtocolFromEvent conformance."""

    def __init__(self, value: str):
        self.value = value

    @classmethod
    def from_event(cls, event: ModelOnexEvent) -> "MyInputState":
        # Has from_event but doesn't implement Protocol
        data = event.data.model_dump() if event.data else {}
        return cls(value=data.get("value", ""))

# Works via getattr fallback (deprecated)
class MyNode(MixinEventBus[MyInputState, MyOutput]):
    pass
```

#### After (v1.0 - Required Pattern)

```python
from omnibase_core.protocols import ProtocolFromEvent
from omnibase_core.models.core.model_onex_event import ModelOnexEvent

class MyInputState(ProtocolFromEvent):
    """Input state implementing ProtocolFromEvent."""

    def __init__(self, value: str):
        self.value = value

    @classmethod
    def from_event(cls, event: ModelOnexEvent) -> "MyInputState":
        # Conforms to ProtocolFromEvent signature
        data = event.data.model_dump() if event.data else {}
        return cls(value=data.get("value", ""))

# Works via Protocol check - v1.0 compatible
class MyNode(MixinEventBus[MyInputState, MyOutput]):
    pass
```

#### ProtocolFromEvent Definition

```python
from typing import Protocol, Any, runtime_checkable

@runtime_checkable
class ProtocolFromEvent(Protocol):
    """Protocol for classes supporting construction from ModelOnexEvent."""

    @classmethod
    def from_event(cls, event: Any) -> Any:
        """Construct an instance from a ModelOnexEvent."""
        ...
```

---

### 4. Topic Validation Additions (Feature)

**What's Being Added**: Message-topic alignment validation when publishing events.

**Why It's Being Added**:
- Ensures events are published to correct topic types
- Prevents misconfiguration (e.g., events on command topics)
- Provides runtime validation of event routing

**Source Locations** (future implementation points -- search for `TODO(v1.0)` in the file):
- `src/omnibase_core/mixins/mixin_event_bus.py`, method `publish_event`
- `src/omnibase_core/mixins/mixin_event_bus.py`, method `publish_completion_event`
- `src/omnibase_core/mixins/mixin_event_bus.py`, method `apublish_completion_event`

#### Current (v0.4.0)

Topic validation is not performed. Events can be published to any topic.

#### Future (v1.0)

```python
# MixinEventBus will validate topic alignment automatically
async def publish_event(self, event_type: str, payload: ModelOnexEvent | None = None):
    bus = self._require_event_bus()

    envelope = ModelEventEnvelope(payload=event)

    # NEW in v1.0: Validate topic alignment
    topic = self._get_topic_for_event_type(event_type)
    self._validate_topic_alignment(topic, envelope)

    await bus.publish_async(envelope)
```

**Topic Naming Convention** (per [MESSAGE_TOPIC_MAPPING.md](../architecture/MESSAGE_TOPIC_MAPPING.md)):
- Events: `*.events.*` (e.g., `dev.user.events.v1`)
- Commands: `*.commands.*` (e.g., `dev.user.commands.v1`)
- Intents: `*.intents.*` (e.g., `dev.payment.intents.v1`)

**Message Category Alignment**:

| Message Category | Topic Pattern | Example |
|-----------------|---------------|---------|
| `EVENT` | `*.events.*` | `dev.user.events.v1` |
| `COMMAND` | `*.commands.*` | `dev.user.commands.v1` |
| `INTENT` | `*.intents.*` | `dev.payment.intents.v1` |

---

## Migration Checklist

Use this checklist to ensure your code is ready for v1.0:

### Required Changes

- [ ] **Explicit State Initialization**: Call `ModelEventBusRuntimeState.create_unbound()` in `__init__`
- [ ] **Event Bus Protocol Conformance**: Ensure event bus implements all `ProtocolEventBus` methods
- [ ] **ProtocolFromEvent Implementation**: Add `ProtocolFromEvent` to input state class inheritance

### Recommended Changes

- [ ] **Use bind_*() in __init__**: Move all binding calls to constructor
- [ ] **Remove hasattr checks**: Don't rely on duck typing for event bus operations
- [ ] **Implement standard signatures**: Match `ProtocolEventBus` method signatures exactly

### Verification Steps

```bash
# Run type checker to find protocol violations
uv run mypy src/your_package/

# Run tests with deprecation warnings enabled
uv run pytest tests/ -W default::DeprecationWarning
```

---

## Code References

All `TODO(v1.0)` comments are located in:

**File**: `src/omnibase_core/mixins/mixin_event_bus.py`

| Location | Category | Description |
|----------|----------|-------------|
| `_event_bus_runtime_state` property | Lazy Init | Runtime state lazy initialization fallback |
| `_event_bus_listener_handle` property | Lazy Init | Listener handle lazy initialization fallback |
| `_get_event_bus` method | hasattr | Event bus binding hasattr fallbacks |
| `publish_event` method | hasattr | `publish_async` method check |
| `publish_event` method | Feature | Topic validation placeholder |
| `publish_completion_event` method | hasattr/Feature | `publish` method check and topic validation |
| `apublish_completion_event` method | hasattr | `publish_async` method check (async) |
| `apublish_completion_event` method | Feature | Topic validation placeholder (async) |
| `stop_event_listener` method | hasattr | `unsubscribe` method check |
| `_event_listener_loop` method | hasattr | `subscribe` method check |
| `_event_to_input_state` method | Fallback | `from_event` getattr fallback |

---

## Related Documentation

- [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)
- [Error Handling Best Practices](../conventions/ERROR_HANDLING_BEST_PRACTICES.md)
- [Threading Guide](THREADING.md)
- [Container Types](../architecture/CONTAINER_TYPES.md)

---

**Questions?** Open an issue on the omnibase_core repository or consult the [Documentation Index](../INDEX.md).
