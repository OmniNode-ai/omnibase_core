> **Navigation**: [Home](../INDEX.md) > Testing > Integration Testing Guide

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
├── test_reducer_integration.py              # NodeReducer FSM state transitions
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
uv run pytest tests/integration/ -v

# Run with integration marker filter
uv run pytest tests/ -m integration -v

# Run specific integration test file
uv run pytest tests/integration/test_compute_pipeline_integration.py -v

# Run specific test class
uv run pytest tests/integration/test_service_orchestration.py::TestServiceHealthLifecycle -v

# Run with timeout protection (recommended for CI)
uv run pytest tests/integration/ --timeout=60 -v
```

### Debug Mode

```bash
# Disable parallelism for debugging
uv run pytest tests/integration/test_multi_module_workflows.py -n 0 -xvs

# Run with verbose output and stop on first failure
uv run pytest tests/integration/ -xvs --tb=long

# Run with logging output
uv run pytest tests/integration/ -v --log-cli-level=DEBUG
```

### Performance Testing

```bash
# Run slow/performance integration tests
uv run pytest tests/integration/ -m "integration and slow" -v

# Run with duration reporting
uv run pytest tests/integration/ --durations=10 -v
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

### NodeReducer Integration Test Example

NodeReducer tests verify FSM-driven state transitions with real data flows. The key components are:

1. **FSM Contract Factory** - Creates test FSM configurations
2. **TestableNodeReducer** - A test implementation that accepts an FSM contract
3. **State Transition Verification** - Validates FSM state changes and output metadata

#### Complete Working Example

```python
"""Integration tests for NodeReducer FSM state transitions."""

import asyncio
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_reducer_types import EnumReductionType
from omnibase_core.models.common.model_reducer_metadata import ModelReducerMetadata
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.subcontracts.model_fsm_state_definition import (
    ModelFSMStateDefinition,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_state_transition import (
    ModelFSMStateTransition,
)
from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.reducer.model_reducer_input import ModelReducerInput
from omnibase_core.models.reducer.model_reducer_output import ModelReducerOutput
from omnibase_core.nodes.node_reducer import NodeReducer

# Version for test contracts
V1_0_0 = ModelSemVer(major=1, minor=0, patch=0)


def create_test_fsm_contract(
    *,
    name: str = "test_fsm",
    initial_state: str = "idle",
    states: list[dict[str, Any]] | None = None,
    transitions: list[dict[str, Any]] | None = None,
) -> ModelFSMSubcontract:
    """Factory to create FSM contracts for testing.

    Args:
        name: State machine name
        initial_state: Initial state name
        states: List of state definition dicts (optional, defaults provided)
        transitions: List of transition definition dicts (optional, defaults provided)

    Returns:
        ModelFSMSubcontract configured for testing
    """
    if states is None:
        states = [
            {
                "version": V1_0_0,
                "state_name": "idle",
                "state_type": "operational",
                "description": "Initial idle state",
                "is_terminal": False,
                "is_recoverable": True,
            },
            {
                "version": V1_0_0,
                "state_name": "processing",
                "state_type": "operational",
                "description": "Processing data",
                "is_terminal": False,
                "is_recoverable": True,
            },
            {
                "version": V1_0_0,
                "state_name": "completed",
                "state_type": "terminal",
                "description": "Processing completed",
                "is_terminal": True,
                "is_recoverable": False,
            },
        ]

    if transitions is None:
        transitions = [
            {
                "version": V1_0_0,
                "transition_name": "start_processing",
                "from_state": "idle",
                "to_state": "processing",
                "trigger": "start",
            },
            {
                "version": V1_0_0,
                "transition_name": "complete_processing",
                "from_state": "processing",
                "to_state": "completed",
                "trigger": "complete",
            },
        ]

    return ModelFSMSubcontract(
        version=V1_0_0,
        state_machine_name=name,
        state_machine_version=V1_0_0,
        description=f"Test FSM: {name}",
        states=[ModelFSMStateDefinition(**s) for s in states],
        initial_state=initial_state,
        transitions=[ModelFSMStateTransition(**t) for t in transitions],
        terminal_states=[],
        error_states=[],
    )


class TestableNodeReducer(NodeReducer[Any, Any]):
    """Test implementation of NodeReducer that accepts an FSM contract directly."""

    def __init__(
        self, container: ModelONEXContainer, fsm_contract: ModelFSMSubcontract
    ) -> None:
        """Initialize with explicit FSM contract.

        Args:
            container: ONEX container for dependency injection
            fsm_contract: FSM subcontract to use for state machine
        """
        # Call NodeCoreBase.__init__ directly (bypass NodeReducer contract loading)
        super(NodeReducer, self).__init__(container)

        # Set FSM contract directly
        self.fsm_contract = fsm_contract

        # Initialize FSM state
        self.initialize_fsm_state(fsm_contract, context={})


# Type alias for reducer factory callable
ReducerWithContractFactory = Callable[[ModelFSMSubcontract], NodeReducer[Any, Any]]


@pytest.fixture
def mock_container() -> ModelONEXContainer:
    """Create a mock ONEX container for testing."""
    container = MagicMock(spec=ModelONEXContainer)
    container.get_service = MagicMock(return_value=MagicMock())
    return container


@pytest.fixture
def reducer_with_contract_factory(
    mock_container: ModelONEXContainer,
) -> ReducerWithContractFactory:
    """Factory fixture for creating NodeReducer instances with custom FSM contracts."""

    def _create_reducer(fsm_contract: ModelFSMSubcontract) -> NodeReducer[Any, Any]:
        return TestableNodeReducer(mock_container, fsm_contract)

    return _create_reducer


@pytest.mark.integration
@pytest.mark.timeout(60)
class TestReducerIntegration:
    """Integration tests for NodeReducer FSM state transitions."""

    def test_happy_path_state_transition(
        self, reducer_with_contract_factory: ReducerWithContractFactory
    ) -> None:
        """Test basic FSM state transition from idle to processing.

        Verifies:
        - ModelReducerInput is processed correctly
        - FSM state transitions from idle -> processing
        - ModelReducerOutput contains correct metadata
        - State history is tracked
        """
        # Arrange: Create FSM contract and reducer
        fsm_contract = create_test_fsm_contract(name="happy_path_fsm")
        reducer = reducer_with_contract_factory(fsm_contract)

        # Verify initial state
        assert reducer.get_current_state() == "idle"
        assert reducer.get_state_history() == []

        # Create input with trigger to transition idle -> processing
        input_data: ModelReducerInput[dict[str, str]] = ModelReducerInput(
            data=[{"key": "value1"}, {"key": "value2"}],
            reduction_type=EnumReductionType.AGGREGATE,
            metadata=ModelReducerMetadata(
                trigger="start",
                source="integration_test",
                correlation_id=str(uuid4()),
            ),
        )

        # Act: Process the input
        result = asyncio.run(reducer.process(input_data))

        # Assert: Verify output structure
        assert isinstance(result, ModelReducerOutput)
        assert result.operation_id == input_data.operation_id
        assert result.reduction_type == EnumReductionType.AGGREGATE

        # Assert: Verify FSM state transitioned
        assert reducer.get_current_state() == "processing"
        assert reducer.get_state_history() == ["idle"]

        # Assert: Verify output metadata contains FSM info
        assert result.metadata.model_extra.get("fsm_state") == "processing"
        assert result.metadata.model_extra.get("fsm_success") is True

    def test_invalid_transition_raises_error(
        self, reducer_with_contract_factory: ReducerWithContractFactory
    ) -> None:
        """Test that invalid FSM trigger raises ModelOnexError.

        Verifies:
        - Invalid trigger results in ModelOnexError
        - FSM state remains unchanged after failed transition
        """
        # Arrange
        fsm_contract = create_test_fsm_contract(name="error_path_fsm")
        reducer = reducer_with_contract_factory(fsm_contract)
        initial_state = reducer.get_current_state()

        # Create input with invalid trigger (no transition from idle with this trigger)
        input_data: ModelReducerInput[str] = ModelReducerInput(
            data=["item1", "item2"],
            reduction_type=EnumReductionType.FOLD,
            metadata=ModelReducerMetadata(
                trigger="invalid_trigger",
                source="error_test",
            ),
        )

        # Act & Assert: Expect ModelOnexError
        with pytest.raises(ModelOnexError) as exc_info:
            asyncio.run(reducer.process(input_data))

        # Verify error contains relevant info
        error = exc_info.value
        assert "no transition" in error.message.lower() or "invalid" in error.message.lower()

        # Verify FSM state unchanged
        assert reducer.get_current_state() == initial_state
```

#### Key Testing Patterns

**1. FSM Contract Factory**: Use `create_test_fsm_contract()` to create minimal FSM configurations with default states and transitions. Override specific parameters as needed.

**2. TestableNodeReducer**: Extends `NodeReducer` to accept FSM contracts directly in the constructor, bypassing the normal contract loading mechanism.

**3. Fixture Factory Pattern**: The `reducer_with_contract_factory` fixture returns a callable that creates fresh reducer instances, allowing each test to have isolated state.

**4. State Verification**: Always verify:
   - Initial state before transition
   - Current state after transition
   - State history accumulation
   - Output metadata containing FSM state info (`fsm_state`, `fsm_success`)

**5. Error Path Testing**: Invalid triggers should raise `ModelOnexError` with descriptive messages, and the FSM state should remain unchanged.

For the complete test suite with multi-step workflows, event-driven patterns, and recovery scenarios, see `tests/integration/test_reducer_integration.py`.

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
    uv run pytest tests/ \
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
uv run pytest tests/integration/ --timeout=60 -v

# Debug specific test without parallelism
uv run pytest tests/integration/test_file.py::TestClass::test_method -n 0 -xvs
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
uv sync

# Check import path
uv run python -c "from tests.integration.conftest import ComputeContextFactory"
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
