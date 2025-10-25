# Testing Intent Publisher Pattern

**Status**: ✅ Production Ready
**Last Updated**: October 23, 2025
**Pattern**: MixinIntentPublisher Testing Guide

---

## Overview

This guide covers comprehensive testing strategies for nodes using `MixinIntentPublisher` - the coordination I/O capability that enables ONEX nodes to publish events while maintaining architectural purity.

### What is MixinIntentPublisher?

`MixinIntentPublisher` is a mixin that allows nodes (especially REDUCER and COMPUTE nodes) to coordinate event publishing without performing direct I/O. Instead of publishing events directly to Kafka, nodes publish "intents" to a coordination topic.

**Architecture**:
```
Node (pure logic) → publish_event_intent() → Kafka (intent topic)
    → IntentExecutor (future) → Kafka (domain topic)
```

**Key Benefits**:
- ✅ Maintains node purity (no direct I/O)
- ✅ Easy to test (no Kafka mocks required)
- ✅ Traceable coordination via intents
- ✅ Decoupled event production from publishing

---

## Test Fixtures

### Available Fixtures

The `tests/fixtures/fixture_intent_publisher.py` module provides fast test fixtures for intent publisher testing:

```python
from tests.fixtures.fixture_intent_publisher import (
    IntentPublisherFixtures,    # Intent event models
    IntentResultFixtures,        # Intent publish results
    MockKafkaClient,             # Test double for Kafka
    create_mock_kafka_client,    # Convenience factory
    create_test_event,           # Simple test event generator
)
```

### IntentPublisherFixtures

Create test intent models efficiently:

```python
# Create event publish intent
intent = IntentPublisherFixtures.event_publish_intent(
    target_topic="dev.test.metrics.v1",
    target_key="test-123",
    target_event_type="METRICS_RECORDED",
    target_event_payload={"metric": "value"},
    priority=5
)

# Create intent execution result
result = IntentPublisherFixtures.intent_execution_result(
    intent_id=intent.intent_id,
    success=True,
    execution_duration_ms=12.5
)
```

### MockKafkaClient

Mock Kafka client for testing intent publishing without real Kafka:

```python
# Create mock Kafka client
mock_kafka = MockKafkaClient()

# Use in container
container = create_test_container(kafka_client=mock_kafka)
node = MyNode(container)

# Publish intent
await node.publish_event_intent(
    target_topic="my.topic.v1",
    target_key="key-123",
    event=my_event
)

# Assert on captured messages
assert len(mock_kafka.published_messages) == 1
assert mock_kafka.published_messages[0]["topic"] == "dev.omninode-bridge.intents.event-publish.v1"

# Access specific messages
messages = mock_kafka.get_messages_for_topic("dev.omninode-bridge.intents.event-publish.v1")
assert len(messages) == 1
```

---

## Testing Patterns

### Pattern 1: Basic Intent Publishing

Test that node publishes intent with correct structure:

```python
import pytest
from uuid import uuid4
from tests.fixtures.fixture_intent_publisher import MockKafkaClient, create_test_event

@pytest.mark.asyncio
async def test_node_publishes_intent():
    """Test that node publishes intent after processing."""
    # Arrange
    mock_kafka = MockKafkaClient()
    container = create_test_container(kafka_client=mock_kafka)
    node = MyReducerNode(container)

    event = create_test_event("METRICS_RECORDED", metric_value=100)

    # Act
    result = await node.execute_reduction(event)

    # Assert - Check intent was published
    assert mock_kafka.get_message_count() == 1

    published = mock_kafka.published_messages[0]
    assert published["topic"] == "dev.omninode-bridge.intents.event-publish.v1"
    assert published["key"] is not None

    # Assert - Result is correct
    assert result.success is True
```

### Pattern 2: Intent Content Verification

Test that intent contains correct target and payload:

```python
import json
from omnibase_core.models.events.model_intent_events import TOPIC_EVENT_PUBLISH_INTENT

@pytest.mark.asyncio
async def test_intent_content_is_correct():
    """Test that published intent has correct target and payload."""
    # Arrange
    mock_kafka = MockKafkaClient()
    container = create_test_container(kafka_client=mock_kafka)
    node = MyReducerNode(container)

    test_data = {"metric_name": "processing_time", "value": 123.45}

    # Act
    await node.execute_reduction(test_data)

    # Assert
    messages = mock_kafka.get_messages_for_topic(TOPIC_EVENT_PUBLISH_INTENT)
    assert len(messages) == 1

    # Parse intent envelope
    intent_envelope = json.loads(messages[0]["value"])
    assert intent_envelope["event_type"] == "EVENT_PUBLISH_INTENT"

    # Parse intent payload
    intent_payload = intent_envelope["payload"]
    assert intent_payload["target_topic"] == "dev.omninode-bridge.metrics.v1"
    assert intent_payload["target_event_type"] == "METRICS_RECORDED"
    assert intent_payload["target_event_payload"]["metric_name"] == "processing_time"
    assert intent_payload["target_event_payload"]["value"] == 123.45
```

### Pattern 3: Correlation ID Propagation

Test that correlation IDs are properly propagated:

```python
@pytest.mark.asyncio
async def test_correlation_id_propagation():
    """Test that correlation ID flows through intent publishing."""
    # Arrange
    correlation_id = uuid4()
    mock_kafka = MockKafkaClient()
    container = create_test_container(kafka_client=mock_kafka)
    node = MyReducerNode(container)

    # Act
    result = await node.publish_event_intent(
        target_topic="my.topic.v1",
        target_key="test-key",
        event=create_test_event("TEST"),
        correlation_id=correlation_id
    )

    # Assert - Result has correlation ID
    assert result.correlation_id == correlation_id

    # Assert - Published message has correlation ID
    intent_envelope = json.loads(mock_kafka.published_messages[0]["value"])
    assert intent_envelope["correlation_id"] == str(correlation_id)
    assert intent_envelope["payload"]["correlation_id"] == str(correlation_id)
```

### Pattern 4: Priority Handling

Test that intent priorities are correctly set:

```python
@pytest.mark.asyncio
async def test_intent_priority_levels():
    """Test that different priority levels are handled correctly."""
    # Arrange
    mock_kafka = MockKafkaClient()
    container = create_test_container(kafka_client=mock_kafka)
    node = MyReducerNode(container)

    # Act - Publish high priority intent
    await node.publish_event_intent(
        target_topic="alerts.v1",
        target_key="alert-1",
        event=create_test_event("CRITICAL_ALERT"),
        priority=1  # Highest priority
    )

    # Act - Publish low priority intent
    await node.publish_event_intent(
        target_topic="metrics.v1",
        target_key="metric-1",
        event=create_test_event("DEBUG_METRIC"),
        priority=10  # Lowest priority
    )

    # Assert
    assert mock_kafka.get_message_count() == 2

    # Parse intents
    intents = [
        json.loads(msg["value"])["payload"]
        for msg in mock_kafka.published_messages
    ]

    assert intents[0]["priority"] == 1
    assert intents[1]["priority"] == 10
```

### Pattern 5: Error Handling

Test error handling when Kafka publishing fails:

```python
@pytest.mark.asyncio
async def test_kafka_publish_error_handling():
    """Test that Kafka publish errors are properly handled."""
    # Arrange
    mock_kafka = MockKafkaClient()
    mock_kafka.set_publish_error(RuntimeError("Kafka unavailable"))

    container = create_test_container(kafka_client=mock_kafka)
    node = MyReducerNode(container)

    # Act & Assert
    with pytest.raises(RuntimeError, match="Kafka unavailable"):
        await node.publish_event_intent(
            target_topic="test.topic.v1",
            target_key="test-key",
            event=create_test_event("TEST")
        )
```

### Pattern 6: Multiple Intent Publishing

Test nodes that publish multiple intents:

```python
@pytest.mark.asyncio
async def test_multiple_intent_publishing():
    """Test node that publishes multiple intents in one execution."""
    # Arrange
    mock_kafka = MockKafkaClient()
    container = create_test_container(kafka_client=mock_kafka)
    node = MyReducerNode(container)

    # Act - Execute operation that generates multiple intents
    result = await node.execute_batch_reduction([item1, item2, item3])

    # Assert - Multiple intents published
    assert mock_kafka.get_message_count() == 3

    # Assert - All intents have correct structure
    for message in mock_kafka.published_messages:
        intent_envelope = json.loads(message["value"])
        assert intent_envelope["event_type"] == "EVENT_PUBLISH_INTENT"
        assert "payload" in intent_envelope
```

### Pattern 7: Pure Function Testing

Test node logic WITHOUT Kafka (true unit test):

```python
@pytest.mark.asyncio
async def test_pure_reduction_logic():
    """Test pure reduction logic without intent publishing."""
    # Arrange - No Kafka client needed
    container = create_minimal_test_container()  # No kafka_client
    node = MyReducerNode(container)

    # Act - Test pure computation
    events = [
        create_test_event("METRIC", value=10),
        create_test_event("METRIC", value=20),
        create_test_event("METRIC", value=30),
    ]

    aggregated = node._aggregate_events(events)  # Call pure method directly

    # Assert - Pure computation is correct
    assert aggregated.total == 60
    assert aggregated.count == 3
    assert aggregated.average == 20.0
```

---

## Integration Test Setup

### Testing with Real Kafka (Optional)

For integration tests that need real Kafka:

```python
import pytest
from testcontainers.kafka import KafkaContainer

@pytest.fixture(scope="session")
def kafka_container():
    """Provide real Kafka container for integration tests."""
    with KafkaContainer() as kafka:
        yield kafka

@pytest.mark.integration
@pytest.mark.asyncio
async def test_intent_publishing_integration(kafka_container):
    """Integration test with real Kafka."""
    # Create real Kafka client
    kafka_client = create_kafka_client(
        bootstrap_servers=kafka_container.get_bootstrap_server()
    )

    container = create_test_container(kafka_client=kafka_client)
    node = MyReducerNode(container)

    # Act
    await node.publish_event_intent(
        target_topic="test.topic.v1",
        target_key="test-key",
        event=create_test_event("TEST")
    )

    # Assert - Consume from Kafka to verify
    # (implementation depends on your Kafka client)
```

---

## Common Patterns by Node Type

### REDUCER Node Testing

```python
@pytest.mark.asyncio
async def test_reducer_publishes_aggregated_result():
    """Test REDUCER publishes intent after aggregation."""
    # Arrange
    mock_kafka = MockKafkaClient()
    container = create_test_container(kafka_client=mock_kafka)
    reducer = MyReducerNode(container)

    events = [
        {"type": "METRIC", "value": 10},
        {"type": "METRIC", "value": 20},
        {"type": "METRIC", "value": 30},
    ]

    # Act - Reducer aggregates and publishes intent
    result = await reducer.execute_reduction(events)

    # Assert - Aggregation is correct (pure logic)
    assert result.total == 60

    # Assert - Intent published (coordination I/O)
    assert mock_kafka.get_message_count() == 1

    intent = json.loads(mock_kafka.published_messages[0]["value"])["payload"]
    assert intent["target_event_type"] == "METRICS_AGGREGATED"
    assert intent["target_event_payload"]["total"] == 60
```

### COMPUTE Node Testing

```python
@pytest.mark.asyncio
async def test_compute_publishes_result_intent():
    """Test COMPUTE publishes intent after computation."""
    # Arrange
    mock_kafka = MockKafkaClient()
    container = create_test_container(kafka_client=mock_kafka)
    compute = MyComputeNode(container)

    input_data = {"values": [1, 2, 3, 4, 5]}

    # Act - Compute processes and publishes intent
    result = await compute.execute_computation(input_data)

    # Assert - Computation is correct
    assert result.sum == 15
    assert result.average == 3.0

    # Assert - Intent published
    assert mock_kafka.get_message_count() == 1
```

### ORCHESTRATOR Node Testing

```python
@pytest.mark.asyncio
async def test_orchestrator_publishes_coordination_intents():
    """Test ORCHESTRATOR publishes coordination intents."""
    # Arrange
    mock_kafka = MockKafkaClient()
    container = create_test_container(kafka_client=mock_kafka)
    orchestrator = MyOrchestratorNode(container)

    workflow_request = {"steps": ["step1", "step2", "step3"]}

    # Act
    await orchestrator.execute_orchestration(workflow_request)

    # Assert - Multiple coordination intents published
    assert mock_kafka.get_message_count() == 3  # One per step

    # Assert - All are coordination events
    for message in mock_kafka.published_messages:
        intent = json.loads(message["value"])["payload"]
        assert "STEP_" in intent["target_event_type"]
```

---

## Best Practices

### ✅ DO: Test Intent Emission, Not Execution

```python
# ✅ CORRECT - Test intent is emitted correctly
@pytest.mark.asyncio
async def test_intent_emission():
    mock_kafka = MockKafkaClient()
    node = MyNode(create_test_container(kafka_client=mock_kafka))

    await node.do_work()

    # Assert intent was published
    assert mock_kafka.get_message_count() == 1
```

```python
# ❌ WRONG - Testing intent execution (not node's responsibility)
@pytest.mark.asyncio
async def test_intent_execution():
    # Don't test that event was actually published to target topic
    # That's the IntentExecutor's responsibility
    pass
```

### ✅ DO: Separate Pure Logic from Coordination

```python
# ✅ CORRECT - Test pure logic separately
def test_pure_aggregation():
    node = MyReducerNode(create_minimal_container())
    result = node._aggregate([1, 2, 3])  # Pure method
    assert result == 6

# ✅ CORRECT - Test coordination separately
@pytest.mark.asyncio
async def test_intent_coordination():
    mock_kafka = MockKafkaClient()
    node = MyReducerNode(create_test_container(kafka_client=mock_kafka))
    await node.execute_reduction([1, 2, 3])
    assert mock_kafka.get_message_count() == 1
```

### ✅ DO: Use Fixtures for Common Setup

```python
# ✅ CORRECT - Reusable test fixtures
@pytest.fixture
def mock_kafka():
    """Provide mock Kafka client for tests."""
    return MockKafkaClient()

@pytest.fixture
def test_node(mock_kafka):
    """Provide configured test node."""
    container = create_test_container(kafka_client=mock_kafka)
    return MyNode(container)

def test_with_fixtures(test_node, mock_kafka):
    # Clean test using fixtures
    pass
```

### ✅ DO: Test Error Scenarios

```python
# ✅ CORRECT - Test error handling
@pytest.mark.asyncio
async def test_kafka_failure_handling():
    mock_kafka = MockKafkaClient()
    mock_kafka.set_publish_error(RuntimeError("Connection failed"))

    node = MyNode(create_test_container(kafka_client=mock_kafka))

    with pytest.raises(RuntimeError):
        await node.publish_event_intent(...)
```

### ❌ DON'T: Mock MixinIntentPublisher Methods

```python
# ❌ WRONG - Don't mock the mixin itself
from unittest.mock import patch

@patch.object(MixinIntentPublisher, 'publish_event_intent')
async def test_bad_pattern(mock_publish):
    # This defeats the purpose of testing
    pass
```

### ❌ DON'T: Test with Real Kafka in Unit Tests

```python
# ❌ WRONG - Don't use real Kafka in unit tests
@pytest.mark.asyncio
async def test_with_real_kafka():
    kafka_client = KafkaClient(bootstrap_servers="localhost:9092")
    # Too slow, requires infrastructure, not isolated
```

---

## Example Test Suite

Complete example test suite for a REDUCER node using MixinIntentPublisher:

```python
"""
Test suite for MyMetricsReducer.

This reducer aggregates metrics and publishes the aggregated result
as an intent for eventual publishing to the metrics topic.
"""

import json
import pytest
from uuid import uuid4

from tests.fixtures.fixture_intent_publisher import (
    MockKafkaClient,
    create_test_event,
)
from omnibase_core.models.events.model_intent_events import TOPIC_EVENT_PUBLISH_INTENT


class TestMyMetricsReducer:
    """Test suite for metrics reducer with intent publishing."""

    @pytest.fixture
    def mock_kafka(self):
        """Provide mock Kafka client."""
        return MockKafkaClient()

    @pytest.fixture
    def reducer(self, mock_kafka):
        """Provide configured reducer instance."""
        container = create_test_container(kafka_client=mock_kafka)
        return MyMetricsReducer(container)

    @pytest.mark.asyncio
    async def test_aggregates_metrics_correctly(self, reducer):
        """Test pure aggregation logic."""
        # Arrange
        metrics = [
            {"metric": "api_latency", "value": 100},
            {"metric": "api_latency", "value": 200},
            {"metric": "api_latency", "value": 150},
        ]

        # Act
        result = reducer._aggregate_metrics(metrics)

        # Assert
        assert result.count == 3
        assert result.total == 450
        assert result.average == 150.0
        assert result.min == 100
        assert result.max == 200

    @pytest.mark.asyncio
    async def test_publishes_intent_after_aggregation(self, reducer, mock_kafka):
        """Test that reducer publishes intent after aggregation."""
        # Arrange
        metrics = [
            {"metric": "api_latency", "value": 100},
            {"metric": "api_latency", "value": 200},
        ]

        # Act
        await reducer.execute_reduction(metrics)

        # Assert
        assert mock_kafka.get_message_count() == 1
        assert mock_kafka.published_messages[0]["topic"] == TOPIC_EVENT_PUBLISH_INTENT

    @pytest.mark.asyncio
    async def test_intent_has_correct_target_and_payload(self, reducer, mock_kafka):
        """Test that published intent targets correct topic with correct payload."""
        # Arrange
        metrics = [{"metric": "api_latency", "value": 150}]

        # Act
        await reducer.execute_reduction(metrics)

        # Assert
        message = mock_kafka.published_messages[0]
        intent_envelope = json.loads(message["value"])
        intent_payload = intent_envelope["payload"]

        assert intent_payload["target_topic"] == "dev.omninode-bridge.metrics.aggregated.v1"
        assert intent_payload["target_event_type"] == "METRICS_AGGREGATED"

        event_payload = intent_payload["target_event_payload"]
        assert event_payload["metric"] == "api_latency"
        assert event_payload["average"] == 150.0

    @pytest.mark.asyncio
    async def test_correlation_id_propagated(self, reducer, mock_kafka):
        """Test that correlation ID flows through intent."""
        # Arrange
        correlation_id = uuid4()
        metrics = [{"metric": "test", "value": 1}]

        # Act
        await reducer.execute_reduction(metrics, correlation_id=correlation_id)

        # Assert
        message = mock_kafka.published_messages[0]
        intent_envelope = json.loads(message["value"])

        assert intent_envelope["correlation_id"] == str(correlation_id)
        assert intent_envelope["payload"]["correlation_id"] == str(correlation_id)

    @pytest.mark.asyncio
    async def test_handles_kafka_publish_error(self, reducer, mock_kafka):
        """Test error handling when Kafka publish fails."""
        # Arrange
        mock_kafka.set_publish_error(RuntimeError("Kafka connection failed"))
        metrics = [{"metric": "test", "value": 1}]

        # Act & Assert
        with pytest.raises(RuntimeError, match="Kafka connection failed"):
            await reducer.execute_reduction(metrics)
```

---

## Summary

### Key Testing Principles

1. **Test intent emission, not execution** - Nodes emit intents, executors run them
2. **Separate pure logic from coordination** - Test aggregation and intent publishing separately
3. **Use MockKafkaClient** - Fast, reliable, no infrastructure required
4. **Test error handling** - Verify graceful handling of Kafka failures
5. **Verify intent structure** - Assert on topic, key, payload, correlation ID

### Fixtures Available

- `IntentPublisherFixtures` - Fast intent model creation
- `IntentResultFixtures` - Fast result model creation
- `MockKafkaClient` - Test double for Kafka
- Helper functions for common test setup

### Documentation References

- **Pattern Guide**: [MODEL_INTENT_ARCHITECTURE.md](../../architecture/MODEL_INTENT_ARCHITECTURE.md)
- **Implementation**: [mixin_intent_publisher.py](../../../src/omnibase_core/mixins/mixin_intent_publisher.py)
- **Fixtures**: [fixture_intent_publisher.py](../../../tests/fixtures/fixture_intent_publisher.py)
- **General Testing**: [Testing Guide](../TESTING_GUIDE.md)

---

**Next Steps**:
- Review [Patterns Catalog](07_PATTERNS_CATALOG.md) for REDUCER-specific patterns and usage examples
- Check [Error Handling Best Practices](../../conventions/ERROR_HANDLING_BEST_PRACTICES.md) for error scenarios
- See [Common Pitfalls](08_COMMON_PITFALLS.md) for anti-patterns to avoid
