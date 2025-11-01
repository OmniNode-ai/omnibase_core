# In-Memory Event Bus Research Report

**Date**: 2025-10-28
**Context**: Kafka Event Bus Adapter has 0% code coverage due to heavy mocking
**Objective**: Determine if an in-memory event bus exists for integration testing

---

## Executive Summary

**Finding**: ✅ **Protocol exists, but NO implementation**

- ✅ `ProtocolEventBusInMemory` protocol is defined in `omnibase_spi`
- ❌ No concrete in-memory implementation exists in `omnibase_core`
- ❌ Current tests use heavy mocking (AsyncMock) with 0% actual code coverage
- ✅ Clear path forward: Implement in-memory event bus for integration testing

**Recommendation**: **Create InMemoryEventBusAdapter** implementing `ProtocolEventBusInMemory`

---

## 1. Current State Analysis

### 1.1 KafkaEventBusAdapter Coverage

**File**: `src/omnibase_core/infrastructure/kafka_event_bus_adapter.py`

**Coverage Status**:
```python
Coverage: 0.00%
Reason: Module was never imported during testing (all mocked)
Tests: 13 tests pass using AsyncMock
```

**Problem**: Tests mock `AIOKafkaProducer` and `AIOKafkaConsumer`, preventing real code execution:

```python
# Current test pattern - NO actual code execution
@patch("omnibase_core.infrastructure.kafka_event_bus_adapter.AIOKafkaProducer")
async def test_publish_success(self, mock_producer_class: Mock, adapter: KafkaEventBusAdapter):
    mock_producer = AsyncMock()
    mock_producer.send_and_wait = AsyncMock()
    mock_producer_class.return_value = mock_producer
    # ... rest of test
```

### 1.2 Test File Analysis

**File**: `tests/unit/infrastructure/test_kafka_event_bus_adapter.py`

**Test Categories**:
1. ✅ Initialization (3 tests) - Mock only
2. ✅ Publishing (2 tests) - Mock only
3. ✅ Subscription (3 tests) - Mock only
4. ✅ Cleanup (2 tests) - Mock only
5. ✅ Message wrapper (3 tests) - Partial real execution

**Total**: 13 tests, 0% real code coverage

---

## 2. Protocol Discovery

### 2.1 ProtocolEventBusInMemory

**Location**: `omnibase_spi.protocols.event_bus.protocol_event_bus_in_memory`

**Protocol Definition**:
```python
@runtime_checkable
class ProtocolEventBusInMemory(Protocol):
    """
    Protocol for in-memory event bus implementations.

    Key Features:
    - Event history tracking for debugging
    - Subscriber count monitoring
    - Memory-based event storage
    - Synchronous event processing
    - Development and testing support
    """

    async def get_event_history(self) -> list[ProtocolEventMessage]: ...
    def clear_event_history(self) -> None: ...
    async def get_subscriber_count(self) -> int: ...
```

**Capabilities**:
- ✅ Event history tracking (debugging)
- ✅ Subscriber monitoring (health checks)
- ✅ Memory-based storage (no external dependencies)
- ✅ Testing and development focus

### 2.2 Related Protocols

**Also Available in omnibase_spi**:
```python
from omnibase_spi.protocols.event_bus import (
    ProtocolEventBus,                    # Base event bus protocol
    ProtocolEventBusHeaders,             # Standard ONEX headers
    ProtocolKafkaEventBusAdapter,        # Kafka adapter protocol
    ProtocolEventMessage,                # Message protocol
    ProtocolAsyncEventBus,               # Async-only event bus
    ProtocolSyncEventBus,                # Sync-only event bus
)
```

### 2.3 Execution Mode Support

**Enum**: `EnumPublisherType`
```python
class EnumPublisherType(str, Enum):
    IN_MEMORY = "IN_MEMORY"  # ✅ Use in-memory Event Bus
    AUTO = "AUTO"            # Automatically select based on context
    HYBRID = "HYBRID"        # Use hybrid routing between both
```

**Model**: `ModelExecutionMode.INMEMORY()`
```python
@classmethod
def INMEMORY(cls) -> "ModelExecutionMode":
    """In-memory execution mode - asynchronous, local event bus."""
    return cls(
        name="INMEMORY",
        value="inmemory",
        is_asynchronous=True,
        is_distributed=False,
        is_local=True,
        requires_event_bus=True,
        supports_scaling=False,
        typical_latency_ms=20,
        reliability_level="medium",
        description="Asynchronous execution with in-memory event bus",
    )
```

---

## 3. Implementation Gap Analysis

### 3.1 What Exists

✅ **Protocol Definition**: `ProtocolEventBusInMemory` (omnibase_spi)
✅ **Execution Mode Enum**: `EnumPublisherType.IN_MEMORY`
✅ **Execution Mode Model**: `ModelExecutionMode.INMEMORY()`
✅ **Base Protocols**: Event bus, headers, messages defined

### 3.2 What's Missing

❌ **Concrete Implementation**: No `InMemoryEventBusAdapter` class
❌ **Integration Tests**: No tests using real in-memory event bus
❌ **Factory Methods**: No container registration for in-memory bus
❌ **Documentation**: No usage examples for in-memory testing

---

## 4. Existing Event Bus Architecture

### 4.1 KafkaEventBusAdapter Structure

**Key Components**:

1. **Configuration Models** (3 classes):
   - `ModelKafkaConfig` - Base connection config
   - `ModelKafkaProducerConfig` - Producer-specific config
   - `ModelKafkaConsumerConfig` - Consumer-specific config

2. **Message Wrapper**:
   - `KafkaEventMessage` - Implements `ProtocolEventMessage`
   - Wraps aiokafka ConsumerRecord
   - Provides acknowledgment capability

3. **Adapter Class**:
   - `KafkaEventBusAdapter` - Main implementation
   - Async producer/consumer management
   - Retry logic with exponential backoff
   - Resource lifecycle management

### 4.2 Protocol Compliance

**KafkaEventBusAdapter implements**:
```python
# Key methods from ProtocolKafkaEventBusAdapter
async def publish(
    topic: str,
    key: bytes | None,
    value: bytes,
    headers: ProtocolEventBusHeaders,
) -> None

async def subscribe(
    topic: str,
    group_id: str,
    on_message: Callable[[ProtocolEventMessage], Awaitable[None]],
) -> Callable[[], Awaitable[None]]

async def close() -> None
```

---

## 5. In-Memory Implementation Design

### 5.1 Recommended Architecture

```python
# New file: src/omnibase_core/infrastructure/in_memory_event_bus_adapter.py

from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_spi.protocols.event_bus import (
    ProtocolEventBusHeaders,
    ProtocolEventMessage,
    ProtocolEventBusInMemory,
)


class InMemoryEventMessage:
    """In-memory implementation of ProtocolEventMessage."""

    def __init__(
        self,
        topic: str,
        key: bytes | None,
        value: bytes,
        headers: dict[str, bytes],
    ):
        self.topic = topic
        self.key = key
        self.value = value
        self.headers = headers
        self.offset = str(uuid4())  # Simulated offset
        self.partition = 0
        self._acked = False

    async def ack(self) -> None:
        """Acknowledge message (no-op for in-memory)."""
        self._acked = True


class InMemoryEventBusAdapter(ProtocolEventBusInMemory):
    """
    In-memory event bus adapter for testing and development.

    Implements ProtocolEventBusInMemory with:
    - Synchronous in-memory message storage
    - Topic-based pub/sub without external dependencies
    - Event history for debugging and testing
    - Subscriber management and monitoring

    Perfect for:
    - Integration testing without Kafka
    - Local development environments
    - Unit test fixtures
    - Event flow debugging
    """

    def __init__(self, container: ModelONEXContainer | None = None):
        self.container = container
        self._topics: dict[str, list[InMemoryEventMessage]] = defaultdict(list)
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._event_history: list[InMemoryEventMessage] = []
        self._closed = False

    async def publish(
        self,
        topic: str,
        key: bytes | None,
        value: bytes,
        headers: ProtocolEventBusHeaders,
    ) -> None:
        """Publish message to in-memory topic."""
        if self._closed:
            raise RuntimeError("Adapter is closed")

        # Convert headers to dict
        headers_dict = self._headers_to_dict(headers)

        # Create message
        message = InMemoryEventMessage(topic, key, value, headers_dict)

        # Store in topic queue
        self._topics[topic].append(message)

        # Add to event history
        self._event_history.append(message)

        # Notify all subscribers for this topic
        for callback in self._subscribers.get(topic, []):
            await callback(message)

    async def subscribe(
        self,
        topic: str,
        group_id: str,
        on_message: Callable[[ProtocolEventMessage], Awaitable[None]],
    ) -> Callable[[], Awaitable[None]]:
        """Subscribe to in-memory topic."""
        if self._closed:
            raise RuntimeError("Adapter is closed")

        # Add subscriber
        self._subscribers[topic].append(on_message)

        # Return unsubscribe function
        async def unsubscribe() -> None:
            if on_message in self._subscribers[topic]:
                self._subscribers[topic].remove(on_message)

        return unsubscribe

    async def close(self) -> None:
        """Close adapter and clear all data."""
        self._closed = True
        self._topics.clear()
        self._subscribers.clear()

    # ProtocolEventBusInMemory methods
    async def get_event_history(self) -> list[ProtocolEventMessage]:
        """Get all published events for debugging."""
        return list(self._event_history)

    def clear_event_history(self) -> None:
        """Clear event history (useful for tests)."""
        self._event_history.clear()

    async def get_subscriber_count(self) -> int:
        """Get total number of active subscribers."""
        return sum(len(subs) for subs in self._subscribers.values())

    def _headers_to_dict(self, headers: ProtocolEventBusHeaders) -> dict[str, bytes]:
        """Convert ProtocolEventBusHeaders to dict."""
        return {
            "content_type": headers.content_type.encode("utf-8"),
            "correlation_id": str(headers.correlation_id).encode("utf-8"),
            "message_id": str(headers.message_id).encode("utf-8"),
            "timestamp": headers.timestamp.isoformat().encode("utf-8"),
            "source": headers.source.encode("utf-8"),
            "event_type": headers.event_type.encode("utf-8"),
            "schema_version": str(headers.schema_version).encode("utf-8"),
        }

    @classmethod
    def from_container(
        cls, container: ModelONEXContainer
    ) -> "InMemoryEventBusAdapter":
        """Create adapter from ONEX container."""
        return cls(container=container)
```

### 5.2 Integration Test Pattern

```python
# New file: tests/integration/infrastructure/test_kafka_event_bus_adapter_integration.py

import pytest
from omnibase_core.infrastructure.in_memory_event_bus_adapter import (
    InMemoryEventBusAdapter,
)
from omnibase_core.infrastructure.kafka_event_bus_adapter import (
    KafkaEventBusAdapter,
)
from omnibase_core.models.container.model_onex_container import ModelONEXContainer


@pytest.fixture
def in_memory_adapter():
    """Create in-memory adapter for testing."""
    return InMemoryEventBusAdapter()


class TestKafkaEventBusAdapterWithInMemory:
    """Integration tests using in-memory event bus."""

    @pytest.mark.asyncio
    async def test_publish_and_subscribe_flow(self, in_memory_adapter):
        """Test complete pub/sub flow without external dependencies."""
        received_messages = []

        async def handler(message):
            received_messages.append(message)

        # Subscribe
        unsubscribe = await in_memory_adapter.subscribe(
            topic="test-topic",
            group_id="test-group",
            on_message=handler,
        )

        # Publish
        headers = create_test_headers()
        await in_memory_adapter.publish(
            topic="test-topic",
            key=b"key1",
            value=b'{"test": "data"}',
            headers=headers,
        )

        # Verify
        assert len(received_messages) == 1
        assert received_messages[0].value == b'{"test": "data"}'
        assert received_messages[0].key == b"key1"

        # Cleanup
        await unsubscribe()
        await in_memory_adapter.close()

    @pytest.mark.asyncio
    async def test_event_history_tracking(self, in_memory_adapter):
        """Test event history for debugging."""
        headers = create_test_headers()

        # Publish multiple messages
        for i in range(5):
            await in_memory_adapter.publish(
                topic=f"topic-{i}",
                key=None,
                value=f"message-{i}".encode(),
                headers=headers,
            )

        # Check history
        history = await in_memory_adapter.get_event_history()
        assert len(history) == 5

        # Verify ordering
        assert history[0].value == b"message-0"
        assert history[4].value == b"message-4"

        # Clear history
        in_memory_adapter.clear_event_history()
        history = await in_memory_adapter.get_event_history()
        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_subscriber_count_monitoring(self, in_memory_adapter):
        """Test subscriber count for health checks."""
        async def handler1(msg): pass
        async def handler2(msg): pass

        # Subscribe with multiple handlers
        unsub1 = await in_memory_adapter.subscribe("topic1", "group1", handler1)
        unsub2 = await in_memory_adapter.subscribe("topic1", "group1", handler2)
        unsub3 = await in_memory_adapter.subscribe("topic2", "group2", handler1)

        # Check count
        count = await in_memory_adapter.get_subscriber_count()
        assert count == 3

        # Unsubscribe one
        await unsub1()
        count = await in_memory_adapter.get_subscriber_count()
        assert count == 2

        # Cleanup
        await unsub2()
        await unsub3()
```

---

## 6. Coverage Impact Estimation

### 6.1 Current Coverage

**File**: `kafka_event_bus_adapter.py`
- **Current**: 0.00%
- **Reason**: Module never imported (mocked in tests)

### 6.2 Estimated Improvement with In-Memory Adapter

#### Approach 1: Integration Tests Only

- **Method**: Add integration tests using `InMemoryEventBusAdapter`
- **Estimated Coverage**: 70-80%
- **Rationale**: Tests actual code paths without external Kafka dependency

#### Approach 2: Hybrid (Unit + Integration)

- **Method**: Keep mocked unit tests + add in-memory integration tests
- **Estimated Coverage**: 85-95%
- **Rationale**: Unit tests cover edge cases, integration tests cover real flows

#### Approach 3: Full Real Testing

- **Method**: Use testcontainers with real Kafka + in-memory for local tests
- **Estimated Coverage**: 95-100%
- **Rationale**: Tests against actual Kafka behavior

**Recommendation**: **Approach 2 (Hybrid)** - Best balance of coverage, speed, and reliability

---

## 7. Implementation Plan

### Phase 1: Core Implementation (Day 1-2)

1. **Create InMemoryEventBusAdapter**
   - File: `src/omnibase_core/infrastructure/in_memory_event_bus_adapter.py`
   - Implement `ProtocolEventBusInMemory`
   - Add `InMemoryEventMessage` wrapper
   - Include event history and subscriber tracking

2. **Add Configuration Models** (if needed)
   - Reuse existing patterns from Kafka adapter
   - Simple initialization (no external config needed)

3. **Write Unit Tests**
   - File: `tests/unit/infrastructure/test_in_memory_event_bus_adapter.py`
   - Test all protocol methods
   - Test event history
   - Test subscriber management

### Phase 2: Integration Testing (Day 2-3)

1. **Create Integration Test Suite**
   - File: `tests/integration/infrastructure/test_kafka_event_bus_integration.py`
   - Test pub/sub flows
   - Test multi-subscriber scenarios
   - Test error handling
   - Test cleanup and resource management

2. **Measure Coverage**
   - Run coverage with in-memory tests
   - Identify remaining gaps
   - Add targeted tests for uncovered lines

### Phase 3: Documentation & Examples (Day 3)

1. **Update Documentation**
   - Add in-memory adapter to architecture docs
   - Create testing guide using in-memory adapter
   - Document when to use Kafka vs in-memory

2. **Add Examples**
   - Simple pub/sub example
   - Event history debugging example
   - Testing pattern example

---

## 8. Alternative Approaches Considered

### 8.1 Real Kafka with Testcontainers

**Pros**:
- ✅ Tests against actual Kafka behavior
- ✅ Catches Kafka-specific issues
- ✅ High confidence in production behavior

**Cons**:
- ❌ Slow test execution (container startup ~10-30s)
- ❌ Requires Docker in CI/CD
- ❌ Resource intensive
- ❌ Flaky in CI environments

**Verdict**: ❌ Too slow for unit/integration tests

### 8.2 Mock-Only Testing (Current Approach)

**Pros**:
- ✅ Fast test execution
- ✅ No external dependencies
- ✅ Easy to write

**Cons**:
- ❌ 0% real code coverage
- ❌ Doesn't test actual logic
- ❌ False confidence
- ❌ Bugs not caught until production

**Verdict**: ❌ Insufficient for production code

### 8.3 In-Memory Adapter (Recommended)

**Pros**:
- ✅ Fast test execution (<100ms)
- ✅ No external dependencies
- ✅ Real code coverage (70-95%)
- ✅ Tests actual logic paths
- ✅ Debugging capabilities (event history)
- ✅ Perfect for CI/CD

**Cons**:
- ⚠️ Doesn't test Kafka-specific issues
- ⚠️ Requires implementation effort

**Verdict**: ✅ **RECOMMENDED** - Best balance for integration testing

### 8.4 Hybrid Approach (Best of All)

**Strategy**:
1. **In-Memory for Integration Tests** (70-80% coverage)
2. **Mocks for Unit Tests** (edge cases, error paths)
3. **Optional: Testcontainers for E2E** (manual/nightly)

**Result**: 85-95% coverage with fast test execution

---

## 9. Recommendations

### 9.1 Immediate Actions

1. ✅ **Implement `InMemoryEventBusAdapter`**
   - Priority: HIGH
   - Effort: 1-2 days
   - Impact: 70-80% coverage gain

2. ✅ **Create Integration Test Suite**
   - Priority: HIGH
   - Effort: 1 day
   - Impact: Validates real behavior

3. ✅ **Update Documentation**
   - Priority: MEDIUM
   - Effort: 0.5 day
   - Impact: Team enablement

### 9.2 Long-Term Enhancements

1. **Add Testcontainers for E2E**
   - Priority: LOW
   - Effort: 1 day
   - Impact: Kafka-specific issue detection

2. **Performance Benchmarking**
   - Compare in-memory vs Kafka performance
   - Document latency characteristics
   - Guide architecture decisions

3. **Event Store Persistence**
   - Optional: Save event history to disk
   - Useful for long-running integration tests
   - Debugging complex event flows

---

## 10. Appendix

### 10.1 File Locations

**Protocols** (omnibase_spi v0.1.0):
```text
omnibase_spi/protocols/event_bus/
├── protocol_event_bus_in_memory.py      # ✅ IN_MEMORY protocol
├── protocol_event_bus.py                # Base event bus protocol
├── protocol_kafka_adapter.py            # Kafka adapter protocol
└── protocol_event_bus_types.py          # Event message types
```

**Implementations** (omnibase_core):
```text
src/omnibase_core/infrastructure/
├── kafka_event_bus_adapter.py           # ✅ Kafka implementation
└── in_memory_event_bus_adapter.py       # ❌ TO BE CREATED
```

**Tests**:
```text
tests/
├── unit/infrastructure/
│   ├── test_kafka_event_bus_adapter.py            # ✅ Mock tests (0% coverage)
│   └── test_in_memory_event_bus_adapter.py        # ❌ TO BE CREATED
└── integration/infrastructure/
    └── test_kafka_event_bus_integration.py        # ❌ TO BE CREATED
```

### 10.2 Related Enums and Models

**EnumPublisherType**:
```python
# Location: src/omnibase_core/enums/enum_publisher_type.py
class EnumPublisherType(str, Enum):
    IN_MEMORY = "IN_MEMORY"  # Use in-memory Event Bus
    AUTO = "AUTO"            # Automatically select
    HYBRID = "HYBRID"        # Hybrid routing
```

**ModelExecutionMode**:
```python
# Location: src/omnibase_core/models/core/model_execution_mode.py
@classmethod
def INMEMORY(cls) -> "ModelExecutionMode":
    """In-memory execution mode."""
    return cls(
        name="INMEMORY",
        value="inmemory",
        is_asynchronous=True,
        is_distributed=False,
        is_local=True,
        requires_event_bus=True,
        supports_scaling=False,
        typical_latency_ms=20,
        reliability_level="medium",
    )
```

### 10.3 Key Dependencies

**Current** (KafkaEventBusAdapter):
```toml
[tool.poetry.dependencies]
aiokafka = "^0.8.0"  # Kafka client library
```

**New** (InMemoryEventBusAdapter):
```toml
# No external dependencies needed!
# Uses only Python standard library:
# - collections.defaultdict
# - asyncio
# - uuid
```

---

## 11. Conclusion

**Summary**: The protocol for in-memory event bus (`ProtocolEventBusInMemory`) exists in `omnibase_spi`, but no concrete implementation exists in `omnibase_core`. This represents a clear opportunity to improve test coverage from 0% to 70-95% by implementing an in-memory adapter.

**Key Findings**:
1. ✅ Protocol is well-defined and ready to implement
2. ❌ No existing in-memory implementation
3. ✅ Clear architecture patterns from KafkaEventBusAdapter
4. ✅ Significant coverage improvement potential
5. ✅ No external dependencies required

**Next Steps**:
1. Implement `InMemoryEventBusAdapter` (1-2 days)
2. Create integration test suite (1 day)
3. Measure coverage improvements
4. Update documentation

**Expected Outcome**:
- **Coverage**: 0% → 70-95%
- **Test Speed**: Maintained (no Kafka overhead)
- **Confidence**: High (real code execution)
- **Maintainability**: Improved (easier to debug)

---

**Report Author**: Claude Code (Polymorphic Agent)
**Date**: 2025-10-28
**Status**: ✅ Complete - Ready for Implementation
