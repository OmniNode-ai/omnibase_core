# Testing Guide - omnibase_core

**Status**: 🚧 Coming Soon

## Overview

Comprehensive testing strategies for ONEX nodes and services.

## Testing Philosophy

1. **Test behavior, not implementation**
2. **Test at the right level** (unit vs integration)
3. **Test error paths** (not just happy paths)
4. **Make tests readable** (tests are documentation)

## Testing Node Types

### EFFECT Nodes
- Mock external dependencies
- Test transaction rollback
- Verify idempotency
- Test circuit breaker behavior

### COMPUTE Nodes
- Test pure transformations
- Verify cache behavior
- Test all input combinations
- Benchmark performance

### REDUCER Nodes
- Test state transitions
- Verify Intent emission
- Test FSM properties
- Check immutability

### ORCHESTRATOR Nodes
- Test workflow execution
- Verify coordination logic
- Test error recovery
- Check dependency handling

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

# Verbose output
poetry run pytest tests/ -v
```

## Coverage Goals

- **Minimum**: 80% code coverage
- **Target**: 90% code coverage
- **Critical paths**: 100% coverage

## Next Steps

- [Node Building Guide](node-building/README.md) - Implementation patterns
- [Debugging Guide](debugging-guide.md) - When tests fail
- [Development Workflow](development-workflow.md) - Complete workflow

---

**Related Documentation**:
- [Testing Pure FSM](node-building/08-testing-pure-fsm.md)
- [Error Handling](../conventions/ERROR_HANDLING_BEST_PRACTICES.md)
