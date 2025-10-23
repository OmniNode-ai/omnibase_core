# Testing Guide - omnibase_core

**Status**: ✅ Production Ready
**Last Updated**: October 23, 2025

## Overview

Comprehensive testing strategies for ONEX nodes and services, including specialized patterns for testing coordination I/O via MixinIntentPublisher.

## Testing Philosophy

1. **Test behavior, not implementation**
2. **Test at the right level** (unit vs integration)
3. **Test error paths** (not just happy paths)
4. **Make tests readable** (tests are documentation)
5. **Separate pure logic from coordination** (test domain logic and I/O separately)

## Testing Node Types

### EFFECT Nodes
- Mock external dependencies
- Test transaction rollback
- Verify idempotency
- Test circuit breaker behavior
- Test retry logic and backoff strategies

### COMPUTE Nodes
- Test pure transformations
- Verify cache behavior
- Test all input combinations
- Benchmark performance
- **NEW**: Test intent publishing for result coordination (see [Intent Publisher Testing](#intent-publisher-testing))

### REDUCER Nodes
- Test state transitions
- Verify Intent emission
- Test FSM properties
- Check immutability
- **NEW**: Test coordination I/O via MixinIntentPublisher (see [Intent Publisher Testing](#intent-publisher-testing))

### ORCHESTRATOR Nodes
- Test workflow execution
- Verify coordination logic
- Test error recovery
- Check dependency handling
- **NEW**: Test coordination event intents (see [Intent Publisher Testing](#intent-publisher-testing))

## Testing Patterns

### Unit Testing
```python
import pytest
from my_node import NodeMyServiceCompute

@pytest.mark.asyncio
async def test_my_node_computation():
    # Arrange
    container = create_test_container()
    node = NodeMyServiceCompute(container)

    # Act
    result = await node.process({"value": 5})

    # Assert
    assert result["output"] == 10
```

### Integration Testing
```python
@pytest.mark.integration
async def test_node_with_dependencies():
    # Test with real dependencies
    pass
```

### Property-Based Testing
```python
from hypothesis import given, strategies as st

@given(st.integers())
def test_node_property(value):
    # Property that should hold for all inputs
    pass
```

## Test Organization

```
tests/
├── unit/              # Unit tests
│   ├── nodes/
│   ├── models/
│   └── utils/
├── integration/       # Integration tests
│   ├── workflows/
│   └── end_to_end/
└── conftest.py        # Shared fixtures
```

## Intent Publisher Testing

**NEW**: Comprehensive testing support for nodes using `MixinIntentPublisher` for coordination I/O.

### Quick Start

```python
from tests.fixtures.fixture_intent_publisher import MockKafkaClient

@pytest.mark.asyncio
async def test_node_publishes_intent():
    # Arrange
    mock_kafka = MockKafkaClient()
    container = create_test_container(kafka_client=mock_kafka)
    node = MyReducerNode(container)

    # Act
    await node.execute_reduction(test_data)

    # Assert - Intent was published
    assert mock_kafka.get_message_count() == 1
    assert mock_kafka.published_messages[0]["topic"] == "dev.omninode-bridge.intents.event-publish.v1"
```

### Available Test Fixtures

```python
from tests.fixtures.fixture_intent_publisher import (
    IntentPublisherFixtures,    # Intent event models
    IntentResultFixtures,        # Intent publish results
    MockKafkaClient,             # Test double for Kafka
    create_mock_kafka_client,    # Convenience factory
    create_test_event,           # Simple test event generator
)
```

### Testing Patterns

1. **Test intent emission** - Verify node publishes intent correctly
2. **Test intent content** - Assert on target topic, key, payload
3. **Test correlation ID propagation** - Verify tracing through workflow
4. **Test priority handling** - Assert on intent priority levels
5. **Test error handling** - Verify graceful Kafka failure handling
6. **Test pure logic separately** - Unit test domain logic without I/O

### Complete Guide

See [Testing Intent Publisher Pattern](node-building/09-testing-intent-publisher.md) for:
- Comprehensive testing patterns
- Complete example test suite
- Integration test setup
- Best practices and anti-patterns
- Node type-specific examples (REDUCER, COMPUTE, ORCHESTRATOR)

## Running Tests

```bash
# All tests
poetry run pytest tests/

# Specific test file
poetry run pytest tests/unit/test_my_node.py

# With coverage
poetry run pytest tests/ --cov=src --cov-report=html

# Fast tests only
poetry run pytest tests/ -m "not slow"

# Integration tests only
poetry run pytest tests/ -m integration

# Verbose output
poetry run pytest tests/ -v

# Test specific pattern (e.g., intent publisher tests)
poetry run pytest tests/ -k "intent" -v
```

## Coverage Goals

- **Minimum**: 80% code coverage
- **Target**: 90% code coverage
- **Critical paths**: 100% coverage
- **Intent publisher code**: 95%+ coverage (coordination I/O is critical)

## Test Organization Best Practices

### Unit Tests
```
tests/unit/
├── nodes/              # Node logic tests
│   ├── test_compute_nodes.py
│   ├── test_reducer_nodes.py
│   └── test_orchestrator_nodes.py
├── mixins/             # Mixin tests
│   └── test_mixin_intent_publisher.py  # When available
├── models/             # Model tests
└── utils/              # Utility tests
```

### Integration Tests
```
tests/integration/
├── test_intent_publishing_integration.py
├── workflows/
└── end_to_end/
```

### Test Fixtures
```
tests/fixtures/
├── fixture_base.py                 # Base fixture class
├── fixture_intent_publisher.py     # Intent publisher fixtures
├── fixture_context.py              # Context fixtures
└── README.md                       # Fixture documentation
```

## Next Steps

- [Node Building Guide](node-building/README.md) - Implementation patterns
- [Testing Intent Publisher](node-building/09-testing-intent-publisher.md) - Coordination I/O testing
- [Debugging Guide](debugging-guide.md) - When tests fail
- [Development Workflow](development-workflow.md) - Complete workflow

---

**Related Documentation**:
- [Testing Pure FSM](node-building/08-testing-pure-fsm.md) - REDUCER testing patterns
- [Testing Intent Publisher](node-building/09-testing-intent-publisher.md) - **NEW** Coordination I/O testing
- [Error Handling](../conventions/ERROR_HANDLING_BEST_PRACTICES.md) - Error testing best practices
- [Test Fixtures README](../../tests/fixtures/README.md) - Fixture usage and performance
