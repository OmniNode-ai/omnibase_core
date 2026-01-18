> **Navigation**: [Home](../INDEX.md) > Guides > ISP Protocol Migration Guide

# ISP Protocol Migration Guide

> **Version**: 0.4.0
> **Last Updated**: 2025-12-25
> **Related**: [CLAUDE.md](../../CLAUDE.md), [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)

---

## Overview

This guide explains the Interface Segregation Principle (ISP) split of `ProtocolEventBus` into minimal, focused protocols. This change allows components to depend only on the capabilities they actually need.

---

## Why ISP Matters

### The Interface Segregation Principle

The Interface Segregation Principle (ISP) states:

> **"Clients should not be forced to depend on interfaces they do not use."**

In practice, this means:
- A component that only publishes events should not need lifecycle management methods
- A component that only subscribes should not need publishing methods
- A health check service should not need to understand event serialization

### The Problem: Monolithic Interface

Before v0.4.0, `ProtocolEventBus` was a monolithic interface with 10+ methods:

```python
class ProtocolEventBus(Protocol):
    # Publishing methods
    async def publish(self, topic: str, key: bytes | None, value: bytes, ...) -> None: ...
    async def publish_envelope(self, envelope: ..., topic: str) -> None: ...
    async def broadcast_to_environment(self, command: str, ...) -> None: ...
    async def send_to_group(self, command: str, ...) -> None: ...

    # Subscription methods
    async def subscribe(self, topic: str, group_id: str, ...) -> Callable[...]: ...
    async def start_consuming(self) -> None: ...

    # Lifecycle methods
    async def start(self) -> None: ...
    async def shutdown(self) -> None: ...
    async def close(self) -> None: ...
    async def health_check(self) -> dict[str, object]: ...
```

**Problems with this approach**:

1. **Unnecessary dependencies**: A publish-only node depends on subscribe methods it never uses
2. **Testing complexity**: Mocks must implement all 10+ methods even for simple tests
3. **Coupling**: Changes to any method affect all consumers
4. **Violation of SRP**: The interface has multiple reasons to change

### The Solution: Focused Protocols

v0.4.0 splits `ProtocolEventBus` into three minimal protocols:

| Protocol | Methods | Purpose |
|----------|---------|---------|
| `ProtocolEventBusPublisher` | `publish`, `publish_envelope`, `broadcast_to_environment`, `send_to_group` | Event publishing |
| `ProtocolEventBusSubscriber` | `subscribe`, `start_consuming` | Event subscription |
| `ProtocolEventBusLifecycle` | `start`, `shutdown`, `close`, `health_check` | Lifecycle management |

The full `ProtocolEventBus` inherits from all three for backwards compatibility.

---

## The ProtocolEventBus Split

### Protocol Hierarchy

```text
                    ProtocolEventBus
                    (full interface)
                          |
         +----------------+----------------+
         |                |                |
ProtocolEventBus    ProtocolEventBus   ProtocolEventBus
   Publisher          Subscriber          Lifecycle
```

### Import Paths

```python
# ISP-compliant imports (prefer these)
from omnibase_core.protocols.event_bus import ProtocolEventBusPublisher
from omnibase_core.protocols.event_bus import ProtocolEventBusSubscriber
from omnibase_core.protocols.event_bus import ProtocolEventBusLifecycle

# Full interface (backwards compatible)
from omnibase_core.protocols.event_bus import ProtocolEventBus
```

### Protocol Details

#### ProtocolEventBusPublisher

Minimal interface for components that only publish events.

```python
@runtime_checkable
class ProtocolEventBusPublisher(Protocol):
    async def publish(
        self,
        topic: str,
        key: bytes | None,
        value: bytes,
        headers: ProtocolEventBusHeaders | None = None,
    ) -> None: ...

    async def publish_envelope(
        self,
        envelope: ProtocolEventEnvelope[object],
        topic: str,
    ) -> None: ...

    async def broadcast_to_environment(
        self,
        command: str,
        payload: dict[str, ContextValue],
        target_environment: str | None = None,
    ) -> None: ...

    async def send_to_group(
        self,
        command: str,
        payload: dict[str, ContextValue],
        target_group: str,
    ) -> None: ...
```

**Use Cases**:
- Effect nodes emitting results to downstream consumers
- Services that fire-and-forget events
- Nodes that produce events but never consume them

#### ProtocolEventBusSubscriber

Minimal interface for components that only consume events.

```python
@runtime_checkable
class ProtocolEventBusSubscriber(Protocol):
    async def subscribe(
        self,
        topic: str,
        group_id: str,
        on_message: Callable[[ProtocolEventMessage], Awaitable[None]],
    ) -> Callable[[], Awaitable[None]]: ...

    async def start_consuming(self) -> None: ...
```

**Use Cases**:
- Reducer nodes aggregating events from multiple sources
- Event handlers that only listen for specific event types
- Background workers processing event streams

#### ProtocolEventBusLifecycle

Minimal interface for lifecycle management.

```python
@runtime_checkable
class ProtocolEventBusLifecycle(Protocol):
    async def start(self) -> None: ...
    async def shutdown(self) -> None: ...
    async def close(self) -> None: ...
    async def health_check(self) -> dict[str, object]: ...
```

**Use Cases**:
- Application bootstrap/shutdown handlers
- Health check services
- Container lifecycle managers
- Graceful shutdown coordinators

---

## Migration Guide

### Before (Monolithic)

```python
from omnibase_core.protocols.event_bus import ProtocolEventBus

class MyPublisher:
    """A simple publisher that only emits events."""

    def __init__(self, bus: ProtocolEventBus):  # Depends on full interface
        self.bus = bus

    async def emit_event(self, data: bytes) -> None:
        # Only uses publish, but depends on 10+ methods
        await self.bus.publish("my.topic", None, data)
```

### After (ISP-Compliant)

```python
from omnibase_core.protocols.event_bus import ProtocolEventBusPublisher

class MyPublisher:
    """A simple publisher that only emits events."""

    def __init__(self, publisher: ProtocolEventBusPublisher):  # Minimal dependency
        self.publisher = publisher

    async def emit_event(self, data: bytes) -> None:
        # Only depends on publishing methods
        await self.publisher.publish("my.topic", None, data)
```

---

## Common Migration Patterns

### Pattern 1: Publish-Only Components

**Before**:
```python
class EventEmitter:
    def __init__(self, bus: ProtocolEventBus):
        self.bus = bus

    async def emit(self, event: ModelEventEnvelope) -> None:
        await self.bus.publish_envelope(event, "events.v1")
```

**After**:
```python
class EventEmitter:
    def __init__(self, publisher: ProtocolEventBusPublisher):
        self.publisher = publisher

    async def emit(self, event: ModelEventEnvelope) -> None:
        await self.publisher.publish_envelope(event, "events.v1")
```

### Pattern 2: Subscribe-Only Components

**Before**:
```python
class EventHandler:
    def __init__(self, bus: ProtocolEventBus):
        self.bus = bus
        self._unsubscribe: Callable[[], Awaitable[None]] | None = None

    async def start(self) -> None:
        self._unsubscribe = await self.bus.subscribe(
            "events.v1", "my-handler", self._handle
        )

    async def stop(self) -> None:
        if self._unsubscribe:
            await self._unsubscribe()
```

**After**:
```python
class EventHandler:
    def __init__(self, subscriber: ProtocolEventBusSubscriber):
        self.subscriber = subscriber
        self._unsubscribe: Callable[[], Awaitable[None]] | None = None

    async def start(self) -> None:
        self._unsubscribe = await self.subscriber.subscribe(
            "events.v1", "my-handler", self._handle
        )

    async def stop(self) -> None:
        if self._unsubscribe:
            await self._unsubscribe()
```

### Pattern 3: Lifecycle Management Only

**Before**:
```python
class AppBootstrap:
    def __init__(self, bus: ProtocolEventBus):
        self.bus = bus

    async def startup(self) -> None:
        await self.bus.start()

    async def shutdown(self) -> None:
        await self.bus.shutdown()
        await self.bus.close()

    async def health_check(self) -> bool:
        health = await self.bus.health_check()
        return health.get("healthy", False)
```

**After**:
```python
class AppBootstrap:
    def __init__(self, lifecycle: ProtocolEventBusLifecycle):
        self.lifecycle = lifecycle

    async def startup(self) -> None:
        await self.lifecycle.start()

    async def shutdown(self) -> None:
        await self.lifecycle.shutdown()
        await self.lifecycle.close()

    async def health_check(self) -> bool:
        health = await self.lifecycle.health_check()
        return health.get("healthy", False)
```

### Pattern 4: Full Event Bus (Unchanged)

If your component needs publish, subscribe, AND lifecycle management, continue using `ProtocolEventBus`:

```python
class FullService:
    """Service that publishes, subscribes, and manages lifecycle."""

    def __init__(self, bus: ProtocolEventBus):  # Still valid
        self.bus = bus

    async def start(self) -> None:
        await self.bus.start()
        await self.bus.subscribe("input", "my-group", self._handle)

    async def _handle(self, msg: ProtocolEventMessage) -> None:
        await self.bus.publish("output", None, msg.value)

    async def stop(self) -> None:
        await self.bus.shutdown()
        await self.bus.close()
```

### Pattern 5: DI Container Registration

**Before**:
```python
# Register only full interface
container.register("ProtocolEventBus", event_bus_instance)
```

**After**:
```python
# Register all interfaces for maximum flexibility
event_bus = create_event_bus()
container.register("ProtocolEventBus", event_bus)
container.register("ProtocolEventBusPublisher", event_bus)
container.register("ProtocolEventBusSubscriber", event_bus)
container.register("ProtocolEventBusLifecycle", event_bus)
```

Components can now request exactly what they need:
```python
# Minimal publisher dependency
publisher = container.get_service("ProtocolEventBusPublisher")

# Minimal subscriber dependency
subscriber = container.get_service("ProtocolEventBusSubscriber")

# Full interface when needed
bus = container.get_service("ProtocolEventBus")
```

---

## Backwards Compatibility

### Existing Code Continues to Work

The split is **fully backwards compatible**. `ProtocolEventBus` now inherits from all three minimal protocols:

```python
@runtime_checkable
class ProtocolEventBus(
    ProtocolEventBusPublisher,
    ProtocolEventBusSubscriber,
    ProtocolEventBusLifecycle,
    Protocol,
):
    """Full event bus interface combining all capabilities."""
    ...
```

This means:
- Existing implementations of `ProtocolEventBus` automatically satisfy all three minimal protocols
- Existing code using `ProtocolEventBus` continues to work unchanged
- Migration can be done incrementally, one component at a time

### Type Compatibility

Due to Python's structural typing with `Protocol`:

```python
# Any ProtocolEventBus instance also satisfies minimal protocols
bus: ProtocolEventBus = create_event_bus()

# These all work - bus satisfies each protocol
publisher: ProtocolEventBusPublisher = bus  # OK
subscriber: ProtocolEventBusSubscriber = bus  # OK
lifecycle: ProtocolEventBusLifecycle = bus  # OK
```

---

## Testing

### Simplified Mocks

With ISP-compliant protocols, you only need to mock the methods you actually use:

**Before (full mock required)**:
```python
class MockEventBus:
    """Must implement all 10+ methods."""
    async def publish(self, ...): ...
    async def publish_envelope(self, ...): ...
    async def broadcast_to_environment(self, ...): ...
    async def send_to_group(self, ...): ...
    async def subscribe(self, ...): ...
    async def start_consuming(self): ...
    async def start(self): ...
    async def shutdown(self): ...
    async def close(self): ...
    async def health_check(self): ...
```

**After (minimal mock)**:
```python
class MockPublisher:
    """Only implement what you need."""
    def __init__(self):
        self.published: list[tuple[str, bytes]] = []

    async def publish(
        self,
        topic: str,
        key: bytes | None,
        value: bytes,
        headers: ProtocolEventBusHeaders | None = None,
    ) -> None:
        self.published.append((topic, value))

    async def publish_envelope(
        self,
        envelope: ProtocolEventEnvelope[object],
        topic: str,
    ) -> None:
        pass  # Mock implementation

    async def broadcast_to_environment(
        self,
        command: str,
        payload: dict[str, ContextValue],
        target_environment: str | None = None,
    ) -> None:
        pass  # Mock implementation

    async def send_to_group(
        self,
        command: str,
        payload: dict[str, ContextValue],
        target_group: str,
    ) -> None:
        pass  # Mock implementation
```

### Test Example

```python
import pytest
from omnibase_core.protocols.event_bus import ProtocolEventBusPublisher


class MockPublisher:
    """Minimal mock for testing publish-only components."""

    def __init__(self):
        self.published: list[tuple[str, bytes]] = []

    async def publish(
        self, topic: str, key: bytes | None, value: bytes, headers=None
    ) -> None:
        self.published.append((topic, value))

    async def publish_envelope(self, envelope, topic: str) -> None:
        pass

    async def broadcast_to_environment(
        self, command: str, payload, target_environment=None
    ) -> None:
        pass

    async def send_to_group(
        self, command: str, payload, target_group: str
    ) -> None:
        pass


@pytest.mark.asyncio
async def test_emitter_publishes_events():
    """Test that emitter correctly publishes events."""
    mock_publisher = MockPublisher()
    emitter = EventEmitter(mock_publisher)

    await emitter.emit(b"test-data")

    assert len(mock_publisher.published) == 1
    assert mock_publisher.published[0] == ("events.v1", b"test-data")
```

---

## Migration Checklist

### For Existing Codebases

- [ ] **Audit dependencies**: Identify which components use `ProtocolEventBus`
  ```bash
  poetry run grep -r "ProtocolEventBus" src/
  ```

- [ ] **Classify by usage**: For each component, determine:
  - Does it publish? -> Consider `ProtocolEventBusPublisher`
  - Does it subscribe? -> Consider `ProtocolEventBusSubscriber`
  - Does it manage lifecycle? -> Consider `ProtocolEventBusLifecycle`
  - Does it do multiple? -> Keep `ProtocolEventBus`

- [ ] **Update imports**: Change imports to minimal protocols where appropriate
  ```python
  # Before
  from omnibase_core.protocols.event_bus import ProtocolEventBus

  # After
  from omnibase_core.protocols.event_bus import ProtocolEventBusPublisher
  ```

- [ ] **Update type hints**: Change parameter types to minimal protocols
  ```python
  # Before
  def __init__(self, bus: ProtocolEventBus): ...

  # After
  def __init__(self, publisher: ProtocolEventBusPublisher): ...
  ```

- [ ] **Update DI registrations**: Register all protocol variations
  ```python
  container.register("ProtocolEventBusPublisher", event_bus)
  container.register("ProtocolEventBusSubscriber", event_bus)
  container.register("ProtocolEventBusLifecycle", event_bus)
  ```

- [ ] **Simplify mocks**: Update test mocks to only implement needed methods

- [ ] **Run tests**: Ensure all tests pass
  ```bash
  poetry run pytest tests/ -x
  ```

- [ ] **Type check**: Verify type compatibility
  ```bash
  poetry run mypy src/
  ```

---

## Summary

| Scenario | Use This Protocol |
|----------|-------------------|
| Component only publishes events | `ProtocolEventBusPublisher` |
| Component only subscribes to events | `ProtocolEventBusSubscriber` |
| Component only manages lifecycle | `ProtocolEventBusLifecycle` |
| Component needs multiple capabilities | `ProtocolEventBus` |
| Backwards compatibility required | `ProtocolEventBus` (unchanged) |

---

## Support

- **Questions**: See [CLAUDE.md](../../CLAUDE.md) for quick reference
- **Architecture**: See [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)
- **Protocol Discovery**: See [Protocol Discovery Guide](PROTOCOL_DISCOVERY_GUIDE.md)

---

**Last Updated**: 2025-12-25
**Version**: 0.4.0
