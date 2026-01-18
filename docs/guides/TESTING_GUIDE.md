> **Navigation**: [Home](../index.md) > Guides > Testing Guide

# Testing Guide - omnibase_core

**Status**: ✅ Complete

## Overview

This guide provides comprehensive testing strategies for ONEX nodes and the omnibase_core framework. It covers unit testing, integration testing, performance testing, and best practices for maintaining high-quality, reliable code.

## Testing Philosophy

### 1. Test Pyramid
- **Unit Tests** (70%) - Fast, isolated tests for individual components
- **Integration Tests** (20%) - Tests for component interactions
- **End-to-End Tests** (10%) - Full system tests

### 2. Testing Principles
- **Fast**: Tests should run quickly
- **Independent**: Tests should not depend on each other
- **Repeatable**: Tests should produce consistent results
- **Self-Validating**: Tests should have clear pass/fail criteria
- **Timely**: Tests should be written close to the code

## Unit Testing

### Basic Node Testing

#### COMPUTE Node Testing

```
import pytest
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.nodes.node_compute import NodeCompute

class TestComputeNode(NodeCompute):
    """Test implementation of COMPUTE node."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simple doubling operation for testing."""
        value = input_data.get("value", 0)
        return {"result": value * 2}

@pytest.fixture
def container():
    """Create test container."""
    return ModelONEXContainer()

@pytest.fixture
def compute_node(container):
    """Create test compute node."""
    return TestComputeNode(container)

@pytest.mark.asyncio
async def test_compute_node_basic(compute_node):
    """Test basic compute node functionality."""
    result = await compute_node.process({"value": 5})

    assert result["result"] == 10
    assert "result" in result

@pytest.mark.asyncio
async def test_compute_node_edge_cases(compute_node):
    """Test edge cases."""
    # Test zero
    result = await compute_node.process({"value": 0})
    assert result["result"] == 0

    # Test negative
    result = await compute_node.process({"value": -5})
    assert result["result"] == -10

    # Test missing value
    result = await compute_node.process({})
    assert result["result"] == 0
```

#### EFFECT Node Testing

```
import pytest
from unittest.mock import AsyncMock, MagicMock
from omnibase_core.nodes.node_effect import NodeEffect

class TestEffectNode(NodeEffect):
    """Test implementation of EFFECT node."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.external_service = None

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test effect operation."""
        if self.external_service:
            result = await self.external_service.call(input_data)
            return {"status": "success", "data": result}
        return {"status": "no_service"}

@pytest.fixture
def effect_node(container):
    """Create test effect node."""
    return TestEffectNode(container)

@pytest.mark.asyncio
async def test_effect_node_success(effect_node):
    """Test successful effect operation."""
    # Mock external service
    mock_service = AsyncMock()
    mock_service.call.return_value = {"external": "data"}
    effect_node.external_service = mock_service

    result = await effect_node.process({"input": "test"})

    assert result["status"] == "success"
    assert result["data"] == {"external": "data"}
    mock_service.call.assert_called_once_with({"input": "test"})

@pytest.mark.asyncio
async def test_effect_node_failure(effect_node):
    """Test effect operation failure."""
    # Mock external service to raise exception
    mock_service = AsyncMock()
    mock_service.call.side_effect = ConnectionError("Service unavailable")
    effect_node.external_service = mock_service

    with pytest.raises(ConnectionError):
        await effect_node.process({"input": "test"})
```

#### REDUCER Node Testing

```
import pytest
from omnibase_core.nodes.node_reducer import NodeReducer

class TestReducerNode(NodeReducer):
    """Test implementation of REDUCER node."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.state = {"count": 0, "items": []}

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test reducer operation."""
        action = input_data.get("action")

        if action == "increment":
            self.state["count"] += 1
        elif action == "add_item":
            item = input_data.get("item")
            self.state["items"].append(item)

        return {"state": self.state.copy()}

@pytest.fixture
def reducer_node(container):
    """Create test reducer node."""
    return TestReducerNode(container)

@pytest.mark.asyncio
async def test_reducer_node_increment(reducer_node):
    """Test state increment."""
    result = await reducer_node.process({"action": "increment"})

    assert result["state"]["count"] == 1
    assert result["state"]["items"] == []

@pytest.mark.asyncio
async def test_reducer_node_add_item(reducer_node):
    """Test adding item to state."""
    result = await reducer_node.process({
        "action": "add_item",
        "item": "test_item"
    })

    assert result["state"]["count"] == 0
    assert result["state"]["items"] == ["test_item"]

@pytest.mark.asyncio
async def test_reducer_node_state_persistence(reducer_node):
    """Test state persistence across operations."""
    # First operation
    await reducer_node.process({"action": "increment"})

    # Second operation
    result = await reducer_node.process({"action": "add_item", "item": "test"})

    assert result["state"]["count"] == 1
    assert result["state"]["items"] == ["test"]
```

### Error Handling Testing

```
import pytest
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

class TestErrorHandlingNode(NodeCompute):
    """Test node with error handling."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test error handling."""
        value = input_data.get("value")

        if value is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Value is required",
                context={"input_data": input_data}
            )

        if value < 0:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.PROCESSING_ERROR,
                message="Value must be positive",
                context={"value": value}
            )

        return {"result": value * 2}

@pytest.fixture
def error_node(container):
    """Create test error handling node."""
    return TestErrorHandlingNode(container)

@pytest.mark.asyncio
async def test_validation_error(error_node):
    """Test validation error handling."""
    with pytest.raises(ModelOnexError) as exc_info:
        await error_node.process({})

    error = exc_info.value
    assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
    assert "Value is required" in error.message

@pytest.mark.asyncio
async def test_processing_error(error_node):
    """Test processing error handling."""
    with pytest.raises(ModelOnexError) as exc_info:
        await error_node.process({"value": -5})

    error = exc_info.value
    assert error.error_code == EnumCoreErrorCode.PROCESSING_ERROR
    assert "Value must be positive" in error.message
```

### Circuit Breaker Testing

```
import pytest
from unittest.mock import AsyncMock
from omnibase_core.utils.circuit_breaker import CircuitBreaker

@pytest.fixture
def circuit_breaker():
    """Create test circuit breaker."""
    return CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=1.0
    )

@pytest.mark.asyncio
async def test_circuit_breaker_success(circuit_breaker):
    """Test successful circuit breaker operation."""
    mock_func = AsyncMock(return_value="success")

    result = await circuit_breaker.call(mock_func)

    assert result == "success"
    assert circuit_breaker.get_state() == "CLOSED"

@pytest.mark.asyncio
async def test_circuit_breaker_failure_threshold(circuit_breaker):
    """Test circuit breaker opening after failure threshold."""
    mock_func = AsyncMock(side_effect=Exception("Service error"))

    # First few failures should not open circuit
    for _ in range(2):
        with pytest.raises(Exception):
            await circuit_breaker.call(mock_func)

    assert circuit_breaker.get_state() == "CLOSED"

    # Third failure should open circuit
    with pytest.raises(Exception):
        await circuit_breaker.call(mock_func)

    assert circuit_breaker.get_state() == "OPEN"

@pytest.mark.asyncio
async def test_circuit_breaker_recovery(circuit_breaker):
    """Test circuit breaker recovery."""
    # Open the circuit
    mock_func = AsyncMock(side_effect=Exception("Service error"))
    for _ in range(3):
        with pytest.raises(Exception):
            await circuit_breaker.call(mock_func)

    assert circuit_breaker.get_state() == "OPEN"

    # Wait for recovery timeout
    await asyncio.sleep(1.1)

    # Test recovery
    mock_func.side_effect = None
    mock_func.return_value = "recovered"

    result = await circuit_breaker.call(mock_func)
    assert result == "recovered"
    assert circuit_breaker.get_state() == "CLOSED"
```

## Integration Testing

### Container Integration Testing

```
import pytest
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class MockDatabaseService:
    """Mock database service for testing."""

    async def query(self, sql: str) -> List[Dict[str, Any]]:
        """Mock database query."""
        return [{"id": 1, "name": "test"}]

class MockCacheService:
    """Mock cache service for testing."""

    def __init__(self):
        self.cache = {}

    async def get(self, key: str) -> Optional[Any]:
        """Mock cache get."""
        return self.cache.get(key)

    async def set(self, key: str, value: Any) -> None:
        """Mock cache set."""
        self.cache[key] = value

@pytest.fixture
def integration_container():
    """Create container with mock services."""
    container = ModelONEXContainer()

    # Register mock services
    container.register_service("DatabaseService", MockDatabaseService())
    container.register_service("CacheService", MockCacheService())

    return container

@pytest.mark.asyncio
async def test_container_service_resolution(integration_container):
    """Test service resolution from container."""
    db_service = integration_container.get_service("DatabaseService")
    cache_service = integration_container.get_service("CacheService")

    assert db_service is not None
    assert cache_service is not None

    # Test service functionality
    result = await db_service.query("SELECT * FROM users")
    assert result == [{"id": 1, "name": "test"}]

    await cache_service.set("test_key", "test_value")
    cached_value = await cache_service.get("test_key")
    assert cached_value == "test_value"
```

### Event System Integration Testing

```
import pytest
from omnibase_core.models.model_event_envelope import ModelEventEnvelope

class TestEventNode(NodeCompute):
    """Test node that emits events."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.emitted_events = []

    async def emit_event(self, event: ModelEventEnvelope) -> None:
        """Override to capture events for testing."""
        self.emitted_events.append(event)
        await super().emit_event(event)

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and emit event."""
        result = {"processed": True}

        # Emit event
        event = ModelEventEnvelope(
            event_type="data_processed",
            payload=result,
            source_node="test_node",
            target_node="effect_node"
        )
        await self.emit_event(event)

        return result

@pytest.fixture
def event_node(container):
    """Create test event node."""
    return TestEventNode(container)

@pytest.mark.asyncio
async def test_event_emission(event_node):
    """Test event emission."""
    result = await event_node.process({"input": "test"})

    assert result["processed"] is True
    assert len(event_node.emitted_events) == 1

    event = event_node.emitted_events[0]
    assert event.event_type == "data_processed"
    assert event.payload == {"processed": True}
    assert event.source_node == "test_node"
    assert event.target_node == "effect_node"
```

## Performance Testing

### Load Testing

```
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

@pytest.mark.asyncio
async def test_node_performance(compute_node):
    """Test node performance under load."""
    # Test single operation
    start_time = time.time()
    result = await compute_node.process({"value": 100})
    single_op_time = time.time() - start_time

    assert result["result"] == 200
    assert single_op_time < 0.1  # Should be fast

    # Test concurrent operations
    async def concurrent_operation():
        return await compute_node.process({"value": 50})

    start_time = time.time()
    tasks = [concurrent_operation() for _ in range(100)]
    results = await asyncio.gather(*tasks)
    concurrent_time = time.time() - start_time

    assert len(results) == 100
    assert all(r["result"] == 100 for r in results)
    assert concurrent_time < 1.0  # Should handle concurrency well

@pytest.mark.asyncio
async def test_memory_usage(compute_node):
    """Test memory usage patterns."""
    import psutil
    import os

    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss

    # Process many operations
    for _ in range(1000):
        await compute_node.process({"value": 42})

    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory

    # Memory increase should be reasonable (less than 10MB)
    assert memory_increase < 10 * 1024 * 1024
```

### Stress Testing

```
import pytest
import asyncio
import random

@pytest.mark.asyncio
async def test_stress_conditions(compute_node):
    """Test node under stress conditions."""
    # Test with large inputs
    large_input = {"value": 1000000}
    result = await compute_node.process(large_input)
    assert result["result"] == 2000000

    # Test with many concurrent operations
    async def stress_operation():
        value = random.randint(1, 1000)
        return await compute_node.process({"value": value})

    # Run 1000 concurrent operations
    tasks = [stress_operation() for _ in range(1000)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Check that all operations succeeded
    exceptions = [r for r in results if isinstance(r, Exception)]
    assert len(exceptions) == 0

    # Check that all results are valid
    valid_results = [r for r in results if isinstance(r, dict)]
    assert len(valid_results) == 1000
```

## Test Utilities

### Test Fixtures

```
import pytest
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

@pytest.fixture(scope="session")
def session_container():
    """Session-scoped container for expensive setup."""
    container = ModelONEXContainer()
    # Setup expensive services here
    return container

@pytest.fixture
def test_data():
    """Common test data."""
    return {
        "valid_input": {"value": 42},
        "invalid_input": {"value": -1},
        "edge_case": {"value": 0}
    }

@pytest.fixture
def mock_services():
    """Mock services for testing."""
    return {
        "database": AsyncMock(),
        "cache": AsyncMock(),
        "api": AsyncMock()
    }
```

### Test Helpers

```
import pytest
from typing import Dict, Any, List

class TestHelper:
    """Helper class for common test operations."""

    @staticmethod
    async def run_concurrent_operations(
        node: NodeCompute,
        operations: List[Dict[str, Any]],
        max_concurrency: int = 10
    ) -> List[Any]:
        """Run operations concurrently with limited concurrency."""
        semaphore = asyncio.Semaphore(max_concurrency)

        async def run_operation(operation):
            async with semaphore:
                return await node.process(operation)

        tasks = [run_operation(op) for op in operations]
        return await asyncio.gather(*tasks)

    @staticmethod
    def assert_error_code(error: Exception, expected_code: EnumCoreErrorCode):
        """Assert that error has expected code."""
        assert isinstance(error, ModelOnexError)
        assert error.error_code == expected_code

    @staticmethod
    def assert_performance_metrics(metrics: Dict[str, Any], max_time: float):
        """Assert performance metrics are within limits."""
        assert "processing_time" in metrics
        assert metrics["processing_time"] < max_time

# Usage in tests
@pytest.mark.asyncio
async def test_with_helper(compute_node):
    """Test using helper methods."""
    operations = [{"value": i} for i in range(100)]

    results = await TestHelper.run_concurrent_operations(
        compute_node,
        operations,
        max_concurrency=5
    )

    assert len(results) == 100
    assert all(r["result"] == i * 2 for i, r in enumerate(results))
```

## Test Configuration

### pytest.ini

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --asyncio-mode=auto
markers =
    unit: Unit tests
    integration: Integration tests
    performance: Performance tests
    slow: Slow tests
```

### conftest.py

```
import pytest
import asyncio
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def container():
    """Create test container."""
    return ModelONEXContainer()

@pytest.fixture(autouse=True)
def reset_container(container):
    """Reset container state between tests."""
    yield
    # Cleanup if needed
    container.clear_services()
```

## Best Practices

### 1. Test Organization

```
# tests/unit/test_compute_node.py
class TestComputeNode:
    """Test class for COMPUTE node functionality."""

    def test_basic_operation(self):
        """Test basic compute operation."""
        pass

    def test_edge_cases(self):
        """Test edge cases."""
        pass

    def test_error_handling(self):
        """Test error handling."""
        pass

# tests/integration/test_node_integration.py
class TestNodeIntegration:
    """Test class for node integration."""

    def test_container_integration(self):
        """Test container integration."""
        pass

    def test_event_integration(self):
        """Test event system integration."""
        pass
```

### 2. Test Data Management

```
# tests/fixtures/test_data.py
VALID_INPUTS = [
    {"value": 1},
    {"value": 100},
    {"value": 0}
]

INVALID_INPUTS = [
    {"value": -1},
    {"value": None},
    {}
]

EXPECTED_OUTPUTS = [
    {"result": 2},
    {"result": 200},
    {"result": 0}
]
```

### 3. Mocking Strategies

```
from unittest.mock import AsyncMock, MagicMock, patch

# Mock external dependencies
@patch('omnibase_core.services.database_service.DatabaseService')
def test_with_mocked_database(mock_db_service):
    """Test with mocked database service."""
    mock_db_service.return_value.query.return_value = [{"id": 1}]
    # Test logic here

# Mock async functions
@pytest.mark.asyncio
async def test_with_async_mock():
    """Test with async mock."""
    mock_func = AsyncMock(return_value="mocked_result")
    result = await mock_func()
    assert result == "mocked_result"
```

### 4. Test Coverage

```
# Run tests with coverage
# pytest --cov=omnibase_core --cov-report=html

# Coverage configuration in pyproject.toml
[tool.coverage.run]
source = ["omnibase_core"]
omit = [
    "*/tests/*",
    "*/test_*",
    "*/__pycache__/*"
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError"
]
```

## Continuous Integration

### omnibase_core CI Strategy

The project uses a sophisticated CI pipeline with parallel test execution for optimal performance and reliability.

#### CI Pipeline Architecture

**Jobs**:
1. **Smoke Tests** (5-10s) - Fast-fail basic validation
2. **Parallel Tests** (12 splits, 3-5 min each) - Full test suite with optimal resource usage
3. **Code Quality** - Black, isort, mypy strict type checking
4. **Documentation Validation** - Link validation and documentation checks
5. **Coverage Report** (main branch only) - Comprehensive coverage analysis

#### Parallel Test Execution

**Strategy Rationale**:
- **Total Tests**: 12,198 tests
- **Split Count (CI)**: 20 parallel jobs (~610 tests/split)
- **Split Count (Local)**: 12 parallel jobs (~1,016 tests/split)
- **Duration**: 3-5 minutes per split (vs ~40+ minutes sequential)
- **Speedup**: 12-20x parallelization
- **Resource Management**: Prevents memory exhaustion with controlled parallelism

**Split Configuration**:

```
# Each split runs a subset of tests using pytest-split
poetry run pytest tests/ \
  --splits 12 \
  --group $SPLIT_NUMBER \
  -n auto \
  --timeout=60 \
  --timeout-method=thread \
  --tb=short
```

**Why 12 Splits?**:
- Increased from 10 to 12 splits to reduce resource exhaustion
- Each split stays under 5 minutes (GitHub Actions best practice)
- Optimal balance between parallelization and overhead
- Prevents individual split timeouts

#### Local Testing Commands

**Standard local testing** (matches pyproject.toml config):
```
# Run all tests with 4 workers (default)
poetry run pytest tests/

# Run specific test file
poetry run pytest tests/unit/models/test_model.py -v

# Run with full parallelism (for powerful machines)
poetry run pytest tests/ -n 8

# Debug single test (disable parallelism)
poetry run pytest tests/unit/test_specific.py -n 0 -xvs
```

**CI-equivalent local testing** (12 splits):
```
# Run specific split locally (e.g., split 1 of 12)
poetry run pytest tests/ --splits 12 --group 1 -n auto

# Run all splits sequentially (full CI simulation)
for i in {1..12}; do
  poetry run pytest tests/ --splits 12 --group $i -n auto
done
```

#### Timeout Configuration

**Per-test timeout**:
- `--timeout=60` (60 seconds per test)
- `--timeout-method=thread` (avoids signal handler conflicts)
- Prevents infinite hangs in async code or event loop issues
- 2x safety margin over longest test (~30s)

**Job-level timeout**:
- Smoke tests: 5 minutes
- Parallel tests: 60 minutes (generous buffer for occasional slowdowns)
- Code quality: 10 minutes
- Coverage: 15 minutes

#### Type Checking in CI

**Status**: ✅ Enabled with strict configuration

```
# CI runs strict mypy (0 errors required)
poetry run mypy src/omnibase_core/
```

**Strict Mode**:
- `disallow_untyped_defs = true`
- All 1865 source files must pass
- Same configuration as pre-commit hooks and local development

#### Coverage Requirements

**Target**: 60% minimum coverage (configured in pyproject.toml)

```
# Run coverage locally
poetry run pytest tests/ --cov=src/omnibase_core --cov-report=term-missing --cov-report=html

# View HTML report
open htmlcov/index.html
```

**CI Coverage**:
- Only runs on `main` branch (saves CI time on PRs)
- Generates XML and HTML reports
- Uploaded as workflow artifacts (30-day retention)

#### GitHub Actions Configuration

See `.github/workflows/test.yml` for complete configuration. Key features:

- **Poetry 2.2.1**: Latest stable Poetry version
- **Python 3.12**: Minimum supported version
- **Caching**: Poetry virtualenv caching with version key
- **Fail-fast**: Disabled to collect all split results
- **Artifacts**: Test results (7 days), coverage reports (30 days)

## Related Documentation

- [Node Building Guide](node-building/README.md) - Implementation tutorials
- [Error Handling](../conventions/ERROR_HANDLING_BEST_PRACTICES.md) - Error handling patterns
- [API Reference](../reference/api/nodes.md) - Complete API documentation
- [Architecture Overview](../architecture/overview.md) - System design
