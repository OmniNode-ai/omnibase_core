import pytest

# SPDX-FileCopyrightText: 2024 OmniNode Team
#
# SPDX-License-Identifier: Apache-2.0
"""
Comprehensive serialization/deserialization tests for NodeOrchestrator models.

Tests cover:
- Frozen behavior (model_config has frozen=True)
- Extra field rejection (extra="forbid")
- JSON serialization (model.model_dump_json())
- JSON deserialization (Model.model_validate_json())
- Round-trip stability: model -> JSON -> model produces equal result
- Required vs optional fields
- Field validators and constraints
- Default values correctness
- Edge cases (empty strings, None values, boundary values)

Models tested:
- ModelOrchestratorInput
- ModelOrchestratorOutput
- ModelAction
- ModelWorkflowStep
- ModelWorkflowDefinition
- ModelWorkflowDefinitionMetadata
- ModelCoordinationRules
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import ValidationError

from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.enums.enum_workflow_coordination import EnumFailureRecoveryStrategy
from omnibase_core.enums.enum_workflow_execution import (
    EnumActionType,
    EnumExecutionMode,
)
from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
from omnibase_core.models.contracts.subcontracts.model_coordination_rules import (
    ModelCoordinationRules,
)
from omnibase_core.models.contracts.subcontracts.model_execution_graph import (
    ModelExecutionGraph,
)
from omnibase_core.models.contracts.subcontracts.model_workflow_definition import (
    ModelWorkflowDefinition,
)
from omnibase_core.models.contracts.subcontracts.model_workflow_definition_metadata import (
    ModelWorkflowDefinitionMetadata,
)
from omnibase_core.models.contracts.subcontracts.model_workflow_node import (
    ModelWorkflowNode,
)
from omnibase_core.models.core.model_action_metadata import ModelActionMetadata
from omnibase_core.models.orchestrator.model_action import ModelAction
from omnibase_core.models.orchestrator.model_orchestrator_input import (
    ModelOrchestratorInput,
)
from omnibase_core.models.orchestrator.model_orchestrator_input_metadata import (
    ModelOrchestratorInputMetadata,
)
from omnibase_core.models.orchestrator.model_orchestrator_output import (
    ModelOrchestratorOutput,
)
from omnibase_core.models.orchestrator.payloads import (
    ModelOperationalActionPayload,
    create_action_payload,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


def _create_test_payload(
    action_type: EnumActionType = EnumActionType.COMPUTE,
    metadata: dict[str, Any] | None = None,
) -> ModelOperationalActionPayload:
    """Create a minimal typed payload for tests.

    This helper creates a valid ProtocolActionPayload for use in ModelAction tests.
    Uses ModelOperationalActionPayload as the default since it's the most generic.
    """
    return create_action_payload(
        action_type=action_type,
        metadata=metadata or {},
    )


# =============================================================================
# ModelOrchestratorInput Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelOrchestratorInputFrozenBehavior:
    """Tests for ModelOrchestratorInput frozen and extra=forbid."""

    def test_model_config_frozen(self) -> None:
        """Verify model_config has frozen=True."""
        config = ModelOrchestratorInput.model_config
        assert config.get("frozen") is True

    def test_model_config_extra_forbid(self) -> None:
        """Verify model_config has extra='forbid'."""
        config = ModelOrchestratorInput.model_config
        assert config.get("extra") == "forbid"

    def test_is_frozen(self) -> None:
        """Verify ModelOrchestratorInput is immutable after creation."""
        # v1.0.1 Fix 1: steps must be typed ModelWorkflowStep instances
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="test",
            step_type="compute",
        )
        model = ModelOrchestratorInput(
            workflow_id=uuid4(),
            steps=[step],
        )
        with pytest.raises(ValidationError):
            model.failure_strategy = "continue_on_error"

    def test_extra_fields_rejected(self) -> None:
        """Verify extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOrchestratorInput(
                workflow_id=uuid4(),
                steps=[],
                unknown_field="should_fail",
            )
        assert (
            "extra" in str(exc_info.value).lower()
            or "unexpected" in str(exc_info.value).lower()
        )

    def test_model_copy_for_modifications(self) -> None:
        """Verify model_copy can be used to create modified copies."""
        # v1.0.1 Fix 1: steps must be typed ModelWorkflowStep instances
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="test",
            step_type="compute",
        )
        original = ModelOrchestratorInput(
            workflow_id=uuid4(),
            steps=[step],
            max_parallel_steps=5,
        )
        modified = original.model_copy(update={"max_parallel_steps": 10})
        assert original.max_parallel_steps == 5
        assert modified.max_parallel_steps == 10


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelOrchestratorInputSerialization:
    """Tests for ModelOrchestratorInput JSON serialization."""

    def test_json_serialization(self) -> None:
        """Test model serializes to valid JSON."""
        workflow_id = uuid4()
        # v1.0.1 Fix 1: steps must be typed ModelWorkflowStep instances
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="step1",
            step_type="compute",
        )
        model = ModelOrchestratorInput(
            workflow_id=workflow_id,
            steps=[step],
            execution_mode=EnumExecutionMode.SEQUENTIAL,
            max_parallel_steps=5,
            global_timeout_ms=300000,
            failure_strategy="fail_fast",
            load_balancing_enabled=False,
            dependency_resolution_enabled=True,
            metadata=ModelOrchestratorInputMetadata(source="test"),
        )
        json_str = model.model_dump_json()
        assert isinstance(json_str, str)
        assert str(workflow_id) in json_str
        assert "step1" in json_str

    def test_json_deserialization(self) -> None:
        """Test model deserializes from valid JSON."""
        workflow_id = uuid4()
        # v1.0.1 Fix 1: steps must be typed ModelWorkflowStep instances
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="step1",
            step_type="compute",
        )
        model = ModelOrchestratorInput(
            workflow_id=workflow_id,
            steps=[step],
        )
        json_str = model.model_dump_json()
        restored = ModelOrchestratorInput.model_validate_json(json_str)
        assert restored.workflow_id == workflow_id
        assert restored.steps == model.steps

    def test_json_round_trip_stability(self) -> None:
        """Test model -> JSON -> model produces equal result."""
        workflow_id = uuid4()
        operation_id = uuid4()
        # v1.0.1 Fix 1: steps must be typed ModelWorkflowStep instances
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="step1",
            step_type="compute",
        )
        model = ModelOrchestratorInput(
            workflow_id=workflow_id,
            steps=[step],
            operation_id=operation_id,
            execution_mode=EnumExecutionMode.PARALLEL,
            max_parallel_steps=10,
            global_timeout_ms=600000,
            failure_strategy="continue_on_error",
            load_balancing_enabled=True,
            dependency_resolution_enabled=False,
            metadata=ModelOrchestratorInputMetadata(environment="test"),
        )
        json_str = model.model_dump_json()
        restored = ModelOrchestratorInput.model_validate_json(json_str)

        assert restored.workflow_id == model.workflow_id
        assert restored.operation_id == model.operation_id
        assert restored.steps == model.steps
        assert restored.execution_mode == model.execution_mode
        assert restored.max_parallel_steps == model.max_parallel_steps
        assert restored.global_timeout_ms == model.global_timeout_ms
        assert restored.failure_strategy == model.failure_strategy
        assert restored.load_balancing_enabled == model.load_balancing_enabled
        assert (
            restored.dependency_resolution_enabled
            == model.dependency_resolution_enabled
        )
        assert restored.metadata == model.metadata


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelOrchestratorInputFieldValidation:
    """Tests for ModelOrchestratorInput field validation."""

    def test_required_workflow_id(self) -> None:
        """Test workflow_id is required."""
        with pytest.raises(ValidationError):
            ModelOrchestratorInput(steps=[])

    def test_required_steps(self) -> None:
        """Test steps is required."""
        with pytest.raises(ValidationError):
            ModelOrchestratorInput(workflow_id=uuid4())

    def test_default_values(self) -> None:
        """Test default values are correct."""
        model = ModelOrchestratorInput(
            workflow_id=uuid4(),
            steps=[],
        )
        assert model.execution_mode == EnumExecutionMode.SEQUENTIAL
        assert model.max_parallel_steps == 5
        assert model.global_timeout_ms == 300000
        assert model.failure_strategy == "fail_fast"
        assert model.load_balancing_enabled is False
        assert model.dependency_resolution_enabled is True
        assert isinstance(model.metadata, ModelOrchestratorInputMetadata)
        assert model.metadata.source is None
        assert model.metadata.environment is None
        assert model.metadata.correlation_id is None
        assert model.metadata.trigger == "process"
        assert model.metadata.persist_result is False

    def test_execution_mode_enum_values(self) -> None:
        """Test all execution mode enum values work."""
        for mode in EnumExecutionMode:
            model = ModelOrchestratorInput(
                workflow_id=uuid4(),
                steps=[],
                execution_mode=mode,
            )
            assert model.execution_mode == mode

    def test_empty_steps_allowed(self) -> None:
        """Test empty steps list is allowed."""
        model = ModelOrchestratorInput(
            workflow_id=uuid4(),
            steps=[],
        )
        assert model.steps == []


# =============================================================================
# ModelOrchestratorOutput Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelOrchestratorOutputFrozenBehavior:
    """Tests for ModelOrchestratorOutput frozen and extra=forbid."""

    def test_model_config_frozen(self) -> None:
        """Verify model_config has frozen=True."""
        config = ModelOrchestratorOutput.model_config
        assert config.get("frozen") is True

    def test_model_config_extra_forbid(self) -> None:
        """Verify model_config has extra='forbid'."""
        config = ModelOrchestratorOutput.model_config
        assert config.get("extra") == "forbid"

    def test_is_frozen(self) -> None:
        """Verify ModelOrchestratorOutput is immutable after creation."""
        model = ModelOrchestratorOutput(
            execution_status="completed",
            execution_time_ms=1500,
            start_time="2025-01-01T00:00:00Z",
            end_time="2025-01-01T00:00:01Z",
        )
        with pytest.raises(ValidationError):
            model.execution_status = "failed"

    def test_extra_fields_rejected(self) -> None:
        """Verify extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOrchestratorOutput(
                execution_status="completed",
                execution_time_ms=1500,
                start_time="2025-01-01T00:00:00Z",
                end_time="2025-01-01T00:00:01Z",
                unknown_field="should_fail",
            )
        assert (
            "extra" in str(exc_info.value).lower()
            or "unexpected" in str(exc_info.value).lower()
        )

    def test_model_copy_for_modifications(self) -> None:
        """Verify model_copy can be used to create modified copies."""
        original = ModelOrchestratorOutput(
            execution_status="completed",
            execution_time_ms=1500,
            start_time="2025-01-01T00:00:00Z",
            end_time="2025-01-01T00:00:01Z",
        )
        modified = original.model_copy(update={"execution_status": "failed"})
        assert original.execution_status == "completed"
        assert modified.execution_status == "failed"


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelOrchestratorOutputSerialization:
    """Tests for ModelOrchestratorOutput JSON serialization."""

    def test_json_serialization(self) -> None:
        """Test model serializes to valid JSON."""
        model = ModelOrchestratorOutput(
            execution_status="completed",
            execution_time_ms=1500,
            start_time="2025-01-01T00:00:00Z",
            end_time="2025-01-01T00:00:01Z",
            completed_steps=["step1", "step2"],
            failed_steps=[],
            skipped_steps=["step3"],
            step_outputs={"step1": {"result": "success"}},
            final_result={"data": "output"},
            output_variables={"var1": "value1"},
            errors=[],
            metrics={"duration_avg": 500.0},
            parallel_executions=2,
            actions_emitted=[],
        )
        json_str = model.model_dump_json()
        assert isinstance(json_str, str)
        assert "completed" in json_str
        assert "step1" in json_str

    def test_json_deserialization(self) -> None:
        """Test model deserializes from valid JSON."""
        model = ModelOrchestratorOutput(
            execution_status="completed",
            execution_time_ms=1500,
            start_time="2025-01-01T00:00:00Z",
            end_time="2025-01-01T00:00:01Z",
        )
        json_str = model.model_dump_json()
        restored = ModelOrchestratorOutput.model_validate_json(json_str)
        assert restored.execution_status == model.execution_status
        assert restored.execution_time_ms == model.execution_time_ms

    def test_json_round_trip_stability(self) -> None:
        """Test model -> JSON -> model produces equal result.

        Note: When actions_emitted contains ModelAction objects, JSON round-trip
        requires special handling due to Protocol-typed payload fields.
        This test uses empty actions_emitted for clean JSON round-trip.
        Action-specific round-trip is tested in TestModelActionSerialization.
        """
        model = ModelOrchestratorOutput(
            execution_status="completed",
            execution_time_ms=1500,
            start_time="2025-01-01T00:00:00Z",
            end_time="2025-01-01T00:00:01Z",
            completed_steps=["step1"],
            failed_steps=["step2"],
            skipped_steps=["step3"],
            step_outputs={"step1": {"key": "value"}},
            final_result="done",
            output_variables={"out": 123},
            errors=[
                {"step_id": "step2", "error_type": "timeout", "message": "Timed out"}
            ],
            metrics={"total_ms": 1500.0},
            parallel_executions=1,
            actions_emitted=[],  # Empty for clean JSON round-trip
        )
        json_str = model.model_dump_json()
        restored = ModelOrchestratorOutput.model_validate_json(json_str)

        assert restored.execution_status == model.execution_status
        assert restored.execution_time_ms == model.execution_time_ms
        assert restored.completed_steps == model.completed_steps
        assert restored.failed_steps == model.failed_steps
        assert restored.skipped_steps == model.skipped_steps
        assert restored.step_outputs == model.step_outputs
        assert restored.final_result == model.final_result
        assert restored.output_variables == model.output_variables
        assert restored.errors == model.errors
        assert restored.metrics == model.metrics
        assert restored.parallel_executions == model.parallel_executions


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelOrchestratorOutputFieldValidation:
    """Tests for ModelOrchestratorOutput field validation."""

    def test_required_fields(self) -> None:
        """Test required fields raise ValidationError when missing."""
        with pytest.raises(ValidationError):
            ModelOrchestratorOutput()

    def test_default_values(self) -> None:
        """Test default values are correct."""
        model = ModelOrchestratorOutput(
            execution_status="completed",
            execution_time_ms=100,
            start_time="2025-01-01T00:00:00Z",
            end_time="2025-01-01T00:00:00Z",
        )
        assert model.completed_steps == []
        assert model.failed_steps == []
        assert model.skipped_steps == []
        assert model.step_outputs == {}
        assert model.final_result is None
        assert model.output_variables == {}
        assert model.errors == []
        assert model.metrics == {}
        assert model.parallel_executions == 0
        assert model.actions_emitted == []
        assert model.custom_outputs is None


# =============================================================================
# ModelAction Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelActionFrozenBehavior:
    """Tests for ModelAction frozen and extra=forbid."""

    def test_model_config_frozen(self) -> None:
        """Verify model_config has frozen=True."""
        config = ModelAction.model_config
        assert config.get("frozen") is True

    def test_model_config_extra_forbid(self) -> None:
        """Verify model_config has extra='forbid'."""
        config = ModelAction.model_config
        assert config.get("extra") == "forbid"

    def test_is_frozen(self) -> None:
        """Verify ModelAction is immutable after creation."""
        model = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="COMPUTE",
            payload=_create_test_payload(),
            lease_id=uuid4(),
            epoch=1,
        )
        with pytest.raises(ValidationError):
            model.epoch = 2

    def test_extra_fields_rejected(self) -> None:
        """Verify extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="COMPUTE",
                payload=_create_test_payload(),
                lease_id=uuid4(),
                epoch=1,
                unknown_field="should_fail",
            )
        assert (
            "extra" in str(exc_info.value).lower()
            or "unexpected" in str(exc_info.value).lower()
        )


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelActionSerialization:
    """Tests for ModelAction JSON serialization."""

    def test_json_serialization(self) -> None:
        """Test model serializes to valid JSON."""
        action_id = uuid4()
        lease_id = uuid4()
        # Create typed metadata
        test_metadata = ModelActionMetadata()
        test_metadata.parameters = {"env": "test"}

        model = ModelAction(
            action_id=action_id,
            action_type=EnumActionType.COMPUTE,
            target_node_type="COMPUTE",
            lease_id=lease_id,
            epoch=5,
            payload=_create_test_payload(metadata={"key": "value"}),
            dependencies=[uuid4()],
            priority=3,
            timeout_ms=60000,
            retry_count=2,
            metadata=test_metadata,
        )
        json_str = model.model_dump_json()
        assert isinstance(json_str, str)
        assert str(action_id) in json_str
        assert str(lease_id) in json_str

    def test_json_deserialization(self) -> None:
        """Test model deserializes from valid JSON.

        Note: ModelAction uses Protocol-typed payload field which cannot be validated
        directly from JSON (requires Python object for isinstance checks). We test
        dict round-trip instead of JSON round-trip for the full model.
        """
        import json

        lease_id = uuid4()
        model = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="COMPUTE",
            payload=_create_test_payload(),
            lease_id=lease_id,
            epoch=1,
        )
        # Test JSON serialization works
        json_str = model.model_dump_json()
        json_data = json.loads(json_str)

        # Verify key fields are present in JSON
        assert json_data["lease_id"] == str(lease_id)
        assert json_data["epoch"] == 1
        assert "payload" in json_data

    def test_json_round_trip_stability(self) -> None:
        """Test model -> dict -> model produces equal result.

        Note: Full JSON round-trip for ModelAction requires special handling of
        Protocol-typed payload field. We test dict round-trip with payload reconstruction.
        """
        dep_id = uuid4()
        # Create typed metadata
        source_metadata = ModelActionMetadata()
        source_metadata.parameters = {"source": "test"}

        model = ModelAction(
            action_type=EnumActionType.EFFECT,
            target_node_type="EFFECT",
            lease_id=uuid4(),
            epoch=10,
            payload=_create_test_payload(EnumActionType.EFFECT, {"data": [1, 2, 3]}),
            dependencies=[dep_id],
            priority=7,
            timeout_ms=120000,
            retry_count=5,
            metadata=source_metadata,
        )

        # Test dict round-trip: serialize to dict and back
        model_dict = model.model_dump()
        # Reconstruct payload using the factory
        model_dict["payload"] = _create_test_payload(
            EnumActionType.EFFECT, model.payload.metadata
        )
        restored = ModelAction.model_validate(model_dict)

        assert restored.action_type == model.action_type
        assert restored.target_node_type == model.target_node_type
        assert restored.epoch == model.epoch
        # Compare payload metadata for equality
        assert restored.payload.metadata == model.payload.metadata
        assert restored.dependencies == model.dependencies
        assert restored.priority == model.priority
        assert restored.timeout_ms == model.timeout_ms
        assert restored.retry_count == model.retry_count


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelActionFieldValidation:
    """Tests for ModelAction field validation."""

    def test_required_fields(self) -> None:
        """Test required fields raise ValidationError when missing."""
        with pytest.raises(ValidationError):
            ModelAction()

        with pytest.raises(ValidationError):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="COMPUTE",
                payload=_create_test_payload(),
                # Missing lease_id and epoch
            )

    def test_default_values(self) -> None:
        """Test default values are correct."""
        model = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="COMPUTE",
            payload=_create_test_payload(),
            lease_id=uuid4(),
            epoch=0,
        )
        # Payload is now a typed model, not an empty dict
        assert model.payload is not None
        assert model.dependencies == []
        assert model.priority == 1
        assert model.timeout_ms == 30000
        assert model.retry_count == 0
        assert isinstance(model.metadata, ModelActionMetadata)
        assert isinstance(model.action_id, UUID)
        assert isinstance(model.created_at, datetime)

    def test_priority_bounds(self) -> None:
        """Test priority constraints (ge=1, le=10)."""
        # Valid range
        for p in [1, 5, 10]:
            model = ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="COMPUTE",
                payload=_create_test_payload(),
                lease_id=uuid4(),
                epoch=1,
                priority=p,
            )
            assert model.priority == p

        # Too small
        with pytest.raises(ValidationError):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="COMPUTE",
                payload=_create_test_payload(),
                lease_id=uuid4(),
                epoch=1,
                priority=0,
            )

        # Too large
        with pytest.raises(ValidationError):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="COMPUTE",
                payload=_create_test_payload(),
                lease_id=uuid4(),
                epoch=1,
                priority=11,
            )

    def test_timeout_ms_bounds(self) -> None:
        """Test timeout_ms constraints (ge=100, le=300000)."""
        # Valid range
        for t in [100, 30000, 300000]:
            model = ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="COMPUTE",
                payload=_create_test_payload(),
                lease_id=uuid4(),
                epoch=1,
                timeout_ms=t,
            )
            assert model.timeout_ms == t

        # Too small
        with pytest.raises(ValidationError):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="COMPUTE",
                payload=_create_test_payload(),
                lease_id=uuid4(),
                epoch=1,
                timeout_ms=99,
            )

        # Too large
        with pytest.raises(ValidationError):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="COMPUTE",
                payload=_create_test_payload(),
                lease_id=uuid4(),
                epoch=1,
                timeout_ms=300001,
            )

    def test_retry_count_bounds(self) -> None:
        """Test retry_count constraints (ge=0, le=10)."""
        # Valid range
        for r in [0, 5, 10]:
            model = ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="COMPUTE",
                payload=_create_test_payload(),
                lease_id=uuid4(),
                epoch=1,
                retry_count=r,
            )
            assert model.retry_count == r

        # Negative
        with pytest.raises(ValidationError):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="COMPUTE",
                payload=_create_test_payload(),
                lease_id=uuid4(),
                epoch=1,
                retry_count=-1,
            )

        # Too large
        with pytest.raises(ValidationError):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="COMPUTE",
                payload=_create_test_payload(),
                lease_id=uuid4(),
                epoch=1,
                retry_count=11,
            )

    def test_epoch_bounds(self) -> None:
        """Test epoch constraints (ge=0)."""
        # Valid
        model = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="COMPUTE",
            payload=_create_test_payload(),
            lease_id=uuid4(),
            epoch=0,
        )
        assert model.epoch == 0

        # Negative
        with pytest.raises(ValidationError):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="COMPUTE",
                payload=_create_test_payload(),
                lease_id=uuid4(),
                epoch=-1,
            )

    def test_target_node_type_length_bounds(self) -> None:
        """Test target_node_type length constraints (min=1, max=100)."""
        # Valid
        model = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="COMPUTE",
            payload=_create_test_payload(),
            lease_id=uuid4(),
            epoch=1,
        )
        assert model.target_node_type == "COMPUTE"

        # Empty string
        with pytest.raises(ValidationError):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="",
                payload=_create_test_payload(),
                lease_id=uuid4(),
                epoch=1,
            )

        # Too long
        with pytest.raises(ValidationError):
            ModelAction(
                action_type=EnumActionType.COMPUTE,
                target_node_type="x" * 101,
                payload=_create_test_payload(),
                lease_id=uuid4(),
                epoch=1,
            )

    def test_all_action_type_values(self) -> None:
        """Test all action type enum values work."""
        for action_type in EnumActionType:
            model = ModelAction(
                action_type=action_type,
                target_node_type="TEST",
                payload=_create_test_payload(action_type),
                lease_id=uuid4(),
                epoch=1,
            )
            assert model.action_type == action_type


# =============================================================================
# ModelWorkflowStep Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelWorkflowStepFrozenBehavior:
    """Tests for ModelWorkflowStep frozen and extra=forbid."""

    def test_model_config_frozen(self) -> None:
        """Verify model_config has frozen=True."""
        config = ModelWorkflowStep.model_config
        assert config.get("frozen") is True

    def test_model_config_extra_forbid(self) -> None:
        """Verify model_config has extra='forbid'."""
        config = ModelWorkflowStep.model_config
        assert config.get("extra") == "forbid"

    def test_is_frozen(self) -> None:
        """Verify ModelWorkflowStep is immutable after creation."""
        model = ModelWorkflowStep(
            step_name="test_step",
            step_type="compute",
        )
        with pytest.raises(ValidationError):
            model.step_name = "modified"

    def test_extra_fields_rejected(self) -> None:
        """Verify extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelWorkflowStep(
                step_name="test_step",
                step_type="compute",
                unknown_field="should_fail",
            )
        assert (
            "extra" in str(exc_info.value).lower()
            or "unexpected" in str(exc_info.value).lower()
        )


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelWorkflowStepSerialization:
    """Tests for ModelWorkflowStep JSON serialization."""

    def test_json_serialization(self) -> None:
        """Test model serializes to valid JSON."""
        step_id = uuid4()
        model = ModelWorkflowStep(
            step_id=step_id,
            step_name="process_data",
            step_type="compute",
            timeout_ms=60000,
            retry_count=3,
            enabled=True,
            skip_on_failure=False,
            continue_on_error=False,
            error_action="stop",
            priority=100,
            order_index=1,
            depends_on=[],
            max_parallel_instances=2,
        )
        json_str = model.model_dump_json()
        assert isinstance(json_str, str)
        assert "process_data" in json_str
        assert str(step_id) in json_str

    def test_json_deserialization(self) -> None:
        """Test model deserializes from valid JSON."""
        model = ModelWorkflowStep(
            step_name="validate",
            step_type="compute",
        )
        json_str = model.model_dump_json()
        restored = ModelWorkflowStep.model_validate_json(json_str)
        assert restored.step_name == model.step_name
        assert restored.step_type == model.step_type

    def test_json_round_trip_stability(self) -> None:
        """Test model -> JSON -> model produces equal result."""
        dep_id = uuid4()
        model = ModelWorkflowStep(
            step_name="transform",
            step_type="effect",
            timeout_ms=90000,
            retry_count=5,
            enabled=False,
            skip_on_failure=True,
            continue_on_error=True,
            error_action="retry",
            max_memory_mb=1024,
            max_cpu_percent=80,
            priority=200,
            order_index=5,
            depends_on=[dep_id],
            parallel_group="batch1",
            max_parallel_instances=4,
        )
        json_str = model.model_dump_json()
        restored = ModelWorkflowStep.model_validate_json(json_str)

        assert restored.step_name == model.step_name
        assert restored.step_type == model.step_type
        assert restored.timeout_ms == model.timeout_ms
        assert restored.retry_count == model.retry_count
        assert restored.enabled == model.enabled
        assert restored.skip_on_failure == model.skip_on_failure
        assert restored.continue_on_error == model.continue_on_error
        assert restored.error_action == model.error_action
        assert restored.max_memory_mb == model.max_memory_mb
        assert restored.max_cpu_percent == model.max_cpu_percent
        assert restored.priority == model.priority
        assert restored.order_index == model.order_index
        assert restored.depends_on == model.depends_on
        assert restored.parallel_group == model.parallel_group
        assert restored.max_parallel_instances == model.max_parallel_instances


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelWorkflowStepFieldValidation:
    """Tests for ModelWorkflowStep field validation."""

    def test_required_fields(self) -> None:
        """Test required fields raise ValidationError when missing."""
        with pytest.raises(ValidationError):
            ModelWorkflowStep()

        with pytest.raises(ValidationError):
            ModelWorkflowStep(step_name="test")

    def test_default_values(self) -> None:
        """Test default values are correct."""
        model = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
        )
        assert model.timeout_ms == 30000
        assert model.retry_count == 3
        assert model.enabled is True
        assert model.skip_on_failure is False
        assert model.continue_on_error is False
        assert model.error_action == "stop"
        assert model.max_memory_mb is None
        assert model.max_cpu_percent is None
        assert model.priority == 100
        assert model.order_index == 0
        assert model.depends_on == []
        assert model.parallel_group is None
        assert model.max_parallel_instances == 1

    def test_step_type_literal_values(self) -> None:
        """Test all valid step_type literal values.

        v1.0.4 Fix 41: step_type must be compute|effect|reducer|orchestrator|custom|parallel only.
        "conditional" is NOT a valid step_type and MUST be rejected.
        """
        valid_types: list[str] = [
            "compute",
            "effect",
            "reducer",
            "orchestrator",
            "parallel",
            "custom",
        ]
        for step_type in valid_types:
            model = ModelWorkflowStep(
                step_name="test",
                step_type=step_type,
            )
            assert model.step_type == step_type

    def test_conditional_step_type_rejected(self) -> None:
        """Test that 'conditional' step_type is rejected per v1.0.4 Fix 41.

        v1.0.4 Fix 41: "conditional" is NOT a valid step_type.
        This enforces that step_type must be one of:
        compute|effect|reducer|orchestrator|custom|parallel
        """
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="test",
                step_type="conditional",  # type: ignore[arg-type]
            )

    def test_error_action_literal_values(self) -> None:
        """Test all valid error_action literal values."""
        valid_actions: list[str] = ["stop", "continue", "retry", "compensate"]
        for action in valid_actions:
            model = ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                error_action=action,
            )
            assert model.error_action == action

    def test_step_name_length_bounds(self) -> None:
        """Test step_name length constraints (min=1, max=255)."""
        # Valid
        model = ModelWorkflowStep(
            step_name="x",
            step_type="compute",
        )
        assert model.step_name == "x"

        model = ModelWorkflowStep(
            step_name="x" * 255,
            step_type="compute",
        )
        assert len(model.step_name) == 255

        # Empty string
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="",
                step_type="compute",
            )

        # Too long
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="x" * 256,
                step_type="compute",
            )

    def test_timeout_ms_bounds(self) -> None:
        """Test timeout_ms constraints (ge=100, le=300000)."""
        # Valid range
        for t in [100, 30000, 300000]:
            model = ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                timeout_ms=t,
            )
            assert model.timeout_ms == t

        # Too small
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                timeout_ms=99,
            )

        # Too large
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                timeout_ms=300001,
            )

    def test_retry_count_bounds(self) -> None:
        """Test retry_count constraints (ge=0, le=10)."""
        # Valid range
        for r in [0, 5, 10]:
            model = ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                retry_count=r,
            )
            assert model.retry_count == r

        # Negative
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                retry_count=-1,
            )

        # Too large
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                retry_count=11,
            )


# =============================================================================
# ModelWorkflowDefinitionMetadata Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelWorkflowDefinitionMetadataFrozenBehavior:
    """Tests for ModelWorkflowDefinitionMetadata frozen and extra=forbid."""

    def test_model_config_frozen(self) -> None:
        """Verify model_config has frozen=True."""
        config = ModelWorkflowDefinitionMetadata.model_config
        assert config.get("frozen") is True

    def test_model_config_extra_forbid(self) -> None:
        """Verify model_config has extra='forbid'."""
        config = ModelWorkflowDefinitionMetadata.model_config
        assert config.get("extra") == "forbid"

    def test_is_frozen(self) -> None:
        """Verify ModelWorkflowDefinitionMetadata is immutable after creation."""
        model = ModelWorkflowDefinitionMetadata(
            version=DEFAULT_VERSION,
            workflow_name="test_workflow",
            workflow_version=DEFAULT_VERSION,
            description="Test description",
        )
        with pytest.raises(ValidationError):
            model.workflow_name = "modified"

    def test_extra_fields_rejected(self) -> None:
        """Verify extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelWorkflowDefinitionMetadata(
                version=DEFAULT_VERSION,
                workflow_name="test",
                workflow_version=DEFAULT_VERSION,
                description="Test",
                unknown_field="should_fail",
            )
        assert (
            "extra" in str(exc_info.value).lower()
            or "unexpected" in str(exc_info.value).lower()
        )


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelWorkflowDefinitionMetadataSerialization:
    """Tests for ModelWorkflowDefinitionMetadata JSON serialization."""

    def test_json_serialization(self) -> None:
        """Test model serializes to valid JSON."""
        model = ModelWorkflowDefinitionMetadata(
            version=DEFAULT_VERSION,
            workflow_name="data_pipeline",
            workflow_version=ModelSemVer(major=2, minor=1, patch=0),
            description="A data processing pipeline",
            execution_mode="parallel",
            timeout_ms=900000,
        )
        json_str = model.model_dump_json()
        assert isinstance(json_str, str)
        assert "data_pipeline" in json_str
        assert "parallel" in json_str

    def test_json_deserialization(self) -> None:
        """Test model deserializes from valid JSON."""
        model = ModelWorkflowDefinitionMetadata(
            version=DEFAULT_VERSION,
            workflow_name="test",
            workflow_version=DEFAULT_VERSION,
            description="Test workflow",
        )
        json_str = model.model_dump_json()
        restored = ModelWorkflowDefinitionMetadata.model_validate_json(json_str)
        assert restored.workflow_name == model.workflow_name
        assert restored.description == model.description

    def test_json_round_trip_stability(self) -> None:
        """Test model -> JSON -> model produces equal result."""
        model = ModelWorkflowDefinitionMetadata(
            version=DEFAULT_VERSION,
            workflow_name="etl_workflow",
            workflow_version=ModelSemVer(major=1, minor=5, patch=2),
            description="Extract Transform Load",
            execution_mode="batch",
            timeout_ms=1800000,
            workflow_hash="abc123def456",
        )
        json_str = model.model_dump_json()
        restored = ModelWorkflowDefinitionMetadata.model_validate_json(json_str)

        assert restored.version == model.version
        assert restored.workflow_name == model.workflow_name
        assert restored.workflow_version == model.workflow_version
        assert restored.description == model.description
        assert restored.execution_mode == model.execution_mode
        assert restored.timeout_ms == model.timeout_ms
        assert restored.workflow_hash == model.workflow_hash


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelWorkflowDefinitionMetadataFieldValidation:
    """Tests for ModelWorkflowDefinitionMetadata field validation."""

    def test_required_fields(self) -> None:
        """Test required fields raise ValidationError when missing."""
        with pytest.raises(ValidationError):
            ModelWorkflowDefinitionMetadata()

    def test_default_values(self) -> None:
        """Test default values are correct."""
        model = ModelWorkflowDefinitionMetadata(
            version=DEFAULT_VERSION,
            workflow_name="test",
            workflow_version=DEFAULT_VERSION,
            description="Test",
        )
        assert model.execution_mode == "sequential"
        assert model.timeout_ms == 600000
        assert model.workflow_hash is None

    def test_timeout_ms_minimum(self) -> None:
        """Test timeout_ms minimum constraint (ge=1000)."""
        # Valid
        model = ModelWorkflowDefinitionMetadata(
            version=DEFAULT_VERSION,
            workflow_name="test",
            workflow_version=DEFAULT_VERSION,
            description="Test",
            timeout_ms=1000,
        )
        assert model.timeout_ms == 1000

        # Too small
        with pytest.raises(ValidationError):
            ModelWorkflowDefinitionMetadata(
                version=DEFAULT_VERSION,
                workflow_name="test",
                workflow_version=DEFAULT_VERSION,
                description="Test",
                timeout_ms=999,
            )


# =============================================================================
# ModelCoordinationRules Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelCoordinationRulesFrozenBehavior:
    """Tests for ModelCoordinationRules frozen and extra=forbid."""

    def test_model_config_frozen(self) -> None:
        """Verify model_config has frozen=True."""
        config = ModelCoordinationRules.model_config
        assert config.get("frozen") is True

    def test_model_config_extra_forbid(self) -> None:
        """Verify model_config has extra='forbid'."""
        config = ModelCoordinationRules.model_config
        assert config.get("extra") == "forbid"

    def test_is_frozen(self) -> None:
        """Verify ModelCoordinationRules is immutable after creation."""
        model = ModelCoordinationRules(version=DEFAULT_VERSION)
        with pytest.raises(ValidationError):
            model.parallel_execution_allowed = False

    def test_extra_fields_rejected(self) -> None:
        """Verify extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCoordinationRules(
                version=DEFAULT_VERSION,
                unknown_field="should_fail",
            )
        assert (
            "extra" in str(exc_info.value).lower()
            or "unexpected" in str(exc_info.value).lower()
        )


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelCoordinationRulesSerialization:
    """Tests for ModelCoordinationRules JSON serialization."""

    def test_json_serialization(self) -> None:
        """Test model serializes to valid JSON."""
        model = ModelCoordinationRules(
            version=DEFAULT_VERSION,
            synchronization_points=["checkpoint1", "checkpoint2"],
            parallel_execution_allowed=True,
            failure_recovery_strategy=EnumFailureRecoveryStrategy.RETRY,
        )
        json_str = model.model_dump_json()
        assert isinstance(json_str, str)
        assert "checkpoint1" in json_str
        assert "RETRY" in json_str

    def test_json_deserialization(self) -> None:
        """Test model deserializes from valid JSON."""
        model = ModelCoordinationRules(version=DEFAULT_VERSION)
        json_str = model.model_dump_json()
        restored = ModelCoordinationRules.model_validate_json(json_str)
        assert restored.parallel_execution_allowed == model.parallel_execution_allowed
        assert restored.failure_recovery_strategy == model.failure_recovery_strategy

    def test_json_round_trip_stability(self) -> None:
        """Test model -> JSON -> model produces equal result."""
        model = ModelCoordinationRules(
            version=DEFAULT_VERSION,
            synchronization_points=["sync1", "sync2", "sync3"],
            parallel_execution_allowed=False,
            failure_recovery_strategy=EnumFailureRecoveryStrategy.ABORT,
        )
        json_str = model.model_dump_json()
        restored = ModelCoordinationRules.model_validate_json(json_str)

        assert restored.version == model.version
        assert restored.synchronization_points == model.synchronization_points
        assert restored.parallel_execution_allowed == model.parallel_execution_allowed
        assert restored.failure_recovery_strategy == model.failure_recovery_strategy


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelCoordinationRulesFieldValidation:
    """Tests for ModelCoordinationRules field validation."""

    def test_required_version(self) -> None:
        """Test version is required."""
        with pytest.raises(ValidationError):
            ModelCoordinationRules()

    def test_default_values(self) -> None:
        """Test default values are correct."""
        model = ModelCoordinationRules(version=DEFAULT_VERSION)
        assert model.synchronization_points == []
        assert model.parallel_execution_allowed is True
        assert model.failure_recovery_strategy == EnumFailureRecoveryStrategy.RETRY

    def test_all_failure_recovery_strategies(self) -> None:
        """Test all failure recovery strategy enum values."""
        for strategy in EnumFailureRecoveryStrategy:
            model = ModelCoordinationRules(
                version=DEFAULT_VERSION,
                failure_recovery_strategy=strategy,
            )
            assert model.failure_recovery_strategy == strategy


# =============================================================================
# ModelWorkflowDefinition Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelWorkflowDefinitionFrozenBehavior:
    """Tests for ModelWorkflowDefinition frozen and extra=forbid."""

    def test_model_config_frozen(self) -> None:
        """Verify model_config has frozen=True."""
        config = ModelWorkflowDefinition.model_config
        assert config.get("frozen") is True

    def test_model_config_extra_forbid(self) -> None:
        """Verify model_config has extra='forbid'."""
        config = ModelWorkflowDefinition.model_config
        assert config.get("extra") == "forbid"

    def test_is_frozen(self) -> None:
        """Verify ModelWorkflowDefinition is immutable after creation."""
        metadata = ModelWorkflowDefinitionMetadata(
            version=DEFAULT_VERSION,
            workflow_name="test",
            workflow_version=DEFAULT_VERSION,
            description="Test",
        )
        execution_graph = ModelExecutionGraph(
            version=DEFAULT_VERSION,
            nodes=[],
        )
        model = ModelWorkflowDefinition(
            version=DEFAULT_VERSION,
            workflow_metadata=metadata,
            execution_graph=execution_graph,
        )
        with pytest.raises(ValidationError):
            model.version = ModelSemVer(major=2, minor=0, patch=0)

    def test_extra_fields_rejected(self) -> None:
        """Verify extra fields are rejected."""
        metadata = ModelWorkflowDefinitionMetadata(
            version=DEFAULT_VERSION,
            workflow_name="test",
            workflow_version=DEFAULT_VERSION,
            description="Test",
        )
        execution_graph = ModelExecutionGraph(
            version=DEFAULT_VERSION,
            nodes=[],
        )
        with pytest.raises(ValidationError) as exc_info:
            ModelWorkflowDefinition(
                version=DEFAULT_VERSION,
                workflow_metadata=metadata,
                execution_graph=execution_graph,
                unknown_field="should_fail",
            )
        assert (
            "extra" in str(exc_info.value).lower()
            or "unexpected" in str(exc_info.value).lower()
        )


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelWorkflowDefinitionSerialization:
    """Tests for ModelWorkflowDefinition JSON serialization."""

    def test_json_serialization(self) -> None:
        """Test model serializes to valid JSON."""
        metadata = ModelWorkflowDefinitionMetadata(
            version=DEFAULT_VERSION,
            workflow_name="data_pipeline",
            workflow_version=DEFAULT_VERSION,
            description="Process data",
        )
        node = ModelWorkflowNode(
            version=DEFAULT_VERSION,
            node_type=EnumNodeType.COMPUTE_GENERIC,
        )
        execution_graph = ModelExecutionGraph(
            version=DEFAULT_VERSION,
            nodes=[node],
        )
        rules = ModelCoordinationRules(version=DEFAULT_VERSION)
        model = ModelWorkflowDefinition(
            version=DEFAULT_VERSION,
            workflow_metadata=metadata,
            execution_graph=execution_graph,
            coordination_rules=rules,
        )
        json_str = model.model_dump_json()
        assert isinstance(json_str, str)
        assert "data_pipeline" in json_str

    def test_json_deserialization(self) -> None:
        """Test model deserializes from valid JSON."""
        metadata = ModelWorkflowDefinitionMetadata(
            version=DEFAULT_VERSION,
            workflow_name="test",
            workflow_version=DEFAULT_VERSION,
            description="Test",
        )
        execution_graph = ModelExecutionGraph(
            version=DEFAULT_VERSION,
            nodes=[],
        )
        model = ModelWorkflowDefinition(
            version=DEFAULT_VERSION,
            workflow_metadata=metadata,
            execution_graph=execution_graph,
        )
        json_str = model.model_dump_json()
        restored = ModelWorkflowDefinition.model_validate_json(json_str)
        assert (
            restored.workflow_metadata.workflow_name
            == model.workflow_metadata.workflow_name
        )

    def test_json_round_trip_stability(self) -> None:
        """Test model -> JSON -> model produces equal result."""
        metadata = ModelWorkflowDefinitionMetadata(
            version=DEFAULT_VERSION,
            workflow_name="complex_workflow",
            workflow_version=ModelSemVer(major=2, minor=3, patch=4),
            description="Complex workflow",
            execution_mode="parallel",
            timeout_ms=1200000,
        )
        node = ModelWorkflowNode(
            version=DEFAULT_VERSION,
            node_type=EnumNodeType.COMPUTE_GENERIC,
            node_requirements={"cpu": 4},
        )
        execution_graph = ModelExecutionGraph(
            version=DEFAULT_VERSION,
            nodes=[node],
        )
        rules = ModelCoordinationRules(
            version=DEFAULT_VERSION,
            synchronization_points=["sync1"],
            parallel_execution_allowed=True,
            failure_recovery_strategy=EnumFailureRecoveryStrategy.ABORT,
        )
        model = ModelWorkflowDefinition(
            version=DEFAULT_VERSION,
            workflow_metadata=metadata,
            execution_graph=execution_graph,
            coordination_rules=rules,
        )
        json_str = model.model_dump_json()
        restored = ModelWorkflowDefinition.model_validate_json(json_str)

        assert restored.version == model.version
        assert (
            restored.workflow_metadata.workflow_name
            == model.workflow_metadata.workflow_name
        )
        assert (
            restored.workflow_metadata.execution_mode
            == model.workflow_metadata.execution_mode
        )
        assert len(restored.execution_graph.nodes) == len(model.execution_graph.nodes)
        assert (
            restored.coordination_rules.failure_recovery_strategy
            == model.coordination_rules.failure_recovery_strategy
        )


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelWorkflowDefinitionFieldValidation:
    """Tests for ModelWorkflowDefinition field validation."""

    def test_required_fields(self) -> None:
        """Test required fields raise ValidationError when missing."""
        with pytest.raises(ValidationError):
            ModelWorkflowDefinition()

    def test_compute_workflow_hash(self) -> None:
        """Test compute_workflow_hash returns consistent hash."""
        metadata = ModelWorkflowDefinitionMetadata(
            version=DEFAULT_VERSION,
            workflow_name="test",
            workflow_version=DEFAULT_VERSION,
            description="Test",
        )
        execution_graph = ModelExecutionGraph(
            version=DEFAULT_VERSION,
            nodes=[],
        )
        model = ModelWorkflowDefinition(
            version=DEFAULT_VERSION,
            workflow_metadata=metadata,
            execution_graph=execution_graph,
        )
        hash1 = model.compute_workflow_hash()
        hash2 = model.compute_workflow_hash()
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex

    def test_with_computed_hash(self) -> None:
        """Test with_computed_hash creates new instance with hash."""
        metadata = ModelWorkflowDefinitionMetadata(
            version=DEFAULT_VERSION,
            workflow_name="test",
            workflow_version=DEFAULT_VERSION,
            description="Test",
        )
        execution_graph = ModelExecutionGraph(
            version=DEFAULT_VERSION,
            nodes=[],
        )
        model = ModelWorkflowDefinition(
            version=DEFAULT_VERSION,
            workflow_metadata=metadata,
            execution_graph=execution_graph,
        )
        assert model.workflow_metadata.workflow_hash is None

        model_with_hash = model.with_computed_hash()
        assert model_with_hash.workflow_metadata.workflow_hash is not None
        assert len(model_with_hash.workflow_metadata.workflow_hash) == 64


# =============================================================================
# Parametrized Tests Across Multiple Models
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestOrchestratorModelsFrozenBehaviorParametrized:
    """Parametrized tests for frozen behavior across multiple models."""

    @pytest.mark.parametrize(
        ("model_class", "kwargs"),
        [
            (
                ModelOrchestratorInput,
                {"workflow_id": uuid4(), "steps": []},
            ),
            (
                ModelOrchestratorOutput,
                {
                    "execution_status": "completed",
                    "execution_time_ms": 100,
                    "start_time": "2025-01-01T00:00:00Z",
                    "end_time": "2025-01-01T00:00:00Z",
                },
            ),
            (
                ModelAction,
                {
                    "action_type": EnumActionType.COMPUTE,
                    "target_node_type": "COMPUTE",
                    "lease_id": uuid4(),
                    "epoch": 1,
                },
            ),
            (
                ModelWorkflowStep,
                {"step_name": "test", "step_type": "compute"},
            ),
            (
                ModelCoordinationRules,
                {"version": DEFAULT_VERSION},
            ),
            (
                ModelWorkflowDefinitionMetadata,
                {
                    "version": DEFAULT_VERSION,
                    "workflow_name": "test",
                    "workflow_version": DEFAULT_VERSION,
                    "description": "Test",
                },
            ),
        ],
        ids=[
            "OrchestratorInput",
            "OrchestratorOutput",
            "Action",
            "WorkflowStep",
            "CoordinationRules",
            "WorkflowDefinitionMetadata",
        ],
    )
    def test_model_config_frozen(
        self, model_class: type[Any], kwargs: dict[str, Any]
    ) -> None:
        """Verify model_config has frozen=True for all models."""
        config = model_class.model_config
        assert config.get("frozen") is True, (
            f"{model_class.__name__} should have frozen=True"
        )

    @pytest.mark.parametrize(
        ("model_class", "kwargs"),
        [
            (
                ModelOrchestratorInput,
                {"workflow_id": uuid4(), "steps": []},
            ),
            (
                ModelOrchestratorOutput,
                {
                    "execution_status": "completed",
                    "execution_time_ms": 100,
                    "start_time": "2025-01-01T00:00:00Z",
                    "end_time": "2025-01-01T00:00:00Z",
                },
            ),
            (
                ModelAction,
                {
                    "action_type": EnumActionType.COMPUTE,
                    "target_node_type": "COMPUTE",
                    "lease_id": uuid4(),
                    "epoch": 1,
                },
            ),
            (
                ModelWorkflowStep,
                {"step_name": "test", "step_type": "compute"},
            ),
            (
                ModelCoordinationRules,
                {"version": DEFAULT_VERSION},
            ),
            (
                ModelWorkflowDefinitionMetadata,
                {
                    "version": DEFAULT_VERSION,
                    "workflow_name": "test",
                    "workflow_version": DEFAULT_VERSION,
                    "description": "Test",
                },
            ),
        ],
        ids=[
            "OrchestratorInput",
            "OrchestratorOutput",
            "Action",
            "WorkflowStep",
            "CoordinationRules",
            "WorkflowDefinitionMetadata",
        ],
    )
    def test_model_config_extra_forbid(
        self, model_class: type[Any], kwargs: dict[str, Any]
    ) -> None:
        """Verify model_config has extra='forbid' for all models."""
        config = model_class.model_config
        assert config.get("extra") == "forbid", (
            f"{model_class.__name__} should have extra='forbid'"
        )


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestOrchestratorModelsSerializationParametrized:
    """Parametrized tests for JSON serialization across multiple models.

    Note: ModelAction is excluded from this test because its Protocol-typed payload
    field cannot be validated from JSON (requires Python objects for isinstance checks).
    ModelAction JSON round-trip is tested separately in TestModelActionSerialization.
    """

    @pytest.mark.parametrize(
        ("model_class", "kwargs"),
        [
            (
                ModelOrchestratorInput,
                {
                    "workflow_id": uuid4(),
                    # v1.0.1 Fix 1: steps must be typed ModelWorkflowStep instances
                    "steps": [
                        ModelWorkflowStep(
                            step_id=uuid4(),
                            step_name="test",
                            step_type="compute",
                        )
                    ],
                },
            ),
            (
                ModelOrchestratorOutput,
                {
                    "execution_status": "completed",
                    "execution_time_ms": 1500,
                    "start_time": "2025-01-01T00:00:00Z",
                    "end_time": "2025-01-01T00:00:01Z",
                },
            ),
            # ModelAction excluded - Protocol-typed payload cannot be validated from JSON
            # See TestModelActionSerialization.test_json_round_trip_stability for Action tests
            (
                ModelWorkflowStep,
                {"step_name": "process", "step_type": "compute"},
            ),
            (
                ModelCoordinationRules,
                {
                    "version": DEFAULT_VERSION,
                    "synchronization_points": ["sync1"],
                },
            ),
            (
                ModelWorkflowDefinitionMetadata,
                {
                    "version": DEFAULT_VERSION,
                    "workflow_name": "pipeline",
                    "workflow_version": DEFAULT_VERSION,
                    "description": "Data pipeline",
                },
            ),
        ],
        ids=[
            "OrchestratorInput",
            "OrchestratorOutput",
            "WorkflowStep",
            "CoordinationRules",
            "WorkflowDefinitionMetadata",
        ],
    )
    def test_json_round_trip(
        self, model_class: type[Any], kwargs: dict[str, Any]
    ) -> None:
        """Test JSON round-trip for all models."""
        model = model_class(**kwargs)
        json_str = model.model_dump_json()
        assert isinstance(json_str, str)

        restored = model_class.model_validate_json(json_str)
        # Compare serialized forms to verify equality
        assert model.model_dump() == restored.model_dump()


# =============================================================================
# Edge Cases and Boundary Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestOrchestratorModelsEdgeCases:
    """Edge cases for orchestrator models."""

    def test_orchestrator_input_default_metadata(self) -> None:
        """Test OrchestratorInput with default metadata."""
        model = ModelOrchestratorInput(
            workflow_id=uuid4(),
            steps=[],
            metadata=ModelOrchestratorInputMetadata(),
        )
        assert isinstance(model.metadata, ModelOrchestratorInputMetadata)
        assert model.metadata.source is None
        assert model.metadata.environment is None
        assert model.metadata.trigger == "process"

    def test_orchestrator_output_empty_collections(self) -> None:
        """Test OrchestratorOutput with empty collections."""
        model = ModelOrchestratorOutput(
            execution_status="completed",
            execution_time_ms=0,
            start_time="2025-01-01T00:00:00Z",
            end_time="2025-01-01T00:00:00Z",
            completed_steps=[],
            failed_steps=[],
            skipped_steps=[],
            step_outputs={},
            errors=[],
            metrics={},
            actions_emitted=[],
        )
        assert model.completed_steps == []
        assert model.errors == []

    def test_action_minimum_valid_values(self) -> None:
        """Test Action with minimum valid constraint values."""
        model = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="x",  # min length 1
            payload=_create_test_payload(),
            lease_id=uuid4(),
            epoch=0,  # min 0
            priority=1,  # min 1
            timeout_ms=100,  # min 100
            retry_count=0,  # min 0
        )
        assert model.target_node_type == "x"
        assert model.epoch == 0
        assert model.priority == 1
        assert model.timeout_ms == 100
        assert model.retry_count == 0

    def test_action_maximum_valid_values(self) -> None:
        """Test Action with maximum valid constraint values."""
        model = ModelAction(
            action_type=EnumActionType.COMPUTE,
            target_node_type="x" * 100,  # max length 100
            payload=_create_test_payload(),
            lease_id=uuid4(),
            epoch=999999999,  # no upper bound
            priority=10,  # max 10
            timeout_ms=300000,  # max 300000
            retry_count=10,  # max 10
        )
        assert len(model.target_node_type) == 100
        assert model.priority == 10
        assert model.timeout_ms == 300000
        assert model.retry_count == 10

    def test_workflow_step_optional_none_values(self) -> None:
        """Test WorkflowStep with None for optional fields."""
        model = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            max_memory_mb=None,
            max_cpu_percent=None,
            parallel_group=None,
        )
        assert model.max_memory_mb is None
        assert model.max_cpu_percent is None
        assert model.parallel_group is None

    def test_workflow_step_resource_bounds(self) -> None:
        """Test WorkflowStep resource constraint bounds."""
        # Valid max_memory_mb
        model = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            max_memory_mb=32768,  # max
        )
        assert model.max_memory_mb == 32768

        # Too large
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                max_memory_mb=32769,
            )

        # Valid max_cpu_percent
        model = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            max_cpu_percent=100,  # max
        )
        assert model.max_cpu_percent == 100

        # Too large
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                max_cpu_percent=101,
            )

    def test_coordination_rules_empty_sync_points(self) -> None:
        """Test CoordinationRules with empty synchronization points."""
        model = ModelCoordinationRules(
            version=DEFAULT_VERSION,
            synchronization_points=[],
        )
        assert model.synchronization_points == []

    def test_workflow_definition_metadata_hash_optional(self) -> None:
        """Test WorkflowDefinitionMetadata with optional hash."""
        model = ModelWorkflowDefinitionMetadata(
            version=DEFAULT_VERSION,
            workflow_name="test",
            workflow_version=DEFAULT_VERSION,
            description="Test",
            workflow_hash=None,
        )
        assert model.workflow_hash is None

        model_with_hash = ModelWorkflowDefinitionMetadata(
            version=DEFAULT_VERSION,
            workflow_name="test",
            workflow_version=DEFAULT_VERSION,
            description="Test",
            workflow_hash="a" * 64,
        )
        assert model_with_hash.workflow_hash == "a" * 64


# =============================================================================
# ModelExecutionGraph and ModelWorkflowNode Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelExecutionGraphFrozenBehavior:
    """Tests for ModelExecutionGraph frozen and extra=forbid."""

    def test_model_config_frozen(self) -> None:
        """Verify model_config has frozen=True."""
        config = ModelExecutionGraph.model_config
        assert config.get("frozen") is True

    def test_model_config_extra_forbid(self) -> None:
        """Verify model_config has extra='forbid'."""
        config = ModelExecutionGraph.model_config
        assert config.get("extra") == "forbid"

    def test_is_frozen(self) -> None:
        """Verify ModelExecutionGraph is immutable after creation."""
        model = ModelExecutionGraph(
            version=DEFAULT_VERSION,
            nodes=[],
        )
        with pytest.raises(ValidationError):
            model.nodes = []

    def test_extra_fields_rejected(self) -> None:
        """Verify extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionGraph(
                version=DEFAULT_VERSION,
                nodes=[],
                unknown_field="should_fail",
            )
        assert (
            "extra" in str(exc_info.value).lower()
            or "unexpected" in str(exc_info.value).lower()
        )


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelExecutionGraphSerialization:
    """Tests for ModelExecutionGraph JSON serialization."""

    def test_json_round_trip_stability(self) -> None:
        """Test model -> JSON -> model produces equal result."""
        node = ModelWorkflowNode(
            version=DEFAULT_VERSION,
            node_type=EnumNodeType.COMPUTE_GENERIC,
            node_requirements={"cpu": 2},
        )
        model = ModelExecutionGraph(
            version=DEFAULT_VERSION,
            nodes=[node],
        )
        json_str = model.model_dump_json()
        restored = ModelExecutionGraph.model_validate_json(json_str)

        assert restored.version == model.version
        assert len(restored.nodes) == 1


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelWorkflowNodeFrozenBehavior:
    """Tests for ModelWorkflowNode frozen and extra=forbid."""

    def test_model_config_frozen(self) -> None:
        """Verify model_config has frozen=True."""
        config = ModelWorkflowNode.model_config
        assert config.get("frozen") is True

    def test_model_config_extra_forbid(self) -> None:
        """Verify model_config has extra='forbid'."""
        config = ModelWorkflowNode.model_config
        assert config.get("extra") == "forbid"

    def test_is_frozen(self) -> None:
        """Verify ModelWorkflowNode is immutable after creation."""
        model = ModelWorkflowNode(
            version=DEFAULT_VERSION,
            node_type=EnumNodeType.COMPUTE_GENERIC,
        )
        with pytest.raises(ValidationError):
            model.node_type = EnumNodeType.TRANSFORMER

    def test_extra_fields_rejected(self) -> None:
        """Verify extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelWorkflowNode(
                version=DEFAULT_VERSION,
                node_type=EnumNodeType.COMPUTE_GENERIC,
                unknown_field="should_fail",
            )
        assert (
            "extra" in str(exc_info.value).lower()
            or "unexpected" in str(exc_info.value).lower()
        )


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelWorkflowNodeSerialization:
    """Tests for ModelWorkflowNode JSON serialization."""

    def test_json_round_trip_stability(self) -> None:
        """Test model -> JSON -> model produces equal result."""
        dep_id = uuid4()
        model = ModelWorkflowNode(
            version=DEFAULT_VERSION,
            node_type=EnumNodeType.COMPUTE_GENERIC,
            node_requirements={"memory_mb": 1024},
            dependencies=[dep_id],
        )
        json_str = model.model_dump_json()
        restored = ModelWorkflowNode.model_validate_json(json_str)

        assert restored.version == model.version
        assert restored.node_type == model.node_type
        assert restored.node_requirements == model.node_requirements
        assert restored.dependencies == model.dependencies
