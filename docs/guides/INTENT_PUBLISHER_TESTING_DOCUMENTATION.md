# Intent Publisher Testing Documentation - Complete Guide

**Status**: ✅ Production Ready
**Date**: October 23, 2025
**Pattern**: MixinIntentPublisher Testing Infrastructure

---

## Overview

This document provides a comprehensive index of all documentation related to testing nodes using `MixinIntentPublisher` - the coordination I/O pattern for ONEX nodes.

## What is MixinIntentPublisher?

`MixinIntentPublisher` is a mixin that enables ONEX nodes (especially REDUCER and COMPUTE nodes) to publish events to Kafka topics while maintaining architectural purity. Instead of publishing directly to Kafka (domain I/O), nodes publish "intents" to a coordination topic.

**Key Benefits**:
- ✅ Maintains node purity (no direct domain I/O)
- ✅ Easy to test (MockKafkaClient, no real Kafka needed)
- ✅ Traceable coordination via intent events
- ✅ Decoupled event production from publishing

---

## Documentation Structure

### 1. Primary Testing Guide

**File**: `docs/guides/node-building/09-testing-intent-publisher.md`

**Content**:
- Comprehensive testing patterns for MixinIntentPublisher
- Test fixtures overview and usage
- 7 testing patterns with complete examples
- Integration test setup guidance
- Node type-specific examples (REDUCER, COMPUTE, ORCHESTRATOR)
- Best practices and anti-patterns
- Complete example test suite

**Use This For**: Learning how to test nodes using MixinIntentPublisher

---

### 2. General Testing Guide

**File**: `docs/guides/TESTING_GUIDE.md`

**Updated Sections**:
- Intent Publisher Testing quick start
- Available test fixtures overview
- Testing patterns summary
- Test organization best practices
- Coverage goals for intent publisher code

**Use This For**: General testing overview with intent publisher context

---

### 3. REDUCER Tutorial with Intent Publishing

**File**: `docs/guides/node-building/05_REDUCER_NODE_TUTORIAL.md`

**New Section**: "Using MixinIntentPublisher for Event Publishing"

**Content**:
- When to use MixinIntentPublisher
- Step-by-step integration guide
- Testing with MixinIntentPublisher
- Pattern comparison (ModelIntent vs MixinIntentPublisher)
- Complete working example

**Use This For**: Learning how to add intent publishing to REDUCER nodes

---

### 4. Test Fixtures

**File**: `tests/fixtures/fixture_intent_publisher.py`

**Provides**:
- `IntentPublisherFixtures` - Fast intent event model creation
- `IntentResultFixtures` - Fast result model creation
- `MockKafkaClient` - Test double for Kafka client
- `create_mock_kafka_client()` - Convenience factory
- `create_test_event()` - Simple test event generator

**Use This For**: Creating test fixtures and mocks in your tests

---

### 5. Fixtures README

**File**: `tests/fixtures/README.md`

**Updated Section**: "Available Fixtures"

**Content**:
- Intent publisher fixtures overview
- Quick usage examples
- Use cases for intent publisher testing
- Link to comprehensive guide

**Use This For**: Quick reference on available fixtures

---

## Quick Start

### 1. Import Test Fixtures

```python
from tests.fixtures.fixture_intent_publisher import (
    MockKafkaClient,
    create_test_event,
)
```python

### 2. Create Mock Kafka Client

```python
@pytest.fixture
def mock_kafka():
    return MockKafkaClient()

@pytest.fixture
def test_node(mock_kafka):
    container = create_test_container(kafka_client=mock_kafka)
    return MyReducerNode(container)
```python

### 3. Write Test

```python
@pytest.mark.asyncio
async def test_node_publishes_intent(test_node, mock_kafka):
    # Act
    await test_node.execute_reduction(test_data)

    # Assert
    assert mock_kafka.get_message_count() == 1
    assert mock_kafka.published_messages[0]["topic"] == "dev.omninode-bridge.intents.event-publish.v1"
```python

---

## Testing Patterns Index

### Pattern 1: Basic Intent Publishing
**File**: `09-testing-intent-publisher.md` → "Pattern 1"
**Tests**: Node publishes intent with correct structure

### Pattern 2: Intent Content Verification
**File**: `09-testing-intent-publisher.md` → "Pattern 2"
**Tests**: Intent contains correct target topic, key, and payload

### Pattern 3: Correlation ID Propagation
**File**: `09-testing-intent-publisher.md` → "Pattern 3"
**Tests**: Correlation IDs flow through intent publishing

### Pattern 4: Priority Handling
**File**: `09-testing-intent-publisher.md` → "Pattern 4"
**Tests**: Intent priorities are correctly set

### Pattern 5: Error Handling
**File**: `09-testing-intent-publisher.md` → "Pattern 5"
**Tests**: Graceful handling of Kafka publishing failures

### Pattern 6: Multiple Intent Publishing
**File**: `09-testing-intent-publisher.md` → "Pattern 6"
**Tests**: Nodes that publish multiple intents

### Pattern 7: Pure Function Testing
**File**: `09-testing-intent-publisher.md` → "Pattern 7"
**Tests**: Pure logic without Kafka (true unit tests)

---

## Node Type Examples

### REDUCER Node Testing
**File**: `09-testing-intent-publisher.md` → "REDUCER Node Testing"
**Example**: Testing aggregation and intent publishing

### COMPUTE Node Testing
**File**: `09-testing-intent-publisher.md` → "COMPUTE Node Testing"
**Example**: Testing computation and result intent publishing

### ORCHESTRATOR Node Testing
**File**: `09-testing-intent-publisher.md` → "ORCHESTRATOR Node Testing"
**Example**: Testing coordination intent publishing

---

## Architecture Documentation

### Intent Pattern Architecture
**File**: `docs/architecture/MODEL_INTENT_ARCHITECTURE.md`
**Content**: Complete intent pattern specification, ModelIntent vs MixinIntentPublisher

### MixinIntentPublisher Implementation
**File**: `src/omnibase_core/mixins/mixin_intent_publisher.py`
**Content**: Production implementation with comprehensive docstrings

### Intent Event Models
**File**: `src/omnibase_core/models/events/model_intent_events.py`
**Content**: ModelEventPublishIntent, ModelIntentExecutionResult

---

## Common Use Cases

### Testing REDUCER Publishing Aggregated Results

```python
@pytest.mark.asyncio
async def test_reducer_publishes_aggregated_results():
    mock_kafka = MockKafkaClient()
    reducer = NodeMetricsReducer(create_test_container(kafka_client=mock_kafka))

    await reducer.execute_reduction([data1, data2, data3])

    assert mock_kafka.get_message_count() == 1
    intent = json.loads(mock_kafka.published_messages[0]["value"])["payload"]
    assert intent["target_event_type"] == "METRICS_AGGREGATED"
```python

### Testing COMPUTE Publishing Computed Results

```python
@pytest.mark.asyncio
async def test_compute_publishes_result():
    mock_kafka = MockKafkaClient()
    compute = NodeDataTransformer(create_test_container(kafka_client=mock_kafka))

    result = await compute.execute_computation(input_data)

    assert mock_kafka.get_message_count() == 1
    assert result.transformed is True
```python

### Testing Error Handling

```python
@pytest.mark.asyncio
async def test_kafka_failure_handling():
    mock_kafka = MockKafkaClient()
    mock_kafka.set_publish_error(RuntimeError("Kafka unavailable"))
    node = MyNode(create_test_container(kafka_client=mock_kafka))

    with pytest.raises(RuntimeError, match="Kafka unavailable"):
        await node.publish_event_intent(...)
```python

---

## Best Practices Summary

### ✅ DO

1. **Test intent emission, not execution** - Nodes emit intents, executors run them
2. **Separate pure logic from coordination** - Test aggregation separately from intent publishing
3. **Use MockKafkaClient** - Fast, reliable, no infrastructure required
4. **Test error scenarios** - Verify graceful Kafka failure handling
5. **Verify intent structure** - Assert on topic, key, payload, correlation ID
6. **Use fixtures** - Reusable test setup via pytest fixtures

### ❌ DON'T

1. **Don't mock MixinIntentPublisher methods** - Mock the Kafka client instead
2. **Don't test intent execution** - That's the IntentExecutor's responsibility
3. **Don't use real Kafka in unit tests** - Too slow and not isolated
4. **Don't test implementation details** - Test behavior, not internal methods
5. **Don't skip error handling tests** - Kafka failures are common in production

---

## Running Tests

```bash
# All intent publisher tests
poetry run pytest tests/ -k "intent" -v

# Specific test file
poetry run pytest tests/unit/nodes/test_my_reducer.py -v

# With coverage
poetry run pytest tests/ --cov=src/omnibase_core/mixins/mixin_intent_publisher.py --cov-report=term-missing

# Fast tests only (no integration)
poetry run pytest tests/ -m "not integration" -v
```python

---

## Coverage Goals

- **Intent publisher mixin**: 95%+ coverage (critical coordination code)
- **Intent event models**: 90%+ coverage
- **Node intent publishing logic**: 85%+ coverage
- **Test fixtures**: 80%+ coverage (test-only code)

---

## Troubleshooting

### Issue: Tests fail with "kafka_client service missing"

**Solution**: Ensure MockKafkaClient is registered in test container:

```python
def create_test_container(kafka_client=None):
    container = ModelONEXContainer()
    container.register_service("kafka_client", kafka_client or MockKafkaClient())
    return container
```text

### Issue: Intent envelope parsing fails

**Solution**: Parse JSON carefully, accounting for envelope structure:

```python
intent_envelope = json.loads(message["value"])
intent_payload = intent_envelope["payload"]  # Intent is inside envelope
```text

### Issue: Correlation ID doesn't match

**Solution**: UUIDs are serialized as strings in JSON:

```python
# Correct
assert intent_envelope["correlation_id"] == str(correlation_id)

# Incorrect
assert intent_envelope["correlation_id"] == correlation_id  # Type mismatch
```python

---

## Future Enhancements

### Planned Additions

1. **IntentExecutor Node** - Execute intents published to coordination topic
2. **Integration Tests** - End-to-end tests with real Kafka (testcontainers)
3. **Performance Benchmarks** - Intent publishing latency metrics
4. **Intent Replay** - Replay intents for debugging and testing

### Documentation Improvements

1. **Video Tutorials** - Screen recordings of testing workflows
2. **Interactive Examples** - Jupyter notebooks with live testing
3. **Migration Guide** - Converting from direct Kafka to intent pattern
4. **Troubleshooting Cookbook** - Common issues and solutions

---

## Summary

This documentation suite provides complete coverage of testing nodes using MixinIntentPublisher:

| Document | Purpose | Audience |
|----------|---------|----------|
| `09-testing-intent-publisher.md` | Comprehensive testing guide | Developers writing tests |
| `TESTING_GUIDE.md` | General testing overview | All developers |
| `05_REDUCER_NODE_TUTORIAL.md` | REDUCER-specific patterns | REDUCER developers |
| `fixture_intent_publisher.py` | Test fixtures implementation | Test authors |
| `fixtures/README.md` | Fixtures quick reference | All developers |

**Start Here**: Read `09-testing-intent-publisher.md` for comprehensive testing patterns, then refer to other documents as needed.

---

## Related Documentation

- [MODEL_INTENT_ARCHITECTURE.md](../architecture/MODEL_INTENT_ARCHITECTURE.md) - Intent pattern architecture
- [Error Handling Best Practices](../conventions/ERROR_HANDLING_BEST_PRACTICES.md) - Error testing patterns
- [Testing Intent Publisher](node-building/09_TESTING_INTENT_PUBLISHER.md) - Intent publisher testing patterns
- [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) - Overall architecture

---

**Last Updated**: October 23, 2025
**Maintainer**: omnibase_core team
**Status**: ✅ Production Ready
