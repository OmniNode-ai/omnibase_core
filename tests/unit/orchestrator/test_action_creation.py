"""
Unit tests for action creation in workflow execution.

Tests the _create_action_for_step function and related action creation logic
in utils/workflow_executor.py for OMN-657.

Test Coverage:
- Priority clamping: step priority (1-1000) -> action priority (1-10)
- Dependency mapping: step dependencies -> action dependencies
- Action ID generation: UUID format and uniqueness
- Action type mapping: step_type -> EnumActionType
- Action field propagation: timeout, retry_count, metadata, payload
"""

from datetime import datetime
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_workflow_execution import EnumActionType
from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
from omnibase_core.models.orchestrator.model_action import ModelAction
from omnibase_core.utils.workflow_executor import _create_action_for_step


@pytest.mark.unit
class TestPriorityClamping:
    """Test priority clamping from step priority (1-1000) to action priority (1-10)."""

    @pytest.mark.parametrize(
        ("step_priority", "expected_action_priority"),
        [
            # Direct mappings for low values
            (1, 1),
            (2, 2),
            (5, 5),
            (10, 10),
            # Clamped values for higher priorities
            (11, 10),
            (50, 10),
            (100, 10),
            (500, 10),
            (1000, 10),
        ],
    )
    def test_priority_clamping_formula(
        self, step_priority: int, expected_action_priority: int
    ) -> None:
        """Test that step priority is clamped to action priority range (1-10).

        The clamping formula is: action_priority = min(step.priority, 10)

        Step priority (1-1000) is an authoring-time hint for workflow authors.
        Action priority (1-10) is an execution-time constraint for node scheduling.
        """
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="test_step",
            step_type="compute",
            priority=step_priority,
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert action.priority == expected_action_priority

    def test_priority_clamps_at_boundary(self) -> None:
        """Test that priority at boundary value (10) is preserved."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="boundary_step",
            step_type="compute",
            priority=10,
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert action.priority == 10

    def test_priority_just_above_boundary(self) -> None:
        """Test that priority just above boundary (11) is clamped to 10."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="above_boundary_step",
            step_type="compute",
            priority=11,
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert action.priority == 10

    def test_priority_at_maximum_step_priority(self) -> None:
        """Test that maximum step priority (1000) clamps to 10."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="max_priority_step",
            step_type="compute",
            priority=1000,
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert action.priority == 10

    def test_priority_at_minimum_step_priority(self) -> None:
        """Test that minimum step priority (1) maps to 1."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="min_priority_step",
            step_type="compute",
            priority=1,
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert action.priority == 1

    def test_default_priority_value(self) -> None:
        """Test that default step priority (100) is clamped correctly."""
        # ModelWorkflowStep has default priority=100
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="default_priority_step",
            step_type="compute",
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        # Default priority 100 should be clamped to 10
        assert action.priority == 10


@pytest.mark.unit
class TestDependencyMapping:
    """Test that step dependencies map correctly to action dependencies."""

    def test_empty_dependencies(self) -> None:
        """Test that empty step dependencies produce empty action dependencies."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="no_deps_step",
            step_type="compute",
            depends_on=[],
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert action.dependencies == []

    def test_single_dependency(self) -> None:
        """Test that single step dependency maps to action dependency."""
        dep_id = uuid4()
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="single_dep_step",
            step_type="compute",
            depends_on=[dep_id],
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert len(action.dependencies) == 1
        assert action.dependencies[0] == dep_id

    def test_multiple_dependencies(self) -> None:
        """Test that multiple step dependencies all map to action dependencies."""
        dep_ids = [uuid4(), uuid4(), uuid4()]
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="multi_dep_step",
            step_type="compute",
            depends_on=dep_ids,
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert len(action.dependencies) == 3
        for dep_id in dep_ids:
            assert dep_id in action.dependencies

    def test_dependency_order_preserved(self) -> None:
        """Test that dependency order is preserved in mapping."""
        dep_ids = [uuid4(), uuid4(), uuid4()]
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="ordered_deps_step",
            step_type="compute",
            depends_on=dep_ids,
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        # Verify order is preserved
        assert action.dependencies == dep_ids

    def test_dependencies_are_uuids(self) -> None:
        """Test that action dependencies are UUID objects."""
        dep_id = uuid4()
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="uuid_dep_step",
            step_type="compute",
            depends_on=[dep_id],
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert all(isinstance(dep, UUID) for dep in action.dependencies)


@pytest.mark.unit
class TestActionIdGeneration:
    """Test action_id generation for uniqueness and format."""

    def test_action_id_is_generated(self) -> None:
        """Test that action_id is auto-generated."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="generated_id_step",
            step_type="compute",
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert action.action_id is not None

    def test_action_id_is_uuid(self) -> None:
        """Test that action_id is a valid UUID object."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="uuid_format_step",
            step_type="compute",
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert isinstance(action.action_id, UUID)

    def test_action_id_unique_per_action(self) -> None:
        """Test that each action gets a unique action_id."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="unique_id_step",
            step_type="compute",
        )
        workflow_id = uuid4()

        # Create multiple actions from the same step
        actions = [_create_action_for_step(step, workflow_id)[0] for _ in range(10)]

        # All action_ids should be unique
        action_ids = [action.action_id for action in actions]
        assert len(action_ids) == len(set(action_ids))

    def test_action_id_differs_from_step_id(self) -> None:
        """Test that action_id is different from step_id."""
        step_id = uuid4()
        step = ModelWorkflowStep(
            step_id=step_id,
            step_name="different_ids_step",
            step_type="compute",
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert action.action_id != step_id

    def test_action_id_format_consistency(self) -> None:
        """Test that action_id format is consistent (UUID v4)."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="format_step",
            step_type="compute",
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        # UUID string representation should be 36 characters (8-4-4-4-12)
        uuid_str = str(action.action_id)
        assert len(uuid_str) == 36
        assert uuid_str.count("-") == 4


@pytest.mark.unit
class TestActionTypeMapping:
    """Test step_type to EnumActionType mapping."""

    @pytest.mark.parametrize(
        ("step_type", "expected_action_type"),
        [
            ("compute", EnumActionType.COMPUTE),
            ("effect", EnumActionType.EFFECT),
            ("reducer", EnumActionType.REDUCE),
            ("orchestrator", EnumActionType.ORCHESTRATE),
            ("custom", EnumActionType.CUSTOM),
        ],
    )
    def test_step_type_to_action_type_mapping(
        self, step_type: str, expected_action_type: EnumActionType
    ) -> None:
        """Test that step_type correctly maps to EnumActionType."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name=f"{step_type}_step",
            step_type=step_type,
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert action.action_type == expected_action_type

    def test_compute_step_type_mapping(self) -> None:
        """Test that compute step type maps to COMPUTE action type."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="compute_step",
            step_type="compute",
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert action.action_type == EnumActionType.COMPUTE

    def test_effect_step_type_mapping(self) -> None:
        """Test that effect step type maps to EFFECT action type."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="effect_step",
            step_type="effect",
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert action.action_type == EnumActionType.EFFECT

    def test_reducer_step_type_mapping(self) -> None:
        """Test that reducer step type maps to REDUCE action type."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="reducer_step",
            step_type="reducer",
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert action.action_type == EnumActionType.REDUCE

    def test_orchestrator_step_type_mapping(self) -> None:
        """Test that orchestrator step type maps to ORCHESTRATE action type."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="orchestrator_step",
            step_type="orchestrator",
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert action.action_type == EnumActionType.ORCHESTRATE

    def test_custom_step_type_mapping(self) -> None:
        """Test that custom step type maps to CUSTOM action type."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="custom_step",
            step_type="custom",
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert action.action_type == EnumActionType.CUSTOM

    def test_conditional_step_type_rejected(self) -> None:
        """Test that conditional step type is rejected per v1.0.4 Fix 41.

        v1.0.4 Normative: step_type="conditional" MUST raise validation error.
        Conditional nodes are reserved for v1.1.
        """
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            ModelWorkflowStep(
                step_id=uuid4(),
                step_name="conditional_step",
                step_type="conditional",  # type: ignore[arg-type]
            )

        # Verify error mentions the invalid step_type
        assert "step_type" in str(exc_info.value)

    def test_parallel_step_type_fallback(self) -> None:
        """Test that parallel step type falls back to CUSTOM action type."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="parallel_step",
            step_type="parallel",
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        # Unknown types fall back to CUSTOM
        assert action.action_type == EnumActionType.CUSTOM


@pytest.mark.unit
class TestTargetNodeTypeMapping:
    """Test step_type to target_node_type mapping."""

    @pytest.mark.parametrize(
        ("step_type", "expected_target_node_type"),
        [
            ("compute", "NodeCompute"),
            ("effect", "NodeEffect"),
            ("reducer", "NodeReducer"),
            ("orchestrator", "NodeOrchestrator"),
            ("custom", "NodeCustom"),
        ],
    )
    def test_target_node_type_mapping(
        self, step_type: str, expected_target_node_type: str
    ) -> None:
        """Test that step_type correctly maps to target_node_type."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name=f"{step_type}_step",
            step_type=step_type,
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert action.target_node_type == expected_target_node_type

    def test_unknown_step_type_rejected_at_validation(self) -> None:
        """Test that unknown step types are rejected at validation time.

        v1.0.4 Fix 41: step_type must be compute|effect|reducer|orchestrator|custom|parallel.
        Invalid step types are rejected during model validation, not during action creation.
        This ensures all step types that reach action creation are valid and mapped.
        """
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_id=uuid4(),
                step_name="invalid_step",
                step_type="invalid_type",  # type: ignore[arg-type]
            )

    def test_parallel_step_type_maps_to_custom(self) -> None:
        """Test that parallel step type maps to NodeCustom target node type."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="parallel_step",
            step_type="parallel",
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        # parallel step type should map to NodeCustom
        assert action.target_node_type == "NodeCustom"


@pytest.mark.unit
class TestActionFieldPropagation:
    """Test that step fields are correctly propagated to action fields."""

    def test_timeout_ms_propagation(self) -> None:
        """Test that step timeout_ms is propagated to action."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="timeout_step",
            step_type="compute",
            timeout_ms=60000,
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert action.timeout_ms == 60000

    def test_default_timeout_ms(self) -> None:
        """Test that default timeout_ms is used when not specified."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="default_timeout_step",
            step_type="compute",
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        # Default is 30000ms
        assert action.timeout_ms == 30000

    def test_retry_count_propagation(self) -> None:
        """Test that step retry_count is propagated to action."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="retry_step",
            step_type="compute",
            retry_count=5,
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert action.retry_count == 5

    def test_default_retry_count(self) -> None:
        """Test that default retry_count is used from step."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="default_retry_step",
            step_type="compute",
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        # Step default is 3
        assert action.retry_count == 3

    def test_metadata_contains_step_name(self) -> None:
        """Test that action metadata contains step_name."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="metadata_step",
            step_type="compute",
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert "step_name" in action.metadata.parameters
        assert action.metadata.parameters["step_name"] == "metadata_step"

    def test_metadata_contains_correlation_id(self) -> None:
        """Test that action metadata contains correlation_id."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="correlation_step",
            step_type="compute",
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert "correlation_id" in action.metadata.parameters
        # Correlation ID should be string representation of UUID
        assert action.metadata.parameters["correlation_id"] == str(step.correlation_id)

    def test_lease_id_is_generated(self) -> None:
        """Test that lease_id is auto-generated for each action."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="lease_step",
            step_type="compute",
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert action.lease_id is not None
        assert isinstance(action.lease_id, UUID)

    def test_epoch_is_zero(self) -> None:
        """Test that epoch starts at 0 for new actions."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="epoch_step",
            step_type="compute",
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert action.epoch == 0

    def test_created_at_is_set(self) -> None:
        """Test that created_at timestamp is set."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="timestamp_step",
            step_type="compute",
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert action.created_at is not None
        assert isinstance(action.created_at, datetime)


@pytest.mark.unit
class TestActionPayload:
    """Test action payload construction and JSON serialization."""

    def test_payload_contains_workflow_id(self) -> None:
        """Test that payload contains workflow_id as string."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="workflow_payload_step",
            step_type="compute",
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert "workflow_id" in action.payload.metadata
        assert action.payload.metadata["workflow_id"] == str(workflow_id)

    def test_payload_contains_step_id(self) -> None:
        """Test that payload contains step_id as string."""
        step_id = uuid4()
        step = ModelWorkflowStep(
            step_id=step_id,
            step_name="step_payload_step",
            step_type="compute",
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert "step_id" in action.payload.metadata
        assert action.payload.metadata["step_id"] == str(step_id)

    def test_payload_contains_step_name(self) -> None:
        """Test that payload contains step_name."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="name_payload_step",
            step_type="compute",
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert "step_name" in action.payload.metadata
        assert action.payload.metadata["step_name"] == "name_payload_step"

    def test_payload_is_json_serializable(self) -> None:
        """Test that payload can be serialized to JSON."""
        import json

        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="json_payload_step",
            step_type="compute",
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        # Should not raise - use model_dump for typed payloads
        payload_dict = action.payload.model_dump(mode="json")
        json_str = json.dumps(payload_dict)
        assert isinstance(json_str, str)

        # Should contain expected metadata
        parsed = json.loads(json_str)
        assert "metadata" in parsed
        assert parsed["metadata"]["step_name"] == "json_payload_step"


@pytest.mark.unit
class TestActionModelIntegrity:
    """Test that created actions are valid ModelAction instances."""

    def test_action_is_model_action_instance(self) -> None:
        """Test that returned object is a ModelAction instance."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="model_step",
            step_type="compute",
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert isinstance(action, ModelAction)

    def test_action_is_frozen(self) -> None:
        """Test that action is immutable (frozen)."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="frozen_step",
            step_type="compute",
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        # Attempting to modify should raise ValidationError for frozen models
        with pytest.raises(Exception):
            action.priority = 5

    def test_action_can_be_serialized(self) -> None:
        """Test that action can be serialized to dict."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="serialize_step",
            step_type="compute",
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        # Should not raise
        action_dict = action.model_dump()
        assert isinstance(action_dict, dict)
        assert "action_id" in action_dict
        assert "action_type" in action_dict
        assert "payload" in action_dict

    def test_action_can_be_copied_with_modifications(self) -> None:
        """Test that frozen action can be copied with modifications."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="copy_step",
            step_type="compute",
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)
        original_priority = action.priority

        # Create modified copy
        new_action = action.model_copy(update={"priority": 5})

        # Original unchanged
        assert action.priority == original_priority
        # New has updated value
        assert new_action.priority == 5


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_long_step_name(self) -> None:
        """Test action creation with maximum length step name."""
        long_name = "a" * 200  # Max length for step_name
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name=long_name,
            step_type="compute",
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert action.payload.metadata["step_name"] == long_name

    def test_minimum_timeout(self) -> None:
        """Test action creation with minimum timeout_ms."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="min_timeout_step",
            step_type="compute",
            timeout_ms=100,  # Minimum value
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert action.timeout_ms == 100

    def test_maximum_timeout(self) -> None:
        """Test action creation with maximum timeout_ms."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="max_timeout_step",
            step_type="compute",
            timeout_ms=300000,  # Maximum value (5 minutes)
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert action.timeout_ms == 300000

    def test_maximum_retry_count(self) -> None:
        """Test action creation with maximum retry_count."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="max_retry_step",
            step_type="compute",
            retry_count=10,  # Maximum value
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert action.retry_count == 10

    def test_zero_retry_count(self) -> None:
        """Test action creation with zero retry_count."""
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="no_retry_step",
            step_type="compute",
            retry_count=0,
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert action.retry_count == 0

    def test_many_dependencies(self) -> None:
        """Test action creation with many dependencies."""
        dep_ids = [uuid4() for _ in range(50)]  # Many dependencies
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="many_deps_step",
            step_type="compute",
            depends_on=dep_ids,
        )
        workflow_id = uuid4()

        action, _ = _create_action_for_step(step, workflow_id)

        assert len(action.dependencies) == 50
        assert action.dependencies == dep_ids
