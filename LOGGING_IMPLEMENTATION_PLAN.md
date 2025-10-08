# Logging Implementation Plan - omnibase_core

## Overview

Implement event-driven logging system for omnibase_core that follows ONEX architecture principles with a clean migration path from bootstrap to production.

## Architecture

### Phase 1: Bootstrap Event-Driven Logging (Current Sprint)

**Goal**: Minimal event-driven logging with in-memory event bus for bootstrap phase.

**Components**:
```
omnibase_core/
├── infrastructure/
│   └── event_bus_inmemory.py          # Simple in-memory event bus (from archived)
├── logging/
│   ├── emit.py                        # Event emission functions
│   ├── models/
│   │   └── model_log_entry.py         # Pydantic log entry model
│   └── subscribers/
│       └── stdout_subscriber.py       # Basic stdout log subscriber
└── models/events/
    └── model_log_event.py             # Log event Pydantic model
```

**Key Files to Restore from Archived**:
- `archived/src/omnibase_core/nodes/canary/utils/memory_event_bus.py` → `src/omnibase_core/infrastructure/event_bus_inmemory.py`
  - Simpler implementation (290 lines vs 730)
  - Circular buffer for memory safety
  - Pattern-based subscriptions
  - Adequate for bootstrap needs

**Implementation**:

1. **Event Bus** (restore from archived):
```python
# src/omnibase_core/infrastructure/event_bus_inmemory.py
class MemoryEventBus:
    """Simple in-memory event bus for bootstrap and testing."""
    # Restored from archived canary utils
    # ~290 lines, circular buffer, pattern subscriptions
```

2. **Log Entry Model**:
```python
# src/omnibase_core/models/events/model_log_entry.py
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from omnibase_core.enums.enum_log_level import EnumLogLevel

class ModelLogEntry(BaseModel):
    """Structured log entry for ONEX logging system."""
    level: EnumLogLevel
    message: str
    correlation_id: UUID | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    context: dict[str, Any] = Field(default_factory=dict)
    node_id: str | None = None
    module_name: str | None = None
    function_name: str | None = None
```

3. **Event Emission**:
```python
# src/omnibase_core/logging/emit.py
from uuid import UUID
from omnibase_core.infrastructure.event_bus_inmemory import MemoryEventBus
from omnibase_core.models.events.model_log_entry import ModelLogEntry
from omnibase_core.enums.enum_log_level import EnumLogLevel

_global_bus: MemoryEventBus | None = None

def get_log_bus() -> MemoryEventBus:
    """Get or create global logging event bus."""
    global _global_bus
    if _global_bus is None:
        _global_bus = MemoryEventBus(max_history_size=1000)
        # Attach default stdout subscriber
        from omnibase_core.logging.subscribers.stdout_subscriber import StdoutSubscriber
        subscriber = StdoutSubscriber()
        _global_bus.subscribe(subscriber.handle_event, pattern="LOG.*")
    return _global_bus

def emit_log_event(
    level: EnumLogLevel,
    message: str,
    correlation_id: UUID | None = None,
    **context
) -> None:
    """
    Emit log event to event bus.

    Subscribers (stdout, file, NodeLogger) handle actual output.
    Core layer stays pure - no I/O coupling.
    """
    log_entry = ModelLogEntry(
        level=level,
        message=message,
        correlation_id=correlation_id,
        context=context
    )

    bus = get_log_bus()
    bus.publish({
        "event_type": f"LOG.{level.value}",
        "payload": log_entry.model_dump(),
        "correlation_id": str(correlation_id) if correlation_id else None
    })

# Convenience functions
def log_debug(message: str, correlation_id: UUID | None = None, **context) -> None:
    emit_log_event(EnumLogLevel.DEBUG, message, correlation_id, **context)

def log_info(message: str, correlation_id: UUID | None = None, **context) -> None:
    emit_log_event(EnumLogLevel.INFO, message, correlation_id, **context)

def log_warning(message: str, correlation_id: UUID | None = None, **context) -> None:
    emit_log_event(EnumLogLevel.WARNING, message, correlation_id, **context)

def log_error(message: str, correlation_id: UUID | None = None, **context) -> None:
    emit_log_event(EnumLogLevel.ERROR, message, correlation_id, **context)
```

4. **Stdout Subscriber**:
```python
# src/omnibase_core/logging/subscribers/stdout_subscriber.py
import sys
from datetime import datetime

class StdoutSubscriber:
    """Simple stdout log subscriber for bootstrap phase."""

    def handle_event(self, event: dict) -> None:
        """Handle log event and print to stdout."""
        payload = event.get("payload", {})
        level = payload.get("level", "INFO")
        message = payload.get("message", "")
        correlation_id = payload.get("correlation_id", "")
        timestamp = payload.get("timestamp", datetime.now().isoformat())

        # Simple format: [timestamp] [level] [correlation_id] message
        correlation_str = f" [{correlation_id[:8]}]" if correlation_id else ""
        print(
            f"[{timestamp}] [{level}]{correlation_str} {message}",
            file=sys.stdout if level != "ERROR" else sys.stderr
        )
```

### Phase 2: Bridge Integration (When omninode_bridge is ready)

**Goal**: Replace stdout subscriber with NodeLogger from omninode_bridge.

**Changes**:
```python
# Simply swap subscriber when bridge is available
from omninode_bridge import get_service

bus = get_log_bus()
# Remove stdout subscriber
bus.unsubscribe(stdout_subscriber.handle_event, pattern="LOG.*")

# Add NodeLogger subscriber
node_logger = get_service("NodeLogger")
bus.subscribe(node_logger.handle_log_event, pattern="LOG.*")
```

**Benefits**:
- No changes to emit.py or calling code
- NodeLogger handles formatting (JSON, YAML, Markdown, etc.)
- NodeLogger handles output backends (stdout, file, cloud, etc.)
- Full omnibase_3 NodeLogger features available

### Phase 3: Production Architecture (Long-term)

**Goal**: Full ONEX logging with NodeLoggerEffect node.

**Architecture**:
```
[Any Node] → emit_log_event() → [Event Bus] → [NodeLoggerEffect]
                                            ↓
                                    [stdout/file/cloud/metrics]
```

**Features**:
- Multiple output formats (JSON, YAML, Markdown, CSV, Text)
- Multiple backends (stdout, file rotation, cloud logging)
- Log aggregation integration (Datadog, Sentry, etc.)
- Performance metrics and monitoring
- Security audit trails
- Query sanitization for PII protection

## Migration Strategy

### Current State (Delete)
- ❌ `src/omnibase_core/logging/bootstrap_logger.py` - Dead code, already deleted
- ❌ `src/omnibase_core/logging/structured.py` - Direct I/O coupling, wrong pattern

### Phase 1 Implementation (This Sprint)
1. Restore `MemoryEventBus` from archived → `infrastructure/event_bus_inmemory.py`
2. Create `ModelLogEntry` Pydantic model
3. Create `emit.py` with event emission functions
4. Create `StdoutSubscriber` for bootstrap output
5. Update existing logging calls to use new emission pattern
6. Add tests for event-driven logging

### Phase 2 Implementation (When bridge ready)
1. Import NodeLogger from omninode_bridge
2. Swap stdout subscriber for NodeLogger subscriber
3. No other code changes required

### Phase 3 Implementation (Production)
1. Create NodeLoggerEffect in omnibase_infra
2. Deploy as proper ONEX effect node
3. Configure output backends and formats
4. Integrate with observability stack

## Testing Strategy

### Unit Tests
```python
# tests/unit/logging/test_emit.py
def test_emit_log_event():
    """Test log event emission to event bus."""
    from omnibase_core.logging.emit import emit_log_event, get_log_bus
    from omnibase_core.enums.enum_log_level import EnumLogLevel

    bus = get_log_bus()
    events = []
    bus.subscribe(lambda e: events.append(e), pattern="LOG.*")

    emit_log_event(EnumLogLevel.INFO, "test message", user_id="123")

    assert len(events) == 1
    assert events[0]["event_type"] == "LOG.INFO"
    assert events[0]["payload"]["message"] == "test message"
    assert events[0]["payload"]["context"]["user_id"] == "123"

# tests/unit/logging/test_stdout_subscriber.py
def test_stdout_subscriber(capsys):
    """Test stdout subscriber output."""
    from omnibase_core.logging.subscribers.stdout_subscriber import StdoutSubscriber

    subscriber = StdoutSubscriber()
    subscriber.handle_event({
        "event_type": "LOG.INFO",
        "payload": {
            "level": "INFO",
            "message": "test message",
            "timestamp": "2025-01-15T10:00:00Z"
        }
    })

    captured = capsys.readouterr()
    assert "INFO" in captured.out
    assert "test message" in captured.out
```

### Integration Tests
```python
# tests/integration/logging/test_logging_integration.py
async def test_end_to_end_logging():
    """Test complete logging flow from emission to output."""
    from omnibase_core.logging.emit import log_info, get_log_bus

    bus = get_log_bus()
    received_events = []

    def capture_event(event):
        received_events.append(event)

    bus.subscribe(capture_event, pattern="LOG.*")

    log_info("integration test", user="test_user")

    assert len(received_events) == 1
    assert received_events[0]["payload"]["message"] == "integration test"
```

## Dependencies

### New Dependencies
- None! Uses only existing dependencies:
  - pydantic (already in pyproject.toml)
  - Standard library (datetime, uuid, logging)

### Files to Restore from Archived
- `archived/src/omnibase_core/nodes/canary/utils/memory_event_bus.py`

### Files to Delete
- `src/omnibase_core/logging/bootstrap_logger.py` ✅ Already deleted
- `src/omnibase_core/logging/structured.py` (to be replaced)

## Benefits

### Architectural
✅ **Event-Driven** - Correct ONEX pattern from day one
✅ **Testable** - Mock event bus, verify events emitted
✅ **Swappable** - Easy transition between subscribers
✅ **Decoupled** - Core layer has no I/O dependencies
✅ **Composable** - Multiple subscribers can coexist

### Practical
✅ **No New Dependencies** - Uses existing libraries
✅ **Simple Bootstrap** - Minimal code for Phase 1
✅ **Clear Migration Path** - Phases 2 and 3 well-defined
✅ **Compatible** - Works with existing event bus protocols from SPI

### Performance
✅ **Minimal Overhead** - Event emission is fast
✅ **Memory Safe** - Circular buffer prevents leaks
✅ **Async Ready** - Event bus supports async subscribers

## Acceptance Criteria

### Phase 1 Complete When:
- [ ] MemoryEventBus restored from archived
- [ ] ModelLogEntry Pydantic model created
- [ ] emit.py with event emission functions created
- [ ] StdoutSubscriber implemented
- [ ] Existing logging calls updated to use new pattern
- [ ] Unit tests passing (>90% coverage)
- [ ] Integration tests passing
- [ ] No direct I/O in core logging layer
- [ ] Documentation updated

### Success Metrics:
- All log events go through event bus
- No direct stdout/stderr writes in core layer
- Event history available for debugging
- Easy subscriber swap demonstrated in tests
- Performance: <1ms for log emission
- Memory: Circular buffer prevents leaks

## Timeline

**Estimated Effort**: 1-2 days

**Breakdown**:
- Restore MemoryEventBus: 1 hour
- Create models and emit layer: 2 hours
- Create stdout subscriber: 1 hour
- Update existing logging calls: 2 hours
- Write tests: 3 hours
- Documentation: 1 hour

## Related Documents

- `PROTOCOL_AUDIT_REPORT.md` - Protocol cleanup work
- `archived/CLAUDE.md` - Archived patterns reference
- Research on omnibase_3 logging (completed)
- Research on omnibase_infra logging (completed)

## Next Steps

1. Complete current protocol cleanup branch
2. Merge protocol cleanup to main
3. Create new branch for logging implementation
4. Implement Phase 1 logging
5. Add task to Archon for tracking
