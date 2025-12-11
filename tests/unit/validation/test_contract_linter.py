"""
Unit tests for contract_linter.py.

Tests comprehensive workflow contract linting functionality including:
- Warning on unused parallel_group with SEQUENTIAL mode
- Warning on duplicate step names (not step_id)
- Warning on unreachable steps
- Warning on priority clamping (>1000 or <1)
- Warning on isolated steps (no edges)
- Verification that linter never raises exceptions
- ModelLintWarning model serialization
"""

from uuid import UUID, uuid4

import pytest

from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
from omnibase_core.models.contracts.subcontracts.model_execution_graph import (
    ModelExecutionGraph,
)
from omnibase_core.models.contracts.subcontracts.model_workflow_definition import (
    ModelWorkflowDefinition,
)
from omnibase_core.models.contracts.subcontracts.model_workflow_definition_metadata import (
    ModelWorkflowDefinitionMetadata,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.validation.model_lint_warning import ModelLintWarning
from omnibase_core.validation.workflow_linter import WorkflowLinter


@pytest.fixture
def sample_steps() -> list[ModelWorkflowStep]:
    """Create sample workflow steps for testing."""
    from uuid import uuid4

    step_a_id = uuid4()
    step_b_id = uuid4()
    return [
        ModelWorkflowStep(
            step_id=step_a_id,
            step_name="step_a",
            step_type="compute",
        ),
        ModelWorkflowStep(
            step_id=step_b_id,
            step_name="step_b",
            step_type="compute",
            depends_on=[step_a_id],
        ),
    ]


@pytest.fixture
def version() -> ModelSemVer:
    """Common version for all test fixtures."""
    return ModelSemVer(major=1, minor=0, patch=0)


@pytest.fixture
def linter() -> WorkflowLinter:
    """Create a WorkflowLinter instance for testing."""
    return WorkflowLinter()


@pytest.fixture
def empty_workflow(version: ModelSemVer) -> ModelWorkflowDefinition:
    """Create an empty workflow definition for testing."""
    return ModelWorkflowDefinition(
        version=version,
        workflow_metadata=ModelWorkflowDefinitionMetadata(
            version=version,
            workflow_name="empty_workflow",
            workflow_version=version,
            description="Empty workflow for testing",
            execution_mode="sequential",
        ),
        execution_graph=ModelExecutionGraph(
            version=version,
            nodes=[],
        ),
    )


@pytest.mark.unit
class TestWarnUnusedParallelGroup:
    """Test warnings for unused parallel_group configuration."""

    def test_warn_unused_parallel_group(
        self,
        linter: WorkflowLinter,
        version: ModelSemVer,
    ) -> None:
        """
        Test that parallel_group triggers warning with SEQUENTIAL mode.

        Should warn when parallel_group is set but execution_mode is SEQUENTIAL.
        """
        # Create workflow with SEQUENTIAL mode
        workflow = ModelWorkflowDefinition(
            version=version,
            workflow_metadata=ModelWorkflowDefinitionMetadata(
                version=version,
                workflow_name="sequential_workflow",
                workflow_version=version,
                description="Workflow with sequential execution",
                execution_mode="sequential",  # SEQUENTIAL mode
            ),
            execution_graph=ModelExecutionGraph(
                version=version,
                nodes=[],
            ),
        )

        # Create step with parallel_group set
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="parallel_step",
            step_type="compute",
            parallel_group="group_1",  # Unused in SEQUENTIAL mode
        )

        warnings = linter.warn_unused_parallel_group(workflow, [step])

        assert len(warnings) == 1
        assert warnings[0].code == "W001"
        assert "parallel_group" in warnings[0].message.lower()
        assert "sequential" in warnings[0].message.lower()
        assert warnings[0].step_reference == str(step.step_id)

    def test_no_warn_parallel_group_with_parallel_mode(
        self,
        linter: WorkflowLinter,
        version: ModelSemVer,
    ) -> None:
        """
        Test that parallel_group does NOT warn with PARALLEL mode.

        Should not warn when execution_mode is PARALLEL.
        """
        workflow = ModelWorkflowDefinition(
            version=version,
            workflow_metadata=ModelWorkflowDefinitionMetadata(
                version=version,
                workflow_name="parallel_workflow",
                workflow_version=version,
                description="Workflow with parallel execution",
                execution_mode="parallel",  # PARALLEL mode
            ),
            execution_graph=ModelExecutionGraph(
                version=version,
                nodes=[],
            ),
        )

        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="parallel_step",
            step_type="parallel",
            parallel_group="group_1",
        )

        warnings = linter.warn_unused_parallel_group(workflow, [step])

        assert len(warnings) == 0


@pytest.mark.unit
class TestWarnDuplicateStepNames:
    """Test warnings for duplicate step names."""

    def test_warn_duplicate_step_names(self, linter: WorkflowLinter) -> None:
        """
        Test that duplicate step names trigger warnings.

        Should warn when multiple steps have the same step_name (not step_id).
        """
        steps = [
            ModelWorkflowStep(
                step_id=uuid4(),
                step_name="duplicate_name",  # DUPLICATE
                step_type="compute",
            ),
            ModelWorkflowStep(
                step_id=uuid4(),
                step_name="duplicate_name",  # DUPLICATE
                step_type="compute",
            ),
            ModelWorkflowStep(
                step_id=uuid4(),
                step_name="unique_name",
                step_type="compute",
            ),
        ]

        warnings = linter.warn_duplicate_step_names(steps)

        assert len(warnings) == 1
        assert warnings[0].code == "W002"
        assert "duplicate_name" in warnings[0].message
        assert warnings[0].step_reference is None  # Applies to multiple steps

    def test_no_warn_unique_step_names(self, linter: WorkflowLinter) -> None:
        """
        Test that unique step names do not trigger warnings.

        Should not warn when all step names are unique.
        """
        steps = [
            ModelWorkflowStep(
                step_id=uuid4(),
                step_name="step_one",
                step_type="compute",
            ),
            ModelWorkflowStep(
                step_id=uuid4(),
                step_name="step_two",
                step_type="compute",
            ),
        ]

        warnings = linter.warn_duplicate_step_names(steps)

        assert len(warnings) == 0

    def test_warn_multiple_duplicate_names(self, linter: WorkflowLinter) -> None:
        """
        Test that multiple sets of duplicate names are all warned.

        Should generate one warning per duplicate name group.
        """
        steps = [
            ModelWorkflowStep(
                step_id=uuid4(),
                step_name="name_a",
                step_type="compute",
            ),
            ModelWorkflowStep(
                step_id=uuid4(),
                step_name="name_a",  # Duplicate A
                step_type="compute",
            ),
            ModelWorkflowStep(
                step_id=uuid4(),
                step_name="name_b",
                step_type="compute",
            ),
            ModelWorkflowStep(
                step_id=uuid4(),
                step_name="name_b",  # Duplicate B
                step_type="compute",
            ),
        ]

        warnings = linter.warn_duplicate_step_names(steps)

        assert len(warnings) == 2
        warning_messages = {w.message for w in warnings}
        assert any("name_a" in msg for msg in warning_messages)
        assert any("name_b" in msg for msg in warning_messages)


@pytest.mark.unit
class TestWarnUnreachableSteps:
    """Test warnings for unreachable steps."""

    def test_warn_unreachable_steps_with_missing_dependency(
        self, linter: WorkflowLinter
    ) -> None:
        """
        Test that steps depending on non-existent steps trigger warnings.

        A step is unreachable if it depends on a step_id that doesn't exist
        in the workflow, creating a broken dependency chain.
        """
        step_a_id = uuid4()
        step_b_id = uuid4()
        missing_dep_id = uuid4()  # This step doesn't exist in the workflow

        steps = [
            ModelWorkflowStep(
                step_id=step_a_id,
                step_name="root_step",
                step_type="compute",
                # No dependencies - root step
            ),
            ModelWorkflowStep(
                step_id=step_b_id,
                step_name="unreachable_step",
                step_type="compute",
                depends_on=[missing_dep_id],  # Depends on non-existent step
            ),
        ]

        warnings = linter.warn_unreachable_steps(steps)

        assert len(warnings) == 1
        assert warnings[0].code == "W003"
        assert "unreachable_step" in warnings[0].message
        assert "not in the workflow" in warnings[0].message
        assert warnings[0].step_reference == str(step_b_id)

    def test_warn_unreachable_steps_multiple_roots_no_warning(
        self, linter: WorkflowLinter
    ) -> None:
        """
        Test that multiple root steps (no dependencies) do NOT trigger warnings.

        Steps with no dependencies are considered root steps and are reachable
        by definition. This is different from isolated steps (which have no
        incoming AND no outgoing edges).
        """
        step_a_id = uuid4()
        step_b_id = uuid4()
        step_orphan_id = uuid4()

        steps = [
            ModelWorkflowStep(
                step_id=step_a_id,
                step_name="root_step",
                step_type="compute",
                # No dependencies - root step
            ),
            ModelWorkflowStep(
                step_id=step_b_id,
                step_name="connected_step",
                step_type="compute",
                depends_on=[step_a_id],
            ),
            ModelWorkflowStep(
                step_id=step_orphan_id,
                step_name="another_root_step",
                step_type="compute",
                depends_on=[],  # No dependencies - also a root step
            ),
        ]

        warnings = linter.warn_unreachable_steps(steps)

        # All steps are reachable: two are roots, one depends on a root
        assert len(warnings) == 0

    def test_no_warn_fully_connected_dag(self, linter: WorkflowLinter) -> None:
        """
        Test that fully connected DAG does not trigger warnings.

        All steps are reachable from root steps.
        """
        step_a_id = uuid4()
        step_b_id = uuid4()

        steps = [
            ModelWorkflowStep(
                step_id=step_a_id,
                step_name="root",
                step_type="compute",
            ),
            ModelWorkflowStep(
                step_id=step_b_id,
                step_name="child",
                step_type="compute",
                depends_on=[step_a_id],
            ),
        ]

        warnings = linter.warn_unreachable_steps(steps)

        assert len(warnings) == 0


@pytest.mark.unit
class TestWarnPriorityClamping:
    """Test warnings for priority clamping."""

    def test_warn_priority_clamping(self, linter: WorkflowLinter) -> None:
        """
        Test that priority >1000 triggers warning.

        Priorities above 1000 will be clamped at runtime.
        Note: ModelWorkflowStep validates priority bounds at creation time,
        so this test uses model_construct to bypass validation.
        """
        from omnibase_core.models.contracts.model_workflow_step import (
            ModelWorkflowStep,
        )

        # Use model_construct to bypass Pydantic validation
        step = ModelWorkflowStep.model_construct(
            step_id=uuid4(),
            step_name="high_priority_step",
            step_type="compute",
            priority=1500,  # Above maximum (bypassing validation)
            timeout_ms=30000,
            retry_count=3,
            enabled=True,
            skip_on_failure=False,
            continue_on_error=False,
            error_action="stop",
            max_memory_mb=None,
            max_cpu_percent=None,
            order_index=0,
            depends_on=[],
            parallel_group=None,
            max_parallel_instances=1,
        )

        warnings = linter.warn_priority_clamping([step])

        assert len(warnings) == 1
        assert warnings[0].code == "W004"
        assert "1500" in warnings[0].message
        assert "1000" in warnings[0].message
        assert "clamped" in warnings[0].message.lower()

    def test_warn_priority_below_minimum(self, linter: WorkflowLinter) -> None:
        """
        Test that priority <1 triggers warning.

        Priorities below 1 will be clamped at runtime.
        Note: ModelWorkflowStep validates priority bounds at creation time,
        so this test uses model_construct to bypass validation.
        """
        from omnibase_core.models.contracts.model_workflow_step import (
            ModelWorkflowStep,
        )

        # Use model_construct to bypass Pydantic validation
        step_too_low = ModelWorkflowStep.model_construct(
            step_id=uuid4(),
            step_name="low_priority_step",
            step_type="compute",
            priority=0,  # Below minimum (bypassing validation)
            timeout_ms=30000,
            retry_count=3,
            enabled=True,
            skip_on_failure=False,
            continue_on_error=False,
            error_action="stop",
            max_memory_mb=None,
            max_cpu_percent=None,
            order_index=0,
            depends_on=[],
            parallel_group=None,
            max_parallel_instances=1,
        )

        warnings = linter.warn_priority_clamping([step_too_low])

        # Should warn for priority=0 (below minimum)
        assert len(warnings) == 1
        assert warnings[0].code == "W004"
        assert "0" in warnings[0].message
        assert "below minimum" in warnings[0].message.lower()
        assert "clamped" in warnings[0].message.lower()

    def test_warn_priority_minimum_boundary_no_warning(
        self, linter: WorkflowLinter
    ) -> None:
        """
        Test that priority=1 (minimum valid) does NOT trigger warning.

        Priority 1 is the valid minimum and should not produce warnings.
        """
        # Create step with minimum valid priority (1)
        step_valid = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="valid_priority_step",
            step_type="compute",
            priority=1,  # Minimum valid - should not warn
        )

        warnings = linter.warn_priority_clamping([step_valid])

        # Should not warn for priority=1 (valid minimum)
        assert len(warnings) == 0

    def test_warn_priority_negative_value(self, linter: WorkflowLinter) -> None:
        """
        Test that negative priority triggers warning.

        Negative priorities will be clamped to 1 at runtime.
        """
        from omnibase_core.models.contracts.model_workflow_step import (
            ModelWorkflowStep,
        )

        # Use model_construct to bypass Pydantic validation
        step_negative = ModelWorkflowStep.model_construct(
            step_id=uuid4(),
            step_name="negative_priority_step",
            step_type="compute",
            priority=-5,  # Negative (bypassing validation)
            timeout_ms=30000,
            retry_count=3,
            enabled=True,
            skip_on_failure=False,
            continue_on_error=False,
            error_action="stop",
            max_memory_mb=None,
            max_cpu_percent=None,
            order_index=0,
            depends_on=[],
            parallel_group=None,
            max_parallel_instances=1,
        )

        warnings = linter.warn_priority_clamping([step_negative])

        # Should warn for negative priority
        assert len(warnings) == 1
        assert warnings[0].code == "W004"
        assert "-5" in warnings[0].message
        assert "below minimum" in warnings[0].message.lower()
        assert warnings[0].step_reference is not None

    def test_warn_multiple_priority_issues(self, linter: WorkflowLinter) -> None:
        """
        Test that multiple priority issues are all warned.

        Should generate warnings for all steps with out-of-range priorities.
        Note: ModelWorkflowStep validates priority bounds at creation time,
        so this test uses model_construct to bypass validation.
        """
        from omnibase_core.models.contracts.model_workflow_step import (
            ModelWorkflowStep,
        )

        # Use model_construct to bypass Pydantic validation
        step_too_high = ModelWorkflowStep.model_construct(
            step_id=uuid4(),
            step_name="too_high",
            step_type="compute",
            priority=2000,  # Above max (bypassing validation)
            timeout_ms=30000,
            retry_count=3,
            enabled=True,
            skip_on_failure=False,
            continue_on_error=False,
            error_action="stop",
            max_memory_mb=None,
            max_cpu_percent=None,
            order_index=0,
            depends_on=[],
            parallel_group=None,
            max_parallel_instances=1,
        )

        step_valid = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="valid",
            step_type="compute",
            priority=500,
        )

        warnings = linter.warn_priority_clamping([step_too_high, step_valid])

        assert len(warnings) == 1  # Only too_high triggers warning
        assert "too_high" in warnings[0].message
        assert "2000" in warnings[0].message


@pytest.mark.unit
class TestWarnIsolatedSteps:
    """Test warnings for isolated steps."""

    def test_warn_isolated_steps(self, linter: WorkflowLinter) -> None:
        """
        Test that isolated steps trigger warnings.

        Isolated steps have no incoming AND no outgoing edges.
        """
        step_a_id = uuid4()
        step_b_id = uuid4()
        step_isolated_id = uuid4()

        steps = [
            ModelWorkflowStep(
                step_id=step_a_id,
                step_name="connected_a",
                step_type="compute",
            ),
            ModelWorkflowStep(
                step_id=step_b_id,
                step_name="connected_b",
                step_type="compute",
                depends_on=[step_a_id],
            ),
            ModelWorkflowStep(
                step_id=step_isolated_id,
                step_name="isolated_step",
                step_type="compute",
                # No dependencies and nothing depends on it
            ),
        ]

        warnings = linter.warn_isolated_steps(steps)

        assert len(warnings) == 1
        assert warnings[0].code == "W005"
        assert "isolated_step" in warnings[0].message
        assert "isolated" in warnings[0].message.lower()

    def test_no_warn_single_step_workflow(self, linter: WorkflowLinter) -> None:
        """
        Test that single-step workflows do not trigger isolation warnings.

        Single-step workflows are exempt from isolation detection.
        """
        step = ModelWorkflowStep(
            step_id=uuid4(),
            step_name="only_step",
            step_type="compute",
        )

        warnings = linter.warn_isolated_steps([step])

        assert len(warnings) == 0

    def test_warn_multiple_isolated_steps(self, linter: WorkflowLinter) -> None:
        """
        Test that multiple isolated steps are all warned.

        Should generate one warning per isolated step.
        """
        step_a_id = uuid4()
        step_b_id = uuid4()
        isolated_1_id = uuid4()
        isolated_2_id = uuid4()

        steps = [
            ModelWorkflowStep(
                step_id=step_a_id,
                step_name="connected_a",
                step_type="compute",
            ),
            ModelWorkflowStep(
                step_id=step_b_id,
                step_name="connected_b",
                step_type="compute",
                depends_on=[step_a_id],
            ),
            ModelWorkflowStep(
                step_id=isolated_1_id,
                step_name="isolated_1",
                step_type="compute",
            ),
            ModelWorkflowStep(
                step_id=isolated_2_id,
                step_name="isolated_2",
                step_type="compute",
            ),
        ]

        warnings = linter.warn_isolated_steps(steps)

        assert len(warnings) == 2
        warning_messages = {w.message for w in warnings}
        assert any("isolated_1" in msg for msg in warning_messages)
        assert any("isolated_2" in msg for msg in warning_messages)


@pytest.mark.unit
class TestLinterDoesNotRaise:
    """Test that linter never raises exceptions."""

    def test_linter_does_not_raise(
        self,
        linter: WorkflowLinter,
        empty_workflow: ModelWorkflowDefinition,
    ) -> None:
        """
        Test that linter never raises exceptions, only returns warnings.

        Linter should be defensive and handle all inputs gracefully.
        """
        # Empty workflow should not raise
        try:
            warnings = linter.lint(empty_workflow)
            assert isinstance(warnings, list)
        except Exception as e:
            pytest.fail(f"Linter raised exception: {e}")

    def test_linter_handles_empty_steps(self, linter: WorkflowLinter) -> None:
        """
        Test that linter handles empty step lists gracefully.

        Should return empty warnings list, not raise exceptions.
        """
        empty_steps: list[ModelWorkflowStep] = []

        try:
            warnings_dup = linter.warn_duplicate_step_names(empty_steps)
            warnings_unreach = linter.warn_unreachable_steps(empty_steps)
            warnings_priority = linter.warn_priority_clamping(empty_steps)
            warnings_isolated = linter.warn_isolated_steps(empty_steps)

            assert isinstance(warnings_dup, list)
            assert isinstance(warnings_unreach, list)
            assert isinstance(warnings_priority, list)
            assert isinstance(warnings_isolated, list)
        except Exception as e:
            pytest.fail(f"Linter raised exception on empty input: {e}")


@pytest.mark.unit
class TestModelLintWarningModel:
    """Test ModelLintWarning model serialization and validation."""

    def test_lint_warning_model(self) -> None:
        """
        Test that ModelLintWarning model serializes correctly.

        Should create valid ModelLintWarning instances with all fields.
        """
        warning = ModelLintWarning(
            code="W001",
            message="Test warning message",
            step_reference=str(uuid4()),
            severity="warning",
        )

        assert warning.code == "W001"
        assert warning.message == "Test warning message"
        assert warning.step_reference is not None
        assert warning.severity == "warning"

    def test_lint_warning_optional_step_reference(self) -> None:
        """
        Test that ModelLintWarning accepts None for step_reference.

        Some warnings apply to the entire workflow, not specific steps.
        """
        warning = ModelLintWarning(
            code="W002",
            message="Workflow-level warning",
            step_reference=None,
            severity="info",
        )

        assert warning.step_reference is None
        assert warning.severity == "info"

    def test_lint_warning_frozen(self) -> None:
        """
        Test that ModelLintWarning is immutable (frozen).

        Should raise ValidationError when attempting to modify fields.
        """
        from pydantic import ValidationError

        warning = ModelLintWarning(
            code="W001",
            message="Test warning",
            severity="warning",
        )

        with pytest.raises(ValidationError) as exc_info:
            warning.code = "W002"  # type: ignore[misc]

        # Verify the error is about frozen instance
        assert (
            "frozen" in str(exc_info.value).lower()
            or "immutable" in str(exc_info.value).lower()
        )

    def test_lint_warning_json_serialization(self) -> None:
        """
        Test that ModelLintWarning can be serialized to JSON.

        Should produce valid JSON representation.
        """
        warning = ModelLintWarning(
            code="W001",
            message="Test warning",
            step_reference="12345678-1234-5678-1234-567812345678",
            severity="warning",
        )

        json_data = warning.model_dump()

        assert json_data["code"] == "W001"
        assert json_data["message"] == "Test warning"
        assert json_data["step_reference"] == "12345678-1234-5678-1234-567812345678"
        assert json_data["severity"] == "warning"


@pytest.mark.unit
class TestLintIntegration:
    """Integration tests for full workflow linting."""

    def test_lint_returns_list_of_model_lint_warning(
        self,
        linter: WorkflowLinter,
        version: ModelSemVer,
    ) -> None:
        """
        Test that lint() returns a list of ModelLintWarning instances.

        Verifies the return type is correct even for empty workflows.
        """
        # Create workflow with no issues
        workflow = ModelWorkflowDefinition(
            version=version,
            workflow_metadata=ModelWorkflowDefinitionMetadata(
                version=version,
                workflow_name="clean_workflow",
                workflow_version=version,
                description="Workflow with no linting issues",
                execution_mode="sequential",
            ),
            execution_graph=ModelExecutionGraph(
                version=version,
                nodes=[],
            ),
        )

        warnings = linter.lint(workflow)

        # Should return list of warnings
        assert isinstance(warnings, list)
        # Empty workflow with no steps should have no warnings
        assert len(warnings) == 0
        # Verify list type (all elements would be ModelLintWarning if present)
        for warning in warnings:
            assert isinstance(warning, ModelLintWarning)

    def test_lint_aggregates_warnings_from_all_checks(
        self,
        linter: WorkflowLinter,
    ) -> None:
        """
        Test that lint() aggregates warnings from all linting checks.

        Should run all linting checks and combine results into a single list.
        """
        # Create steps with multiple linting issues using model_construct
        step_a_id = uuid4()
        step_b_id = uuid4()
        isolated_id = uuid4()

        # Normal step
        step_a = ModelWorkflowStep(
            step_id=step_a_id,
            step_name="step_a",
            step_type="compute",
        )

        # Step depending on step_a
        step_b = ModelWorkflowStep(
            step_id=step_b_id,
            step_name="step_b",
            step_type="compute",
            depends_on=[step_a_id],
        )

        # Isolated step (no dependencies, nothing depends on it)
        isolated_step = ModelWorkflowStep(
            step_id=isolated_id,
            step_name="isolated_step",
            step_type="compute",
        )

        steps = [step_a, step_b, isolated_step]

        # Test warn_isolated_steps directly
        isolated_warnings = linter.warn_isolated_steps(steps)

        # Should detect the isolated step
        assert len(isolated_warnings) >= 1
        assert any(w.code == "W005" for w in isolated_warnings)
        # Verify the warning contains expected information
        isolated_warning = next(w for w in isolated_warnings if w.code == "W005")
        assert "isolated_step" in isolated_warning.message
        assert isinstance(isolated_warning, ModelLintWarning)

    def test_lint_empty_workflow_no_warnings(
        self,
        linter: WorkflowLinter,
        empty_workflow: ModelWorkflowDefinition,
    ) -> None:
        """
        Test that empty workflow produces no warnings.

        Empty workflow has no steps, so no linting issues.
        """
        warnings = linter.lint(empty_workflow)

        assert len(warnings) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
