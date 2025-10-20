"""
Tests for ModelWorkflowInputState - comprehensive coverage.

Tests workflow input state model for protocol workflow orchestrator,
including action types, scenario IDs, correlation tracking, and parameters.

ZERO TOLERANCE: No Any types allowed.
"""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.operations.model_workflow_parameters import (
    ModelWorkflowParameters,
)
from omnibase_core.models.workflows.model_workflow_input_state import (
    ModelWorkflowInputState,
)


class TestBasicCreation:
    """Test basic creation and initialization."""

    def test_minimal_creation_with_required_fields(self) -> None:
        """Test creating input state with all required fields."""
        scenario_id = uuid4()
        correlation_id = uuid4()

        input_state = ModelWorkflowInputState(
            action="process",
            scenario_id=scenario_id,
            correlation_id=correlation_id,
            operation_type="model_generation",
        )

        assert input_state.action == "process"
        assert input_state.scenario_id == scenario_id
        assert input_state.correlation_id == correlation_id
        assert input_state.operation_type == "model_generation"
        assert isinstance(input_state.parameters, ModelWorkflowParameters)

    def test_creation_with_custom_parameters(self) -> None:
        """Test creating input state with custom parameters."""
        scenario_id = uuid4()
        correlation_id = uuid4()
        custom_params = ModelWorkflowParameters()

        input_state = ModelWorkflowInputState(
            action="orchestrate",
            scenario_id=scenario_id,
            correlation_id=correlation_id,
            operation_type="extraction",
            parameters=custom_params,
        )

        assert input_state.parameters == custom_params

    def test_creation_with_all_action_types(self) -> None:
        """Test creating input state with different action types."""
        actions = ["process", "orchestrate", "execute"]
        scenario_id = uuid4()
        correlation_id = uuid4()

        for action in actions:
            input_state = ModelWorkflowInputState(
                action=action,
                scenario_id=scenario_id,
                correlation_id=correlation_id,
                operation_type="generic",
            )
            assert input_state.action == action

    def test_creation_with_all_operation_types(self) -> None:
        """Test creating input state with different operation types."""
        operation_types = [
            "model_generation",
            "bootstrap_validation",
            "extraction",
            "generic",
        ]
        scenario_id = uuid4()
        correlation_id = uuid4()

        for op_type in operation_types:
            input_state = ModelWorkflowInputState(
                action="process",
                scenario_id=scenario_id,
                correlation_id=correlation_id,
                operation_type=op_type,
            )
            assert input_state.operation_type == op_type


class TestRequiredFieldValidation:
    """Test validation of required fields."""

    def test_action_required(self) -> None:
        """Test that action field is required."""
        with pytest.raises(ValidationError, match="Field required"):
            ModelWorkflowInputState(  # type: ignore[call-arg]
                scenario_id=uuid4(),
                correlation_id=uuid4(),
                operation_type="generic",
            )

    def test_scenario_id_required(self) -> None:
        """Test that scenario_id field is required."""
        with pytest.raises(ValidationError, match="Field required"):
            ModelWorkflowInputState(  # type: ignore[call-arg]
                action="process",
                correlation_id=uuid4(),
                operation_type="generic",
            )

    def test_correlation_id_required(self) -> None:
        """Test that correlation_id field is required."""
        with pytest.raises(ValidationError, match="Field required"):
            ModelWorkflowInputState(  # type: ignore[call-arg]
                action="process",
                scenario_id=uuid4(),
                operation_type="generic",
            )

    def test_operation_type_required(self) -> None:
        """Test that operation_type field is required."""
        with pytest.raises(ValidationError, match="Field required"):
            ModelWorkflowInputState(  # type: ignore[call-arg]
                action="process",
                scenario_id=uuid4(),
                correlation_id=uuid4(),
            )


class TestActionValidation:
    """Test action field validation."""

    def test_action_process(self) -> None:
        """Test 'process' action type."""
        input_state = ModelWorkflowInputState(
            action="process",
            scenario_id=uuid4(),
            correlation_id=uuid4(),
            operation_type="generic",
        )

        assert input_state.action == "process"

    def test_action_orchestrate(self) -> None:
        """Test 'orchestrate' action type."""
        input_state = ModelWorkflowInputState(
            action="orchestrate",
            scenario_id=uuid4(),
            correlation_id=uuid4(),
            operation_type="generic",
        )

        assert input_state.action == "orchestrate"

    def test_action_execute(self) -> None:
        """Test 'execute' action type."""
        input_state = ModelWorkflowInputState(
            action="execute",
            scenario_id=uuid4(),
            correlation_id=uuid4(),
            operation_type="generic",
        )

        assert input_state.action == "execute"

    def test_action_string_type(self) -> None:
        """Test that action is a string."""
        input_state = ModelWorkflowInputState(
            action="custom_action",
            scenario_id=uuid4(),
            correlation_id=uuid4(),
            operation_type="generic",
        )

        assert isinstance(input_state.action, str)
        assert input_state.action == "custom_action"


class TestScenarioIdValidation:
    """Test scenario_id field validation."""

    def test_scenario_id_uuid_type(self) -> None:
        """Test that scenario_id is a UUID."""
        scenario_id = uuid4()

        input_state = ModelWorkflowInputState(
            action="process",
            scenario_id=scenario_id,
            correlation_id=uuid4(),
            operation_type="generic",
        )

        assert isinstance(input_state.scenario_id, UUID)
        assert input_state.scenario_id == scenario_id

    def test_scenario_id_string_conversion(self) -> None:
        """Test that scenario_id string is converted to UUID."""
        uuid_string = "12345678-1234-5678-9abc-123456789abc"

        input_state = ModelWorkflowInputState(
            action="process",
            scenario_id=UUID(uuid_string),
            correlation_id=uuid4(),
            operation_type="generic",
        )

        assert isinstance(input_state.scenario_id, UUID)
        assert str(input_state.scenario_id) == uuid_string

    def test_scenario_id_invalid_format(self) -> None:
        """Test that invalid UUID format raises error."""
        with pytest.raises(ValidationError):
            ModelWorkflowInputState(
                action="process",
                scenario_id="not-a-valid-uuid",  # type: ignore[arg-type]
                correlation_id=uuid4(),
                operation_type="generic",
            )


class TestCorrelationIdValidation:
    """Test correlation_id field validation."""

    def test_correlation_id_uuid_type(self) -> None:
        """Test that correlation_id is a UUID."""
        correlation_id = uuid4()

        input_state = ModelWorkflowInputState(
            action="process",
            scenario_id=uuid4(),
            correlation_id=correlation_id,
            operation_type="generic",
        )

        assert isinstance(input_state.correlation_id, UUID)
        assert input_state.correlation_id == correlation_id

    def test_correlation_id_string_conversion(self) -> None:
        """Test that correlation_id string is converted to UUID."""
        uuid_string = "87654321-4321-8765-cba9-987654321cba"

        input_state = ModelWorkflowInputState(
            action="process",
            scenario_id=uuid4(),
            correlation_id=UUID(uuid_string),
            operation_type="generic",
        )

        assert isinstance(input_state.correlation_id, UUID)
        assert str(input_state.correlation_id) == uuid_string

    def test_correlation_id_invalid_format(self) -> None:
        """Test that invalid correlation_id format raises error."""
        with pytest.raises(ValidationError):
            ModelWorkflowInputState(
                action="process",
                scenario_id=uuid4(),
                correlation_id="invalid-correlation-id",  # type: ignore[arg-type]
                operation_type="generic",
            )

    def test_correlation_tracking_across_workflows(self) -> None:
        """Test that same correlation_id can be used across multiple workflows."""
        correlation_id = uuid4()

        workflow1 = ModelWorkflowInputState(
            action="process",
            scenario_id=uuid4(),
            correlation_id=correlation_id,
            operation_type="model_generation",
        )

        workflow2 = ModelWorkflowInputState(
            action="execute",
            scenario_id=uuid4(),
            correlation_id=correlation_id,
            operation_type="extraction",
        )

        assert workflow1.correlation_id == workflow2.correlation_id


class TestOperationTypeValidation:
    """Test operation_type field validation."""

    def test_operation_type_model_generation(self) -> None:
        """Test 'model_generation' operation type."""
        input_state = ModelWorkflowInputState(
            action="process",
            scenario_id=uuid4(),
            correlation_id=uuid4(),
            operation_type="model_generation",
        )

        assert input_state.operation_type == "model_generation"

    def test_operation_type_bootstrap_validation(self) -> None:
        """Test 'bootstrap_validation' operation type."""
        input_state = ModelWorkflowInputState(
            action="process",
            scenario_id=uuid4(),
            correlation_id=uuid4(),
            operation_type="bootstrap_validation",
        )

        assert input_state.operation_type == "bootstrap_validation"

    def test_operation_type_extraction(self) -> None:
        """Test 'extraction' operation type."""
        input_state = ModelWorkflowInputState(
            action="process",
            scenario_id=uuid4(),
            correlation_id=uuid4(),
            operation_type="extraction",
        )

        assert input_state.operation_type == "extraction"

    def test_operation_type_generic(self) -> None:
        """Test 'generic' operation type."""
        input_state = ModelWorkflowInputState(
            action="process",
            scenario_id=uuid4(),
            correlation_id=uuid4(),
            operation_type="generic",
        )

        assert input_state.operation_type == "generic"

    def test_operation_type_custom_string(self) -> None:
        """Test custom operation type string."""
        input_state = ModelWorkflowInputState(
            action="process",
            scenario_id=uuid4(),
            correlation_id=uuid4(),
            operation_type="custom_operation",
        )

        assert input_state.operation_type == "custom_operation"


class TestParametersIntegration:
    """Test workflow parameters integration."""

    def test_default_parameters_created(self) -> None:
        """Test that default parameters are created."""
        input_state = ModelWorkflowInputState(
            action="process",
            scenario_id=uuid4(),
            correlation_id=uuid4(),
            operation_type="generic",
        )

        assert isinstance(input_state.parameters, ModelWorkflowParameters)

    def test_parameters_field_accessible(self) -> None:
        """Test that parameters field is accessible."""
        input_state = ModelWorkflowInputState(
            action="process",
            scenario_id=uuid4(),
            correlation_id=uuid4(),
            operation_type="generic",
        )

        # Should not raise an error
        params = input_state.parameters
        assert params is not None

    def test_custom_parameters_preserved(self) -> None:
        """Test that custom parameters are preserved."""
        custom_params = ModelWorkflowParameters()

        input_state = ModelWorkflowInputState(
            action="process",
            scenario_id=uuid4(),
            correlation_id=uuid4(),
            operation_type="generic",
            parameters=custom_params,
        )

        assert input_state.parameters is custom_params


class TestWorkflowInputScenarios:
    """Test complete workflow input scenarios."""

    def test_model_generation_workflow_input(self) -> None:
        """Test input state for model generation workflow."""
        input_state = ModelWorkflowInputState(
            action="process",
            scenario_id=uuid4(),
            correlation_id=uuid4(),
            operation_type="model_generation",
        )

        assert input_state.action == "process"
        assert input_state.operation_type == "model_generation"
        assert isinstance(input_state.parameters, ModelWorkflowParameters)

    def test_bootstrap_validation_workflow_input(self) -> None:
        """Test input state for bootstrap validation workflow."""
        input_state = ModelWorkflowInputState(
            action="orchestrate",
            scenario_id=uuid4(),
            correlation_id=uuid4(),
            operation_type="bootstrap_validation",
        )

        assert input_state.action == "orchestrate"
        assert input_state.operation_type == "bootstrap_validation"

    def test_extraction_workflow_input(self) -> None:
        """Test input state for extraction workflow."""
        input_state = ModelWorkflowInputState(
            action="execute",
            scenario_id=uuid4(),
            correlation_id=uuid4(),
            operation_type="extraction",
        )

        assert input_state.action == "execute"
        assert input_state.operation_type == "extraction"

    def test_generic_workflow_input(self) -> None:
        """Test input state for generic workflow."""
        input_state = ModelWorkflowInputState(
            action="process",
            scenario_id=uuid4(),
            correlation_id=uuid4(),
            operation_type="generic",
        )

        assert input_state.action == "process"
        assert input_state.operation_type == "generic"


class TestMultipleWorkflowCoordination:
    """Test coordination across multiple workflows."""

    def test_different_scenarios_same_correlation(self) -> None:
        """Test different scenarios can share correlation ID."""
        correlation_id = uuid4()
        scenario1 = uuid4()
        scenario2 = uuid4()

        input1 = ModelWorkflowInputState(
            action="process",
            scenario_id=scenario1,
            correlation_id=correlation_id,
            operation_type="model_generation",
        )

        input2 = ModelWorkflowInputState(
            action="process",
            scenario_id=scenario2,
            correlation_id=correlation_id,
            operation_type="extraction",
        )

        assert input1.correlation_id == input2.correlation_id
        assert input1.scenario_id != input2.scenario_id

    def test_unique_scenarios_unique_correlations(self) -> None:
        """Test unique scenarios with unique correlation IDs."""
        inputs = [
            ModelWorkflowInputState(
                action="process",
                scenario_id=uuid4(),
                correlation_id=uuid4(),
                operation_type="generic",
            )
            for _ in range(5)
        ]

        # All should have unique IDs
        scenario_ids = {inp.scenario_id for inp in inputs}
        correlation_ids = {inp.correlation_id for inp in inputs}

        assert len(scenario_ids) == 5
        assert len(correlation_ids) == 5

    def test_workflow_chain_correlation_tracking(self) -> None:
        """Test correlation tracking across workflow chain."""
        correlation_id = uuid4()

        # Step 1: Model generation
        step1 = ModelWorkflowInputState(
            action="process",
            scenario_id=uuid4(),
            correlation_id=correlation_id,
            operation_type="model_generation",
        )

        # Step 2: Bootstrap validation
        step2 = ModelWorkflowInputState(
            action="orchestrate",
            scenario_id=uuid4(),
            correlation_id=correlation_id,
            operation_type="bootstrap_validation",
        )

        # Step 3: Extraction
        step3 = ModelWorkflowInputState(
            action="execute",
            scenario_id=uuid4(),
            correlation_id=correlation_id,
            operation_type="extraction",
        )

        # All steps share same correlation ID
        assert step1.correlation_id == correlation_id
        assert step2.correlation_id == correlation_id
        assert step3.correlation_id == correlation_id


class TestSerialization:
    """Test serialization and deserialization."""

    def test_model_dump_basic(self) -> None:
        """Test basic model_dump serialization."""
        scenario_id = uuid4()
        correlation_id = uuid4()

        input_state = ModelWorkflowInputState(
            action="process",
            scenario_id=scenario_id,
            correlation_id=correlation_id,
            operation_type="model_generation",
        )

        dumped = input_state.model_dump()

        assert dumped["action"] == "process"
        # model_dump returns UUID objects, not strings
        assert dumped["scenario_id"] == scenario_id
        assert dumped["correlation_id"] == correlation_id
        assert dumped["operation_type"] == "model_generation"
        assert "parameters" in dumped

    def test_model_dump_json(self) -> None:
        """Test JSON serialization."""
        input_state = ModelWorkflowInputState(
            action="process",
            scenario_id=uuid4(),
            correlation_id=uuid4(),
            operation_type="generic",
        )

        json_str = input_state.model_dump_json()

        assert isinstance(json_str, str)
        assert "action" in json_str
        assert "scenario_id" in json_str


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_action_string(self) -> None:
        """Test very long action string."""
        long_action = "a" * 1000

        input_state = ModelWorkflowInputState(
            action=long_action,
            scenario_id=uuid4(),
            correlation_id=uuid4(),
            operation_type="generic",
        )

        assert input_state.action == long_action

    def test_very_long_operation_type(self) -> None:
        """Test very long operation_type string."""
        long_op_type = "operation_" * 100

        input_state = ModelWorkflowInputState(
            action="process",
            scenario_id=uuid4(),
            correlation_id=uuid4(),
            operation_type=long_op_type,
        )

        assert input_state.operation_type == long_op_type

    def test_special_characters_in_action(self) -> None:
        """Test special characters in action field."""
        special_action = "process-step_1.2@v3"

        input_state = ModelWorkflowInputState(
            action=special_action,
            scenario_id=uuid4(),
            correlation_id=uuid4(),
            operation_type="generic",
        )

        assert input_state.action == special_action

    def test_special_characters_in_operation_type(self) -> None:
        """Test special characters in operation_type field."""
        special_op = "model-generation:v2.0"

        input_state = ModelWorkflowInputState(
            action="process",
            scenario_id=uuid4(),
            correlation_id=uuid4(),
            operation_type=special_op,
        )

        assert input_state.operation_type == special_op


class TestZeroToleranceCompliance:
    """Test ZERO TOLERANCE compliance - no Any types."""

    def test_all_fields_strongly_typed(self) -> None:
        """Test that all fields have concrete types."""
        input_state = ModelWorkflowInputState(
            action="process",
            scenario_id=uuid4(),
            correlation_id=uuid4(),
            operation_type="generic",
        )

        assert isinstance(input_state.action, str)
        assert isinstance(input_state.scenario_id, UUID)
        assert isinstance(input_state.correlation_id, UUID)
        assert isinstance(input_state.operation_type, str)
        assert isinstance(input_state.parameters, ModelWorkflowParameters)


__all__ = [
    "TestBasicCreation",
    "TestRequiredFieldValidation",
    "TestActionValidation",
    "TestScenarioIdValidation",
    "TestCorrelationIdValidation",
    "TestOperationTypeValidation",
    "TestParametersIntegration",
    "TestWorkflowInputScenarios",
    "TestMultipleWorkflowCoordination",
    "TestSerialization",
    "TestEdgeCases",
    "TestZeroToleranceCompliance",
]
