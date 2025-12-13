"""
Unit tests for WorkflowValidator.

TDD-first tests for workflow DAG validation per OMN-176 acceptance criteria:
- Kahn's algorithm topological sorting
- Cycle detection with step name reporting
- Dependency validation (missing dependencies)
- Isolated step detection
- Unique step name validation
- Resource exhaustion protection (PR #158)

Tests are written FIRST before implementation (TDD red phase).
"""

from unittest.mock import patch
from uuid import UUID, uuid4

import pytest

from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.validation.workflow_validator import (
    MAX_DFS_ITERATIONS,
    ModelWorkflowValidationResult,
    WorkflowValidator,
)

# =============================================================================
# Test Fixtures
# =============================================================================


def create_step(
    step_name: str,
    step_id: UUID | None = None,
    depends_on: list[UUID] | None = None,
) -> ModelWorkflowStep:
    """Create a workflow step with minimal required fields."""
    return ModelWorkflowStep(
        step_id=step_id or uuid4(),
        step_name=step_name,
        step_type="compute",
        depends_on=depends_on or [],
    )


# =============================================================================
# Kahn's Algorithm Topological Sort Tests
# =============================================================================


class TestWorkflowValidatorTopologicalSort:
    """Tests for Kahn's algorithm topological sorting."""

    @pytest.mark.unit
    def test_empty_workflow_returns_empty_order(self) -> None:
        """Test that an empty workflow returns an empty topological order."""
        validator = WorkflowValidator()
        steps: list[ModelWorkflowStep] = []

        result = validator.topological_sort(steps)

        assert result == []

    @pytest.mark.unit
    def test_single_step_workflow_returns_single_step(self) -> None:
        """Test that a single step workflow returns that step."""
        validator = WorkflowValidator()
        step = create_step("only_step")
        steps = [step]

        result = validator.topological_sort(steps)

        assert len(result) == 1
        assert result[0] == step.step_id

    @pytest.mark.unit
    def test_multiple_independent_steps_returns_all_steps(self) -> None:
        """Test that multiple independent steps (no dependencies) are all returned."""
        validator = WorkflowValidator()
        step_a = create_step("step_a")
        step_b = create_step("step_b")
        step_c = create_step("step_c")
        steps = [step_a, step_b, step_c]

        result = validator.topological_sort(steps)

        # All steps should be in result (order may vary for independent steps)
        assert len(result) == 3
        assert set(result) == {step_a.step_id, step_b.step_id, step_c.step_id}

    @pytest.mark.unit
    def test_linear_chain_returns_correct_order(self) -> None:
        """Test linear chain dependency (A -> B -> C) returns correct topological order."""
        validator = WorkflowValidator()

        # Create steps with explicit IDs for dependency references
        step_a_id = uuid4()
        step_b_id = uuid4()
        step_c_id = uuid4()

        step_a = create_step("step_a", step_id=step_a_id)
        step_b = create_step("step_b", step_id=step_b_id, depends_on=[step_a_id])
        step_c = create_step("step_c", step_id=step_c_id, depends_on=[step_b_id])
        steps = [step_c, step_a, step_b]  # Deliberately unordered input

        result = validator.topological_sort(steps)

        # A must come before B, B must come before C
        assert len(result) == 3
        assert result.index(step_a_id) < result.index(step_b_id)
        assert result.index(step_b_id) < result.index(step_c_id)

    @pytest.mark.unit
    def test_diamond_pattern_returns_valid_order(self) -> None:
        """
        Test diamond dependency pattern returns valid topological order.

        Pattern:
            A
           / \
          B   C
           \\ /
            D

        A -> B, A -> C, B -> D, C -> D
        """
        validator = WorkflowValidator()

        step_a_id = uuid4()
        step_b_id = uuid4()
        step_c_id = uuid4()
        step_d_id = uuid4()

        step_a = create_step("step_a", step_id=step_a_id)
        step_b = create_step("step_b", step_id=step_b_id, depends_on=[step_a_id])
        step_c = create_step("step_c", step_id=step_c_id, depends_on=[step_a_id])
        step_d = create_step(
            "step_d", step_id=step_d_id, depends_on=[step_b_id, step_c_id]
        )
        steps = [step_d, step_b, step_c, step_a]  # Deliberately unordered

        result = validator.topological_sort(steps)

        # Verify ordering constraints
        assert len(result) == 4
        # A must come before B and C
        assert result.index(step_a_id) < result.index(step_b_id)
        assert result.index(step_a_id) < result.index(step_c_id)
        # B and C must come before D
        assert result.index(step_b_id) < result.index(step_d_id)
        assert result.index(step_c_id) < result.index(step_d_id)

    @pytest.mark.unit
    def test_complex_dag_returns_valid_order(self) -> None:
        """
        Test complex DAG with multiple entry and exit points.

        Pattern:
            A     E
           / \\     \
          B   C     F
           \\   \\   /
            D   G
        """
        validator = WorkflowValidator()

        step_a_id = uuid4()
        step_b_id = uuid4()
        step_c_id = uuid4()
        step_d_id = uuid4()
        step_e_id = uuid4()
        step_f_id = uuid4()
        step_g_id = uuid4()

        step_a = create_step("step_a", step_id=step_a_id)
        step_b = create_step("step_b", step_id=step_b_id, depends_on=[step_a_id])
        step_c = create_step("step_c", step_id=step_c_id, depends_on=[step_a_id])
        step_d = create_step("step_d", step_id=step_d_id, depends_on=[step_b_id])
        step_e = create_step("step_e", step_id=step_e_id)
        step_f = create_step("step_f", step_id=step_f_id, depends_on=[step_e_id])
        step_g = create_step(
            "step_g", step_id=step_g_id, depends_on=[step_c_id, step_f_id]
        )

        steps = [step_g, step_f, step_e, step_d, step_c, step_b, step_a]

        result = validator.topological_sort(steps)

        # Verify all steps present
        assert len(result) == 7

        # Verify ordering constraints
        assert result.index(step_a_id) < result.index(step_b_id)
        assert result.index(step_a_id) < result.index(step_c_id)
        assert result.index(step_b_id) < result.index(step_d_id)
        assert result.index(step_e_id) < result.index(step_f_id)
        assert result.index(step_c_id) < result.index(step_g_id)
        assert result.index(step_f_id) < result.index(step_g_id)


# =============================================================================
# Cycle Detection Tests
# =============================================================================


class TestWorkflowValidatorCycleDetection:
    """Tests for cycle detection with step name reporting."""

    @pytest.mark.unit
    def test_simple_cycle_detected(self) -> None:
        """Test simple cycle (A -> B -> A) is detected."""
        validator = WorkflowValidator()

        step_a_id = uuid4()
        step_b_id = uuid4()

        step_a = create_step("step_a", step_id=step_a_id, depends_on=[step_b_id])
        step_b = create_step("step_b", step_id=step_b_id, depends_on=[step_a_id])
        steps = [step_a, step_b]

        result = validator.detect_cycles(steps)

        assert result.has_cycle is True

    @pytest.mark.unit
    def test_simple_cycle_reports_step_names(self) -> None:
        """
        CRITICAL: Test simple cycle reports step NAMES (not just IDs).

        Per OMN-176 acceptance criteria: Error messages MUST include step names.
        """
        validator = WorkflowValidator()

        step_a_id = uuid4()
        step_b_id = uuid4()

        step_a = create_step("process_data", step_id=step_a_id, depends_on=[step_b_id])
        step_b = create_step("validate_data", step_id=step_b_id, depends_on=[step_a_id])
        steps = [step_a, step_b]

        result = validator.detect_cycles(steps)

        # CRITICAL: Error message must contain step NAMES
        assert result.has_cycle is True
        assert "process_data" in result.cycle_description
        assert "validate_data" in result.cycle_description

    @pytest.mark.unit
    def test_multi_step_cycle_detected(self) -> None:
        """Test multi-step cycle (A -> B -> C -> A) is detected."""
        validator = WorkflowValidator()

        step_a_id = uuid4()
        step_b_id = uuid4()
        step_c_id = uuid4()

        step_a = create_step("step_a", step_id=step_a_id, depends_on=[step_c_id])
        step_b = create_step("step_b", step_id=step_b_id, depends_on=[step_a_id])
        step_c = create_step("step_c", step_id=step_c_id, depends_on=[step_b_id])
        steps = [step_a, step_b, step_c]

        result = validator.detect_cycles(steps)

        assert result.has_cycle is True

    @pytest.mark.unit
    def test_multi_step_cycle_reports_all_step_names(self) -> None:
        """Test multi-step cycle reports all involved step names."""
        validator = WorkflowValidator()

        step_a_id = uuid4()
        step_b_id = uuid4()
        step_c_id = uuid4()

        step_a = create_step("fetch_data", step_id=step_a_id, depends_on=[step_c_id])
        step_b = create_step(
            "transform_data", step_id=step_b_id, depends_on=[step_a_id]
        )
        step_c = create_step("store_data", step_id=step_c_id, depends_on=[step_b_id])
        steps = [step_a, step_b, step_c]

        result = validator.detect_cycles(steps)

        assert result.has_cycle is True
        # All step names in the cycle should be reported
        assert "fetch_data" in result.cycle_description
        assert "transform_data" in result.cycle_description
        assert "store_data" in result.cycle_description

    @pytest.mark.unit
    def test_self_reference_cycle_detected(self) -> None:
        """Test self-reference cycle (A -> A) is detected."""
        validator = WorkflowValidator()

        step_a_id = uuid4()
        step_a = create_step("self_loop", step_id=step_a_id, depends_on=[step_a_id])
        steps = [step_a]

        result = validator.detect_cycles(steps)

        assert result.has_cycle is True
        assert "self_loop" in result.cycle_description

    @pytest.mark.unit
    def test_no_cycle_in_valid_dag(self) -> None:
        """Test that valid DAG without cycles passes detection."""
        validator = WorkflowValidator()

        step_a_id = uuid4()
        step_b_id = uuid4()
        step_c_id = uuid4()

        step_a = create_step("step_a", step_id=step_a_id)
        step_b = create_step("step_b", step_id=step_b_id, depends_on=[step_a_id])
        step_c = create_step("step_c", step_id=step_c_id, depends_on=[step_b_id])
        steps = [step_a, step_b, step_c]

        result = validator.detect_cycles(steps)

        assert result.has_cycle is False
        assert result.cycle_description == ""

    @pytest.mark.unit
    def test_cycle_in_subgraph_detected(self) -> None:
        """Test cycle in subgraph is detected even with valid portions."""
        validator = WorkflowValidator()

        # Valid portion
        step_a_id = uuid4()
        step_a = create_step("valid_step", step_id=step_a_id)

        # Cycle portion
        step_b_id = uuid4()
        step_c_id = uuid4()
        step_b = create_step("cycle_step_1", step_id=step_b_id, depends_on=[step_c_id])
        step_c = create_step("cycle_step_2", step_id=step_c_id, depends_on=[step_b_id])

        steps = [step_a, step_b, step_c]

        result = validator.detect_cycles(steps)

        assert result.has_cycle is True
        assert "cycle_step_1" in result.cycle_description
        assert "cycle_step_2" in result.cycle_description


# =============================================================================
# Dependency Validation Tests
# =============================================================================


class TestWorkflowValidatorDependencyValidation:
    """Tests for dependency existence validation."""

    @pytest.mark.unit
    def test_missing_dependency_detected(self) -> None:
        """Test that referencing non-existent step_id is detected."""
        validator = WorkflowValidator()

        non_existent_id = uuid4()
        step_a = create_step("step_a", depends_on=[non_existent_id])
        steps = [step_a]

        result = validator.validate_dependencies(steps)

        assert not result.is_valid
        assert len(result.missing_dependencies) == 1
        assert non_existent_id in result.missing_dependencies

    @pytest.mark.unit
    def test_multiple_missing_dependencies_detected(self) -> None:
        """Test that multiple missing dependencies are all reported."""
        validator = WorkflowValidator()

        missing_id_1 = uuid4()
        missing_id_2 = uuid4()
        missing_id_3 = uuid4()

        step_a = create_step("step_a", depends_on=[missing_id_1, missing_id_2])
        step_b = create_step("step_b", depends_on=[missing_id_3])
        steps = [step_a, step_b]

        result = validator.validate_dependencies(steps)

        assert not result.is_valid
        assert len(result.missing_dependencies) == 3
        assert missing_id_1 in result.missing_dependencies
        assert missing_id_2 in result.missing_dependencies
        assert missing_id_3 in result.missing_dependencies

    @pytest.mark.unit
    def test_all_dependencies_exist_passes(self) -> None:
        """Test that valid dependencies pass validation."""
        validator = WorkflowValidator()

        step_a_id = uuid4()
        step_b_id = uuid4()

        step_a = create_step("step_a", step_id=step_a_id)
        step_b = create_step("step_b", step_id=step_b_id, depends_on=[step_a_id])
        steps = [step_a, step_b]

        result = validator.validate_dependencies(steps)

        assert result.is_valid
        assert len(result.missing_dependencies) == 0

    @pytest.mark.unit
    def test_empty_workflow_dependencies_valid(self) -> None:
        """Test that empty workflow has valid dependencies."""
        validator = WorkflowValidator()
        steps: list[ModelWorkflowStep] = []

        result = validator.validate_dependencies(steps)

        assert result.is_valid
        assert len(result.missing_dependencies) == 0

    @pytest.mark.unit
    def test_missing_dependency_reports_step_name(self) -> None:
        """Test that missing dependency error includes the step name that has the issue."""
        validator = WorkflowValidator()

        non_existent_id = uuid4()
        step_a = create_step("problematic_step", depends_on=[non_existent_id])
        steps = [step_a]

        result = validator.validate_dependencies(steps)

        assert not result.is_valid
        # Error should indicate which step has the missing dependency
        assert "problematic_step" in result.error_message


# =============================================================================
# Isolated Step Detection Tests
# =============================================================================


class TestWorkflowValidatorIsolatedSteps:
    """Tests for isolated step detection."""

    @pytest.mark.unit
    def test_isolated_step_detected(self) -> None:
        """
        Test isolated step detection.

        An isolated step has NO incoming AND NO outgoing edges in a workflow
        with multiple steps. Single-step workflows are exempt.
        """
        validator = WorkflowValidator()

        # Connected chain: A -> B
        step_a_id = uuid4()
        step_b_id = uuid4()
        step_a = create_step("connected_a", step_id=step_a_id)
        step_b = create_step("connected_b", step_id=step_b_id, depends_on=[step_a_id])

        # Isolated step: no dependencies and nothing depends on it
        step_isolated = create_step("isolated_step")

        steps = [step_a, step_b, step_isolated]

        result = validator.detect_isolated_steps(steps)

        assert len(result.isolated_steps) == 1
        assert result.isolated_steps[0] == step_isolated.step_id

    @pytest.mark.unit
    def test_step_with_only_incoming_edges_not_isolated(self) -> None:
        """Test that a step with only incoming edges (endpoint) is NOT isolated."""
        validator = WorkflowValidator()

        step_a_id = uuid4()
        step_b_id = uuid4()

        step_a = create_step("start_step", step_id=step_a_id)
        step_b = create_step(
            "end_step", step_id=step_b_id, depends_on=[step_a_id]
        )  # Only incoming

        steps = [step_a, step_b]

        result = validator.detect_isolated_steps(steps)

        # step_b has incoming edges, so it's not isolated
        assert step_b_id not in result.isolated_steps

    @pytest.mark.unit
    def test_step_with_only_outgoing_edges_not_isolated(self) -> None:
        """Test that a step with only outgoing edges (start point) is NOT isolated."""
        validator = WorkflowValidator()

        step_a_id = uuid4()
        step_b_id = uuid4()

        step_a = create_step(
            "start_step", step_id=step_a_id
        )  # Only outgoing (others depend on it)
        step_b = create_step("end_step", step_id=step_b_id, depends_on=[step_a_id])

        steps = [step_a, step_b]

        result = validator.detect_isolated_steps(steps)

        # step_a has outgoing edges (step_b depends on it), so it's not isolated
        assert step_a_id not in result.isolated_steps

    @pytest.mark.unit
    def test_single_step_workflow_not_isolated(self) -> None:
        """Test that a single-step workflow is not considered isolated."""
        validator = WorkflowValidator()

        step_only = create_step("only_step")
        steps = [step_only]

        result = validator.detect_isolated_steps(steps)

        # Single step workflows are exempt from isolation detection
        assert len(result.isolated_steps) == 0

    @pytest.mark.unit
    def test_multiple_isolated_steps_detected(self) -> None:
        """Test multiple isolated steps are all detected."""
        validator = WorkflowValidator()

        # Connected pair
        step_a_id = uuid4()
        step_b_id = uuid4()
        step_a = create_step("connected_a", step_id=step_a_id)
        step_b = create_step("connected_b", step_id=step_b_id, depends_on=[step_a_id])

        # Multiple isolated steps
        isolated_1 = create_step("isolated_1")
        isolated_2 = create_step("isolated_2")

        steps = [step_a, step_b, isolated_1, isolated_2]

        result = validator.detect_isolated_steps(steps)

        assert len(result.isolated_steps) == 2
        assert isolated_1.step_id in result.isolated_steps
        assert isolated_2.step_id in result.isolated_steps

    @pytest.mark.unit
    def test_empty_workflow_no_isolated_steps(self) -> None:
        """Test that empty workflow has no isolated steps."""
        validator = WorkflowValidator()
        steps: list[ModelWorkflowStep] = []

        result = validator.detect_isolated_steps(steps)

        assert len(result.isolated_steps) == 0

    @pytest.mark.unit
    def test_isolated_step_reports_step_name(self) -> None:
        """Test that isolated step detection includes step names."""
        validator = WorkflowValidator()

        # Connected chain
        step_a_id = uuid4()
        step_b_id = uuid4()
        step_a = create_step("connected_a", step_id=step_a_id)
        step_b = create_step("connected_b", step_id=step_b_id, depends_on=[step_a_id])

        # Isolated step
        isolated = create_step("orphaned_step")

        steps = [step_a, step_b, isolated]

        result = validator.detect_isolated_steps(steps)

        # Step name should be in the message
        assert "orphaned_step" in result.isolated_step_names


# =============================================================================
# Unique Step Name Validation Tests
# =============================================================================


class TestWorkflowValidatorUniqueNames:
    """Tests for unique step name validation."""

    @pytest.mark.unit
    def test_duplicate_step_names_detected(self) -> None:
        """Test that duplicate step names are detected."""
        validator = WorkflowValidator()

        step_a = create_step("duplicate_name")
        step_b = create_step("duplicate_name")  # Same name, different step_id
        steps = [step_a, step_b]

        result = validator.validate_unique_names(steps)

        assert not result.is_valid
        assert "duplicate_name" in result.duplicate_names

    @pytest.mark.unit
    def test_unique_step_names_pass(self) -> None:
        """Test that unique step names pass validation."""
        validator = WorkflowValidator()

        step_a = create_step("unique_name_a")
        step_b = create_step("unique_name_b")
        step_c = create_step("unique_name_c")
        steps = [step_a, step_b, step_c]

        result = validator.validate_unique_names(steps)

        assert result.is_valid
        assert len(result.duplicate_names) == 0

    @pytest.mark.unit
    def test_empty_workflow_unique_names_valid(self) -> None:
        """Test that empty workflow has valid unique names."""
        validator = WorkflowValidator()
        steps: list[ModelWorkflowStep] = []

        result = validator.validate_unique_names(steps)

        assert result.is_valid
        assert len(result.duplicate_names) == 0

    @pytest.mark.unit
    def test_multiple_duplicate_names_all_reported(self) -> None:
        """Test that multiple sets of duplicates are all reported."""
        validator = WorkflowValidator()

        step_a1 = create_step("name_a")
        step_a2 = create_step("name_a")
        step_b1 = create_step("name_b")
        step_b2 = create_step("name_b")
        step_c = create_step("unique_name")
        steps = [step_a1, step_a2, step_b1, step_b2, step_c]

        result = validator.validate_unique_names(steps)

        assert not result.is_valid
        assert "name_a" in result.duplicate_names
        assert "name_b" in result.duplicate_names
        assert "unique_name" not in result.duplicate_names

    @pytest.mark.unit
    def test_triple_duplicate_names_detected(self) -> None:
        """Test that three steps with same name are detected."""
        validator = WorkflowValidator()

        step_1 = create_step("repeated_name")
        step_2 = create_step("repeated_name")
        step_3 = create_step("repeated_name")
        steps = [step_1, step_2, step_3]

        result = validator.validate_unique_names(steps)

        assert not result.is_valid
        assert "repeated_name" in result.duplicate_names


# =============================================================================
# Integration Tests - Full Workflow Validation
# =============================================================================


class TestWorkflowValidatorIntegration:
    """Integration tests for complete workflow validation."""

    @pytest.mark.unit
    def test_valid_dag_validation_returns_success_with_correct_topology(self) -> None:
        """
        Test that valid DAG passes all validation checks.

        Verifies:
        - Result type is ModelWorkflowValidationResult
        - is_valid is True for valid DAGs
        - No cycles detected
        - Topological order contains all steps
        - Dependency ordering is correct (A before B)
        """
        validator = WorkflowValidator()

        step_a_id = uuid4()
        step_b_id = uuid4()
        step_a = create_step("step_a", step_id=step_a_id)
        step_b = create_step("step_b", step_id=step_b_id, depends_on=[step_a_id])
        steps = [step_a, step_b]

        result = validator.validate_workflow(steps)

        # Verify result type
        assert isinstance(result, ModelWorkflowValidationResult)
        # For a valid workflow, is_valid should be True
        assert result.is_valid is True
        # Should have no cycles in a valid DAG
        assert result.has_cycles is False
        # Should have correct topological order with all steps
        assert len(result.topological_order) == 2
        assert step_a_id in result.topological_order
        assert step_b_id in result.topological_order
        # Verify dependency order: step_a must come before step_b
        assert result.topological_order.index(
            step_a_id
        ) < result.topological_order.index(step_b_id)

    @pytest.mark.unit
    def test_valid_workflow_passes_all_checks(self) -> None:
        """Test that a valid workflow passes all validation checks."""
        validator = WorkflowValidator()

        step_a_id = uuid4()
        step_b_id = uuid4()
        step_c_id = uuid4()

        step_a = create_step("fetch_data", step_id=step_a_id)
        step_b = create_step("process_data", step_id=step_b_id, depends_on=[step_a_id])
        step_c = create_step("store_data", step_id=step_c_id, depends_on=[step_b_id])
        steps = [step_a, step_b, step_c]

        result = validator.validate_workflow(steps)

        assert result.is_valid
        assert not result.has_cycles
        assert len(result.missing_dependencies) == 0
        assert len(result.isolated_steps) == 0
        assert len(result.duplicate_names) == 0
        assert len(result.topological_order) == 3

    @pytest.mark.unit
    def test_workflow_with_cycle_fails(self) -> None:
        """Test that workflow with cycle fails validation."""
        validator = WorkflowValidator()

        step_a_id = uuid4()
        step_b_id = uuid4()

        step_a = create_step("step_a", step_id=step_a_id, depends_on=[step_b_id])
        step_b = create_step("step_b", step_id=step_b_id, depends_on=[step_a_id])
        steps = [step_a, step_b]

        result = validator.validate_workflow(steps)

        assert not result.is_valid
        assert result.has_cycles
        assert len(result.errors) > 0

    @pytest.mark.unit
    def test_workflow_with_missing_dependency_fails(self) -> None:
        """Test that workflow with missing dependency fails validation."""
        validator = WorkflowValidator()

        non_existent_id = uuid4()
        step_a = create_step("step_a", depends_on=[non_existent_id])
        steps = [step_a]

        result = validator.validate_workflow(steps)

        assert not result.is_valid
        assert len(result.missing_dependencies) > 0
        assert len(result.errors) > 0

    @pytest.mark.unit
    def test_workflow_with_duplicate_names_fails(self) -> None:
        """Test that workflow with duplicate names fails validation."""
        validator = WorkflowValidator()

        step_a = create_step("duplicate_name")
        step_b = create_step("duplicate_name")
        steps = [step_a, step_b]

        result = validator.validate_workflow(steps)

        assert not result.is_valid
        assert len(result.duplicate_names) > 0
        assert len(result.errors) > 0

    @pytest.mark.unit
    def test_malformed_workflow_reports_all_validation_issues(self) -> None:
        """
        Test workflow with multiple validation issues reports all of them.

        Creates workflow with 4 intentional issues:
        1. Cycle between step_a and step_b (cycle error)
        2. Duplicate names: step_a and step_b both named "cycle_step" (name error)
        3. Missing dependency (dependency error)
        4. Isolated step (warning, not error)

        Expected errors (3 total):
        - Duplicate step names error
        - Missing dependency error
        - Cycle detection error

        Note: Isolated steps generate warnings, not errors.
        """
        validator = WorkflowValidator()

        step_a_id = uuid4()
        step_b_id = uuid4()
        non_existent_id = uuid4()

        # Cycle + Duplicate names
        step_a = create_step("cycle_step", step_id=step_a_id, depends_on=[step_b_id])
        step_b = create_step(
            "cycle_step",
            step_id=step_b_id,  # Duplicate name!
            depends_on=[step_a_id],
        )

        # Missing dependency
        step_c = create_step("missing_dep_step", depends_on=[non_existent_id])

        # Isolated step (no dependencies, nothing depends on it)
        step_isolated = create_step("isolated_step")

        steps = [step_a, step_b, step_c, step_isolated]

        result = validator.validate_workflow(steps)

        assert not result.is_valid
        # Verify specific errors detected
        assert result.has_cycles is True
        assert len(result.duplicate_names) > 0
        assert len(result.missing_dependencies) > 0
        # Should have at least 3 errors: duplicate names, missing dep, cycle
        expected_min_errors = 3
        assert len(result.errors) >= expected_min_errors
        # Isolated step should be reported as warning, not error
        assert len(result.isolated_steps) > 0
        assert len(result.warnings) > 0

    @pytest.mark.unit
    def test_validation_result_contains_topological_order_for_valid_dag(self) -> None:
        """Test that valid DAG validation result contains topological order."""
        validator = WorkflowValidator()

        step_a_id = uuid4()
        step_b_id = uuid4()

        step_a = create_step("step_a", step_id=step_a_id)
        step_b = create_step("step_b", step_id=step_b_id, depends_on=[step_a_id])
        steps = [step_a, step_b]

        result = validator.validate_workflow(steps)

        assert result.is_valid
        assert len(result.topological_order) == 2
        assert result.topological_order.index(
            step_a_id
        ) < result.topological_order.index(step_b_id)

    @pytest.mark.unit
    def test_validation_result_contains_warnings_for_isolated_steps(self) -> None:
        """Test that isolated steps generate warnings, not errors."""
        validator = WorkflowValidator()

        # Connected pair
        step_a_id = uuid4()
        step_b_id = uuid4()
        step_a = create_step("connected_a", step_id=step_a_id)
        step_b = create_step("connected_b", step_id=step_b_id, depends_on=[step_a_id])

        # Isolated step - may be warning not error depending on implementation
        step_isolated = create_step("isolated_step")

        steps = [step_a, step_b, step_isolated]

        result = validator.validate_workflow(steps)

        # Isolated steps should at minimum be reported
        assert len(result.isolated_steps) == 1
        # Warnings should be present
        assert len(result.warnings) > 0


# =============================================================================
# Edge Cases and Error Handling Tests
# =============================================================================


class TestWorkflowValidatorEdgeCases:
    """Edge case tests for robust error handling."""

    @pytest.mark.unit
    def test_step_depends_on_itself_and_others(self) -> None:
        """Test step that depends on itself and other valid steps."""
        validator = WorkflowValidator()

        step_a_id = uuid4()
        step_b_id = uuid4()

        step_a = create_step("valid_dep", step_id=step_a_id)
        step_b = create_step(
            "self_dep",
            step_id=step_b_id,
            depends_on=[step_a_id, step_b_id],  # Both valid dep and self-dep
        )
        steps = [step_a, step_b]

        result = validator.detect_cycles(steps)

        assert result.has_cycle is True

    @pytest.mark.unit
    def test_large_linear_chain_validates_with_correct_order(self) -> None:
        """
        Test validation of a large 100-step linear chain workflow.

        Verifies:
        - Large workflows validate successfully
        - Topological order contains all 100 steps
        - Order respects linear dependency chain
        """
        validator = WorkflowValidator()

        # Create a large linear chain: step_0 -> step_1 -> ... -> step_99
        num_steps = 100
        steps: list[ModelWorkflowStep] = []
        prev_id: UUID | None = None

        for i in range(num_steps):
            step_id = uuid4()
            depends = [prev_id] if prev_id else []
            step = create_step(f"step_{i}", step_id=step_id, depends_on=depends)
            steps.append(step)
            prev_id = step_id

        result = validator.validate_workflow(steps)

        assert result.is_valid
        assert len(result.topological_order) == num_steps
        # Verify linear chain order: first step must be first, last must be last
        assert result.topological_order[0] == steps[0].step_id
        assert result.topological_order[-1] == steps[-1].step_id
        # Verify no cycles, no missing deps, no duplicates
        assert result.has_cycles is False
        assert len(result.missing_dependencies) == 0
        assert len(result.duplicate_names) == 0

    @pytest.mark.unit
    def test_parallel_branches_validates_with_correct_constraints(self) -> None:
        """
        Test workflow with multiple parallel execution branches.

        Validates fan-out/fan-in pattern:
            start
           /  |  \\
          a   b   c
           \\  |  /
            end

        Verifies:
        - Valid workflow passes
        - All 5 steps in topological order
        - start comes before all branches
        - All branches come before end
        - No cycles, missing deps, or isolated steps
        """
        validator = WorkflowValidator()

        start_id = uuid4()
        a_id = uuid4()
        b_id = uuid4()
        c_id = uuid4()
        end_id = uuid4()

        start = create_step("start", step_id=start_id)
        a = create_step("branch_a", step_id=a_id, depends_on=[start_id])
        b = create_step("branch_b", step_id=b_id, depends_on=[start_id])
        c = create_step("branch_c", step_id=c_id, depends_on=[start_id])
        end = create_step("end", step_id=end_id, depends_on=[a_id, b_id, c_id])

        num_steps = 5
        steps = [start, a, b, c, end]

        result = validator.validate_workflow(steps)

        assert result.is_valid
        assert len(result.topological_order) == num_steps
        # start must be first (has no dependencies)
        assert result.topological_order[0] == start_id
        # end must be last (depends on all branches)
        assert result.topological_order[-1] == end_id
        # All branches must come after start and before end
        start_idx = result.topological_order.index(start_id)
        end_idx = result.topological_order.index(end_id)
        for branch_id in [a_id, b_id, c_id]:
            branch_idx = result.topological_order.index(branch_id)
            assert start_idx < branch_idx < end_idx
        # Verify no validation issues
        assert result.has_cycles is False
        assert len(result.missing_dependencies) == 0
        assert len(result.isolated_steps) == 0


# =============================================================================
# Resource Exhaustion Protection Tests (PR #158)
# =============================================================================


class TestWorkflowValidatorResourceExhaustion:
    """Tests for resource exhaustion protection in cycle detection."""

    @pytest.mark.unit
    def test_max_dfs_iterations_constant_is_exported(self) -> None:
        """Test that MAX_DFS_ITERATIONS constant is exported and has reasonable value."""
        # Verify the constant is exported and accessible
        assert MAX_DFS_ITERATIONS == 10_000
        # Value should be reasonable for typical workflows
        assert MAX_DFS_ITERATIONS > 1000  # Enough for normal workflows
        assert MAX_DFS_ITERATIONS < 1_000_000  # Not too high to cause real issues

    @pytest.mark.unit
    def test_iteration_limit_raises_on_excessive_iterations(self) -> None:
        """
        Test that cycle detection raises ModelOnexError when iteration limit exceeded.

        This test uses mocking to simulate exceeding the iteration limit without
        creating an actual malicious workflow, which would be slow and memory-intensive.
        """
        validator = WorkflowValidator()

        # Create a simple valid workflow
        step_a_id = uuid4()
        step_a = create_step("step_a", step_id=step_a_id)
        steps = [step_a]

        # Mock MAX_DFS_ITERATIONS to a very low value to trigger the limit
        with patch("omnibase_core.validation.workflow_validator.MAX_DFS_ITERATIONS", 0):
            with pytest.raises(ModelOnexError) as exc_info:
                validator.detect_cycles(steps)

            # Verify error message includes key information
            error = exc_info.value
            assert "exceeded" in error.message.lower()
            assert "iterations" in error.message.lower()

    @pytest.mark.unit
    def test_error_context_includes_step_count(self) -> None:
        """
        Test that resource exhaustion error includes step count context.

        The error context should include:
        - step_count: number of steps in the workflow
        - max_iterations: the iteration limit that was exceeded
        - last_node: the node being processed when limit was hit
        """
        validator = WorkflowValidator()

        # Create a workflow with multiple steps
        step_ids = [uuid4() for _ in range(5)]
        steps = [create_step(f"step_{i}", step_id=step_ids[i]) for i in range(5)]

        # Mock MAX_DFS_ITERATIONS to a very low value
        with patch("omnibase_core.validation.workflow_validator.MAX_DFS_ITERATIONS", 0):
            with pytest.raises(ModelOnexError) as exc_info:
                validator.detect_cycles(steps)

            # Verify error context contains expected fields
            error = exc_info.value
            # Access context through the underlying model
            assert hasattr(error, "model")
            context = error.model.context
            assert context is not None
            assert "step_count" in context
            assert context["step_count"] == 5
            assert "max_iterations" in context
            assert "last_node" in context

    @pytest.mark.unit
    def test_normal_workflow_does_not_trigger_limit(self) -> None:
        """
        Test that normal workflows don't trigger the iteration limit.

        A workflow with 100 steps in a linear chain should validate successfully
        without hitting the 10,000 iteration limit.
        """
        validator = WorkflowValidator()

        # Create a 100-step linear chain (well under 10,000 iterations)
        steps: list[ModelWorkflowStep] = []
        prev_id: UUID | None = None

        for i in range(100):
            step_id = uuid4()
            depends = [prev_id] if prev_id else []
            step = create_step(f"step_{i}", step_id=step_id, depends_on=depends)
            steps.append(step)
            prev_id = step_id

        # Should complete without raising
        result = validator.detect_cycles(steps)
        assert result.has_cycle is False

    @pytest.mark.unit
    def test_complex_dag_does_not_trigger_limit(self) -> None:
        """
        Test that complex DAG structures don't trigger the iteration limit.

        A diamond pattern DAG with fan-out and fan-in should validate
        successfully without hitting resource limits.
        """
        validator = WorkflowValidator()

        # Create a complex fan-out / fan-in pattern
        # Start -> [A, B, C, D, E] -> [X, Y, Z] -> End
        start_id = uuid4()
        middle_ids = [uuid4() for _ in range(5)]
        merge_ids = [uuid4() for _ in range(3)]
        end_id = uuid4()

        steps = [create_step("start", step_id=start_id)]

        # Fan-out: 5 parallel steps depending on start
        for i, mid_id in enumerate(middle_ids):
            steps.append(
                create_step(f"middle_{i}", step_id=mid_id, depends_on=[start_id])
            )

        # Merge: 3 steps depending on all middle steps
        for i, merge_id in enumerate(merge_ids):
            steps.append(
                create_step(f"merge_{i}", step_id=merge_id, depends_on=middle_ids)
            )

        # End: depends on all merge steps
        steps.append(create_step("end", step_id=end_id, depends_on=merge_ids))

        # Should complete without raising
        result = validator.detect_cycles(steps)
        assert result.has_cycle is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
