# AsyncProtocolEventBus: Core vs SPI Comparison

**Date**: 2025-01-15

---

## 🔍 Protocol Signatures Comparison

### omnibase_core: AsyncProtocolEventBus

**Location**: `src/omnibase_core/mixin/mixin_event_bus.py:45`

```python
@runtime_checkable
class AsyncProtocolEventBus(Protocol):
    """Protocol for asynchronous event bus."""

    async def publish(self, event: OnexEvent) -> None: ...
    async def publish_event(self, event: OnexEvent) -> None: ...
```

**Methods**:
- `async publish(event: OnexEvent) -> None`
- `async publish_event(event: OnexEvent) -> None`

**Event Type**: `OnexEvent` (concrete Pydantic model from omnibase_core)

---

### omnibase_spi: ProtocolAsyncEventBus

**Location**: `src/omnibase_spi/protocols/event_bus/protocol_event_bus_mixin.py:54`

```python
@runtime_checkable
class ProtocolAsyncEventBus(ProtocolEventBusBase, Protocol):
    """Protocol for asynchronous event bus operations."""

    # Inherited from ProtocolEventBusBase:
    async def publish(self, event: ProtocolEventMessage) -> None: ...

    # Own method:
    async def publish_async(self, event: ProtocolEventMessage) -> None: ...
```

**Methods**:
- `async publish(event: ProtocolEventMessage) -> None` (inherited)
- `async publish_async(event: ProtocolEventMessage) -> None`

**Event Type**: `ProtocolEventMessage` (protocol from omnibase_spi)

---

## 📊 Key Differences

### 1. Method Names
| omnibase_core | omnibase_spi |
|---------------|--------------|
| `publish()` | `publish()` ✅ Same |
| `publish_event()` | `publish_async()` ❌ Different |

### 2. Event Type
| omnibase_core | omnibase_spi |
|---------------|--------------|
| `OnexEvent` (concrete model) | `ProtocolEventMessage` (protocol) ❌ Different |

### 3. Inheritance
| omnibase_core | omnibase_spi |
|---------------|--------------|
| No base class | Extends `ProtocolEventBusBase` ✅ Better design |

---

## 🤔 Functionality Assessment

### Same Core Functionality? ✅ YES

**Both protocols define**:
- Async event publishing capability
- Primary method: `publish(event) -> None`
- Secondary method: `publish_event()` vs `publish_async()`

**Semantic equivalence**:
- `omnibase_core.publish_event()` ≈ `omnibase_spi.publish_async()`
- Both are async operations for publishing events
- Method name difference is cosmetic

### Type Compatibility? ⚠️ NEEDS INVESTIGATION

**Question**: Does `OnexEvent` implement `ProtocolEventMessage`?

Need to check if:
```python
isinstance(OnexEvent(...), ProtocolEventMessage)  # True or False?
```

---

## 🔬 Type Investigation Needed

### What is OnexEvent?

**Location**: `src/omnibase_core/models/core/model_onex_event.py`

**Expected structure** (need to verify):
```python
class OnexEvent(BaseModel):
    event_id: UUID
    event_type: str
    timestamp: datetime
    source: str
    payload: dict[str, Any]
    correlation_id: UUID
    metadata: dict[str, Any]
```

### What is ProtocolEventMessage?

**Location**: `src/omnibase_spi/protocols/types/protocol_event_bus_types.py:166`

**Structure** (from SPI):
```python
@runtime_checkable
class ProtocolEventMessage(Protocol):
    """Protocol for ONEX event bus message objects."""
    # Methods and attributes defined here
```

### What is ProtocolOnexEvent?

**Location**: `src/omnibase_spi/protocols/types/protocol_event_bus_types.py:104`

**Structure**:
```python
@runtime_checkable
class ProtocolOnexEvent(Protocol):
    """Protocol for ONEX system events."""
    event_id: UUID
    event_type: str
    timestamp: ProtocolDateTime
    source: str
    payload: dict[str, ProtocolEventData]
    correlation_id: UUID
    metadata: dict[str, ProtocolEventData]

    async def validate_onex_event(self) -> bool: ...
```

---

## 🎯 Critical Question

**Is `OnexEvent` (concrete model) compatible with `ProtocolOnexEvent` (protocol)?**

If YES:
- ✅ OnexEvent already implements the protocol interface
- ✅ We can use spi protocols directly
- ✅ Simple import swap, no code changes

If NO:
- ❌ OnexEvent needs to be updated to implement ProtocolOnexEvent
- ❌ May need adapter layer
- ❌ More complex migration

---

## 🔍 Next Steps

1. **Read `model_onex_event.py`** completely
2. **Check if OnexEvent has**:
   - All required fields from ProtocolOnexEvent
   - `validate_onex_event()` method
   - Compatible types (ProtocolDateTime, ProtocolEventData)

3. **Determine**:
   - Can we use OnexEvent with ProtocolEventMessage?
   - Do we need OnexEvent to extend/implement ProtocolOnexEvent?
   - Is there type alignment needed?

---

## 💡 Provisional Assessment

**Functionality**: ✅ **SAME** - Both provide async event bus publishing

**Type Compatibility**: ⚠️ **UNKNOWN** - Need to verify OnexEvent structure

**Recommendation**:
- **IF** OnexEvent implements ProtocolOnexEvent interface → **Delete core protocol, use SPI**
- **IF NOT** → **Update OnexEvent to implement ProtocolOnexEvent, then use SPI**

---

**Status**: AWAITING TYPE VERIFICATION
**Next Command**: Read model_onex_event.py fully
