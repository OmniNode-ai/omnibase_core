# Integration Testing Guide - omnibase_core

**Status**: Complete
**Version**: 0.4.0

## Overview

Integration tests validate the interaction between multiple components working together in realistic scenarios. Unlike unit tests that isolate individual components, integration tests verify:

- Cross-module data flow and coordination
- Service orchestration and lifecycle management
- Multi-step workflow execution
- Error propagation across component boundaries
- Real-world usage patterns without mocking (where possible)

In omnibase_core, integration tests complement the 12,000+ unit tests by ensuring that components work correctly together in production-like scenarios.

## Test Philosophy

### Integration vs Unit Tests

| Aspect | Unit Tests | Integration Tests |
|--------|------------|-------------------|
| **Scope** | Single component in isolation | Multiple components interacting |
| **Mocking** | Heavy mocking of dependencies | Minimal mocking (real components) |
| **Speed** | Very fast (< 1ms typically) | Slower (10-500ms typically) |
| **Coverage Goal** | 70% of test suite | 20% of test suite |
| **Focus** | Implementation correctness | Component interaction |
| **Location** | `tests/unit/` | `tests/integration/` |

### When to Write Integration Tests

Write integration tests when verifying:

1. **Cross-module workflows** - Data flowing through multiple components
2. **Service orchestration** - Multiple services coordinating actions
3. **State management** - State transitions across components
4. **Error propagation** - Errors flowing through component chains
5. **Event-driven patterns** - Kafka/event bus message flows
6. **Contract compliance** - Full contract execution (not just parsing)

## Integration Test Structure

### Directory Organization

```text
tests/integration/
├── __init__.py
├── conftest.py                              # Shared fixtures for integration tests
├── test_cache_config_integration.py         # Cache configuration tests
├── test_compute_pipeline_integration.py     # Full compute pipeline scenarios
├── test_intent_publisher_integration.py     # Kafka intent publishing workflow
├── test_multi_module_workflows.py           # Cross-module coordination
├── test_service_orchestration.py            # Service lifecycle management
├── test_validation_integration.py           # Validation across components
├── mixins/
│   └── test_mixin_health_check_integration.py  # Mixin integration tests
└── scripts/
    └── test_check_transport_imports_integration.py  # Import validation
```

### Naming Conventions

- File names: `test_<domain>_integration.py`
- Test classes: `Test<Feature>Integration` or `Test<Workflow>Scenario`
- Test methods: `test_<scenario>_<expected_behavior>()`

## Test Scenarios

### 1. Happy Path Tests

Test the expected successful flow through components.

```python
@pytest.mark.integration
class TestServiceHealthLifecycle:
    """Test complete service health monitoring lifecycle."""

    def test_healthy_service_creation_and_analysis(self):
        """Test creating and analyzing a healthy service."""
        # Create healthy service
        service = ModelServiceHealth.create_healthy(
            service_name="postgres_db",
            service_type="postgresql",
            connection_string="postgresql://***:***@localhost:5432/mydb",
            response_time_ms=50,
        )

        # Verify basic properties
        assert service.service_name == "postgres_db"
        assert service.is_healthy()
        assert service.calculate_reliability_score() == 1.0
        assert service.get_performance_category() == "excellent"
```

### 2. Error Path Tests

Test error propagation and handling across components.

```python
@pytest.mark.integration
class TestErrorHandlingIntegration:
    """Test error handling across multiple modules."""

    def test_chained_error_handling(self):
        """Test error handling chain across multiple operations."""
        errors_encountered = []

        # Simulate multiple operations with error handling
        try:
            # Operation 1: Invalid service creation
            ModelServiceHealth(
                service_name="123invalid",  # Starts with number - invalid
                service_type=EnumServiceType.REST_API,
                status=EnumServiceHealthStatus.REACHABLE,
                connection_string="https://api.example.com",
                last_check_time=datetime.now(UTC).isoformat(),
            )
        except OnexError as e:
            errors_encountered.append(("service_creation", e.error_code))

        # Verify error was caught with correct code
        assert len(errors_encountered) == 1
        assert errors_encountered[0][1] == EnumCoreErrorCode.VALIDATION_ERROR
```

### 3. Multi-step Workflow Tests

Test complete workflows with multiple sequential steps.

```python
@pytest.mark.integration
@pytest.mark.timeout(60)  # CI protection
class TestComputePipelineIntegration:
    """Integration tests for complete pipeline scenarios."""

    def test_multi_step_pipeline_execution(
        self, compute_execution_context_factory: ComputeContextFactory
    ) -> None:
        """Test pipeline with multiple transformation steps chained together."""
        # Create pipeline: TRIM -> CASE_CONVERSION -> IDENTITY
        contract = ModelComputeSubcontract(
            operation_name="multi_step_test",
            operation_version={"major": 1, "minor": 0, "patch": 0},
            pipeline=[
                ModelComputePipelineStep(
                    step_name="trim_input",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.TRIM,
                    transformation_config=ModelTransformTrimConfig(
                        mode=EnumTrimMode.BOTH
                    ),
                ),
                ModelComputePipelineStep(
                    step_name="uppercase",
                    step_type=EnumComputeStepType.TRANSFORMATION,
                    transformation_type=EnumTransformationType.CASE_CONVERSION,
                    transformation_config=ModelTransformCaseConfig(
                        mode=EnumCaseMode.UPPER
                    ),
                ),
            ],
        )

        result = execute_compute_pipeline(
            contract=contract,
            input_data="  hello world  ",
            context=compute_execution_context_factory(),
        )

        assert result.success is True
        assert result.output == "HELLO WORLD"
        assert len(result.steps_executed) == 2
```

### 4. Event-Driven Workflow Tests

Test Kafka/event bus message flows.

```python
@pytest.mark.integration
class TestIntentPublisherIntegration:
    """Integration tests for intent publisher pattern."""

    @pytest.mark.asyncio
    async def test_correlation_id_tracking_through_workflow(
        self, container_with_kafka, mock_kafka_client
    ):
        """Test correlation ID preservation through entire workflow."""
        orchestrator = MockOrchestratorWithIntentPublisher(container_with_kafka)

        workflow_id = uuid4()
        correlation_id = uuid4()

        # Execute workflow with specific correlation ID
        result = await orchestrator.execute_workflow(workflow_id, correlation_id)

        # Verify correlation ID in result
        assert result["correlation_id"] == str(correlation_id)

        # Verify correlation ID in published intent
        message = mock_kafka_client.published_messages[0]
        intent = self.extract_intent_from_message(message["value"])
        assert intent["correlation_id"] == str(correlation_id)
```

### 5. Recovery Workflow Tests

Test system recovery from failures.

```python
@pytest.mark.integration
class TestComplexWorkflows:
    """Test complex multi-step workflows."""

    def test_disaster_recovery_workflow(self):
        """Test disaster recovery workflow."""
        # Step 1: Primary service fails
        primary = ModelServiceHealth.create_error(
            service_name="primary_db",
            service_type="postgresql",
            connection_string="postgresql://primary.db:5432/main",
            error_message="Database connection lost",
            error_code="CONNECTION_LOST",
        )

        assert primary.is_unhealthy()
        assert primary.requires_attention()

        # Step 2: Assess business impact
        impact = primary.get_business_impact()
        assert impact.severity == EnumImpactSeverity.CRITICAL

        # Step 3: Failover to secondary
        secondary = ModelServiceHealth.create_healthy(
            service_name="secondary_db",
            service_type="postgresql",
            connection_string="postgresql://secondary.db:5432/main",
            response_time_ms=100,
        )

        # Step 4: Verify recovery
        assert secondary.is_healthy()
        assert secondary.calculate_reliability_score() == 1.0
```

## Running Integration Tests

### Basic Commands

```bash
# Run all integration tests
poetry run pytest tests/integration/ -v

# Run with integration marker filter
poetry run pytest tests/ -m integration -v

# Run specific integration test file
poetry run pytest tests/integration/test_compute_pipeline_integration.py -v

# Run specific test class
poetry run pytest tests/integration/test_service_orchestration.py::TestServiceHealthLifecycle -v

# Run with timeout protection (recommended for CI)
poetry run pytest tests/integration/ --timeout=60 -v
```

### Debug Mode

```bash
# Disable parallelism for debugging
poetry run pytest tests/integration/test_multi_module_workflows.py -n 0 -xvs

# Run with verbose output and stop on first failure
poetry run pytest tests/integration/ -xvs --tb=long

# Run with logging output
poetry run pytest tests/integration/ -v --log-cli-level=DEBUG
```

### Performance Testing

```bash
# Run slow/performance integration tests
poetry run pytest tests/integration/ -m "integration and slow" -v

# Run with duration reporting
poetry run pytest tests/integration/ --durations=10 -v
```

## Writing New Integration Tests

### Step 1: Choose the Right Location

- **New domain?** Create `tests/integration/test_<domain>_integration.py`
- **Existing domain?** Add to existing test file
- **Mixin tests?** Place in `tests/integration/mixins/`

### Step 2: Use Fixtures from conftest.py

The `tests/integration/conftest.py` provides shared fixtures:

```python
from tests.integration.conftest import ComputeContextFactory

@pytest.fixture
def compute_execution_context_factory() -> ComputeContextFactory:
    """Factory fixture that creates a new execution context each time called.

    Returns:
        ComputeContextFactory: A callable that returns a new
            ModelComputeExecutionContext with unique IDs each time it's called.
    """
    def _create_context() -> ModelComputeExecutionContext:
        return ModelComputeExecutionContext(
            operation_id=uuid4(),
            correlation_id=uuid4(),
        )
    return _create_context
```

### Step 3: Apply Required Markers

```python
import pytest

@pytest.mark.integration  # Required - classifies test as integration
@pytest.mark.timeout(60)   # Recommended - CI protection against hangs
class TestMyFeatureIntegration:
    """Integration tests for my feature."""

    @pytest.mark.asyncio  # Required for async tests
    async def test_async_workflow(self):
        """Test async workflow."""
        pass

    @pytest.mark.slow  # Optional - marks long-running tests
    def test_performance_scenario(self):
        """Test performance under load."""
        pass
```

### Step 4: Mock External Dependencies Appropriately

For integration tests, mock only external systems (databases, message queues) not internal components:

```python
@pytest.fixture
def mock_kafka_client(self):
    """
    Create mock Kafka client with realistic behavior.
    Tracks all published messages for verification.
    """
    client = AsyncMock()
    client.published_messages = []

    async def mock_publish(topic: str, key: str, value: str):
        """Mock publish that records messages."""
        client.published_messages.append({
            "topic": topic,
            "key": key,
            "value": value,
            "timestamp": datetime.now(UTC),
        })

    client.publish = mock_publish
    return client

@pytest.fixture
def container_with_kafka(self, mock_kafka_client):
    """Create container with mocked Kafka client."""
    container = ModelONEXContainer()

    original_get_service = container.get_service

    def mock_get_service(service_name: str):
        if service_name == "kafka_client":
            return mock_kafka_client
        return original_get_service(service_name)

    container.get_service = mock_get_service
    return container
```

### Step 5: Follow Test Structure

```python
@pytest.mark.integration
@pytest.mark.timeout(60)
class TestFeatureIntegration:
    """Integration tests for [feature name].

    Tests verify:
    1. [First capability]
    2. [Second capability]
    3. [Error handling]

    Note: 60-second timeout protects against execution hangs.
    """

    def test_happy_path_scenario(self, fixture_name):
        """Test [expected behavior] when [conditions].

        Verifies that:
        - [First assertion]
        - [Second assertion]
        """
        # Arrange - Setup test data and components
        component = create_component()

        # Act - Execute the workflow
        result = component.execute_workflow()

        # Assert - Verify outcomes
        assert result.success is True
        assert result.output == expected_output

    def test_error_scenario(self, fixture_name):
        """Test error handling when [failure condition]."""
        # Arrange
        component = create_component_with_failure()

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            component.execute_workflow()

        assert exc_info.value.error_code == EnumCoreErrorCode.EXPECTED_ERROR
```

## Integration vs Unit Tests - Decision Guide

### Write a Unit Test When:

- Testing a single function or method
- Testing pure logic without external dependencies
- Testing edge cases and boundary conditions
- Testing error handling within a single component
- Fast feedback is critical

### Write an Integration Test When:

- Testing data flow between components
- Testing service coordination
- Testing complete workflow execution
- Testing event-driven patterns
- Testing state management across boundaries
- Validating real-world usage patterns

## CI Integration

### How Integration Tests Run in CI

Integration tests are included in the standard CI pipeline alongside unit tests:

1. **Parallel Execution**: Tests run across 20 parallel splits
2. **Timeout Protection**: 60-second per-test timeout prevents hangs
3. **Marker Filtering**: Use `@pytest.mark.integration` for classification
4. **Coverage**: Included in coverage metrics (60% minimum)

### CI Configuration

From `.github/workflows/test.yml`:

```yaml
- name: Run Tests (Split ${{ matrix.split }})
  run: |
    poetry run pytest tests/ \
      --splits 20 --group ${{ matrix.split }} \
      -n auto --timeout=60 --tb=short
```

### Split Timing Expectations

Integration tests typically run in the same 2-4 minute splits as unit tests. Monitor for:

- **Normal**: 2m30s - 3m30s per split
- **Warning**: 3m30s - 4m30s (review slow tests)
- **Critical**: > 4m30s (investigate immediately)

See [CI Monitoring Guide](../ci/CI_MONITORING_GUIDE.md) for detailed monitoring procedures.

## Troubleshooting

### Common Issues

#### 1. Test Hangs (No Progress)

**Symptoms**: Test doesn't complete, no output

**Solution**:
```bash
# Run with timeout protection
poetry run pytest tests/integration/ --timeout=60 -v

# Debug specific test without parallelism
poetry run pytest tests/integration/test_file.py::TestClass::test_method -n 0 -xvs
```

**Common Causes**:
- Missing `@pytest.mark.asyncio` on async tests
- Event loop issues
- Infinite loops in mocked services

#### 2. Fixture Not Found

**Symptoms**: `fixture 'fixture_name' not found`

**Solution**:
- Ensure `tests/integration/conftest.py` exists
- Check fixture scope (function/class/module/session)
- Verify fixture is imported correctly

#### 3. Import Errors

**Symptoms**: `ImportError` or `ModuleNotFoundError`

**Solution**:
```bash
# Verify package installation
poetry install

# Check import path
poetry run python -c "from tests.integration.conftest import ComputeContextFactory"
```

#### 4. Async Test Failures

**Symptoms**: `RuntimeError: Event loop is closed`

**Solution**:
```python
# Add marker to async tests
@pytest.mark.asyncio
async def test_async_operation(self):
    result = await async_function()
    assert result is not None
```

### Debug Techniques

#### Enable Verbose Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_with_logging(self):
    logger.debug("Starting test")
    # ... test code
    logger.debug(f"Result: {result}")
```

#### Capture Intermediate State

```python
def test_workflow_debug(self, capfd):
    """Test with output capture."""
    for step in workflow_steps:
        result = execute_step(step)
        print(f"Step {step.name}: {result}")  # Captured by capfd

    captured = capfd.readouterr()
    # captured.out contains all print output
```

## Related Documentation

- [Testing Guide](../guides/TESTING_GUIDE.md) - Comprehensive testing strategies
- [CI Test Strategy](CI_TEST_STRATEGY.md) - CI/CD test configuration
- [Parallel Testing](PARALLEL_TESTING.md) - Parallel test execution
- [CI Monitoring Guide](../ci/CI_MONITORING_GUIDE.md) - CI performance monitoring
- [Error Handling](../conventions/ERROR_HANDLING_BEST_PRACTICES.md) - Error handling patterns

---

**Last Updated**: 2025-12-17
**Documentation Version**: 1.0.0
**Framework Version**: omnibase_core 0.4.0
