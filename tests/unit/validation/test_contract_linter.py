"""
Unit tests for WorkflowLinter (workflow_linter.py).

Tests comprehensive workflow contract linting functionality including:
- Warning on unused parallel_group with SEQUENTIAL mode
- Warning on duplicate step names (not step_id)
- Warning on unreachable steps
- Warning on priority clamping (>1000 or <1)
- Warning on isolated steps (no edges)
- Verification that linter never raises exceptions
- ModelLintWarning model serialization
- Warning aggregation for large workflows
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
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.validation.model_lint_warning import ModelLintWarning
from omnibase_core.validation.workflow_linter import (
    DEFAULT_MAX_WARNINGS_PER_CODE,
    WorkflowLinter,
)


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

    def test_warn_isolated_steps_detects_isolation(
        self,
        linter: WorkflowLinter,
    ) -> None:
        """
        Test that warn_isolated_steps detects isolated steps in a workflow.

        An isolated step has no incoming dependencies and no outgoing edges.
        """
        # Create steps with one isolated step
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

    def test_lint_aggregates_warnings_from_all_checks(
        self,
        version: ModelSemVer,
    ) -> None:
        """
        Test that lint() aggregates warnings from all individual check methods.

        Verifies that the main lint() method calls all warning checks and
        combines their results into a single list of ModelLintWarning instances.
        This exercises the full integration path through lint().
        """
        from omnibase_core.enums.enum_node_type import EnumNodeType
        from omnibase_core.models.contracts.subcontracts.model_workflow_node import (
            ModelWorkflowNode,
        )

        linter = WorkflowLinter(aggregate_warnings=False)

        # Create a workflow that triggers multiple warning types:
        # - W005: Isolated steps (multiple isolated nodes)
        # - W002: Duplicate step names (if applicable via nodes)

        # Use dict for version to avoid Pydantic model class identity issues
        # in parallel test execution (pytest-xdist). The dict is coerced by
        # Pydantic into the correct ModelSemVer type during validation.
        version_dict = version.model_dump()

        # Create multiple isolated nodes to trigger W005 warnings
        isolated_nodes = [
            ModelWorkflowNode(
                version=version_dict,
                node_id=uuid4(),
                node_type=EnumNodeType.COMPUTE_GENERIC,
                node_requirements={"step_name": f"isolated_{i}"},
                dependencies=[],
            )
            for i in range(3)
        ]

        workflow = ModelWorkflowDefinition(
            version=version_dict,
            workflow_metadata=ModelWorkflowDefinitionMetadata(
                version=version_dict,
                workflow_name="multi_warning_workflow",
                workflow_version=version_dict,
                description="Workflow designed to trigger multiple warning types",
                execution_mode="sequential",
            ),
            execution_graph=ModelExecutionGraph(
                version=version_dict,
                nodes=isolated_nodes,
            ),
        )

        # Call lint() which should aggregate warnings from all checks
        warnings = linter.lint(workflow)

        # Should return a list of ModelLintWarning instances
        assert isinstance(warnings, list)
        for warning in warnings:
            assert isinstance(warning, ModelLintWarning)

        # Should have W005 warnings for isolated steps (3 isolated nodes)
        w005_warnings = [w for w in warnings if w.code == "W005"]
        assert len(w005_warnings) == 3


@pytest.mark.unit
class TestWarningAggregation:
    """Test warning aggregation functionality for large workflows."""

    def test_aggregation_when_warnings_exceed_threshold(self) -> None:
        """
        Test that warnings are aggregated when they exceed max_warnings_per_code.

        Should keep first N warnings and add a summary warning.
        """
        linter = WorkflowLinter(max_warnings_per_code=3, aggregate_warnings=True)

        # Create 5 warnings with same code
        warnings = [
            ModelLintWarning(
                code="W001",
                message=f"Warning {i}",
                step_reference=str(uuid4()),
                severity="warning",
            )
            for i in range(5)
        ]

        aggregated = linter._aggregate_warnings_by_code(warnings)

        # Should have 3 kept warnings + 1 summary = 4 total
        assert len(aggregated) == 4
        # First 3 should be the original warnings
        for i in range(3):
            assert aggregated[i].message == f"Warning {i}"
        # Last should be summary
        assert "2 more similar warnings" in aggregated[3].message
        assert "5 total" in aggregated[3].message

    def test_aggregation_disabled(self) -> None:
        """
        Test that aggregation can be disabled via lint() method.

        When aggregate_warnings=False, lint() should return all warnings
        without calling _aggregate_warnings_by_code, preserving full count.
        """
        from omnibase_core.enums.enum_node_type import EnumNodeType
        from omnibase_core.models.contracts.subcontracts.model_workflow_node import (
            ModelWorkflowNode,
        )

        # Create two linters: one with aggregation, one without
        linter_with_agg = WorkflowLinter(
            max_warnings_per_code=2, aggregate_warnings=True
        )
        linter_without_agg = WorkflowLinter(
            max_warnings_per_code=2, aggregate_warnings=False
        )

        # Use dict for version to avoid Pydantic model class identity issues
        # in parallel test execution (pytest-xdist). The dict is coerced by
        # Pydantic into the correct ModelSemVer type during validation.
        version_dict = {"major": 1, "minor": 0, "patch": 0}

        # Create workflow with many isolated nodes (will trigger W005 warnings)
        # We need 5+ isolated nodes to exceed the threshold of 2
        # Convert to dicts to avoid Pydantic validation issues with frozen models
        isolated_nodes = [
            ModelWorkflowNode(
                version=version_dict,
                node_id=uuid4(),
                node_type=EnumNodeType.COMPUTE_GENERIC,
                node_requirements={"step_name": f"isolated_step_{i}"},
                dependencies=[],
            ).model_dump()
            for i in range(5)
        ]

        workflow = ModelWorkflowDefinition(
            version=version_dict,
            workflow_metadata=ModelWorkflowDefinitionMetadata(
                version=version_dict,
                workflow_name="test_workflow",
                workflow_version=version_dict,
                description="Test workflow with isolated steps",
                execution_mode="sequential",
            ),
            execution_graph=ModelExecutionGraph(
                version=version_dict,
                nodes=isolated_nodes,
            ),
        )

        # Lint with both linters
        warnings_with_agg = linter_with_agg.lint(workflow)
        warnings_without_agg = linter_without_agg.lint(workflow)

        # With aggregation enabled: should have fewer warnings (aggregated)
        # 5 isolated steps -> 5 W005 warnings, aggregated to 2 + 1 summary = 3
        w005_with_agg = [w for w in warnings_with_agg if w.code == "W005"]
        assert len(w005_with_agg) == 3  # 2 kept + 1 summary
        assert any("more similar warnings" in w.message for w in w005_with_agg)

        # Without aggregation: should have all 5 original warnings
        w005_without_agg = [w for w in warnings_without_agg if w.code == "W005"]
        assert len(w005_without_agg) == 5  # All original warnings preserved
        assert not any("more similar warnings" in w.message for w in w005_without_agg)

    def test_aggregation_with_multiple_codes(self) -> None:
        """
        Test aggregation with multiple warning codes.

        Each code should be aggregated independently.
        """
        linter = WorkflowLinter(max_warnings_per_code=2, aggregate_warnings=True)

        # Create warnings with different codes
        warnings = [
            # 4 W001 warnings
            ModelLintWarning(code="W001", message="W001-1", severity="warning"),
            ModelLintWarning(code="W001", message="W001-2", severity="warning"),
            ModelLintWarning(code="W001", message="W001-3", severity="warning"),
            ModelLintWarning(code="W001", message="W001-4", severity="warning"),
            # 3 W002 warnings
            ModelLintWarning(code="W002", message="W002-1", severity="info"),
            ModelLintWarning(code="W002", message="W002-2", severity="info"),
            ModelLintWarning(code="W002", message="W002-3", severity="info"),
        ]

        aggregated = linter._aggregate_warnings_by_code(warnings)

        # W001: 2 kept + 1 summary = 3
        # W002: 2 kept + 1 summary = 3
        # Total: 6
        assert len(aggregated) == 6

        # Check W001 aggregation
        w001_warnings = [w for w in aggregated if w.code == "W001"]
        assert len(w001_warnings) == 3
        assert any("2 more similar warnings" in w.message for w in w001_warnings)

        # Check W002 aggregation
        w002_warnings = [w for w in aggregated if w.code == "W002"]
        assert len(w002_warnings) == 3
        assert any("1 more similar warnings" in w.message for w in w002_warnings)

    def test_no_aggregation_when_below_threshold(self) -> None:
        """
        Test that no aggregation occurs when warnings are below threshold.

        Should return original warnings unchanged.
        """
        linter = WorkflowLinter(max_warnings_per_code=10, aggregate_warnings=True)

        warnings = [
            ModelLintWarning(code="W001", message=f"Warning {i}", severity="warning")
            for i in range(5)
        ]

        aggregated = linter._aggregate_warnings_by_code(warnings)

        # Should have same count - no summary added
        assert len(aggregated) == 5
        # No summary message should be present
        assert not any("more similar warnings" in w.message for w in aggregated)

    def test_aggregation_empty_warnings(self) -> None:
        """
        Test aggregation with empty warnings list.

        Should return empty list without error.
        """
        linter = WorkflowLinter(max_warnings_per_code=5, aggregate_warnings=True)

        aggregated = linter._aggregate_warnings_by_code([])

        assert len(aggregated) == 0

    def test_default_aggregation_settings(self) -> None:
        """
        Test that default aggregation settings are correct.

        Should have aggregation enabled with default max_warnings_per_code.
        """
        linter = WorkflowLinter()

        assert linter._aggregate_warnings is True
        assert linter._max_warnings_per_code == DEFAULT_MAX_WARNINGS_PER_CODE
        assert DEFAULT_MAX_WARNINGS_PER_CODE == 10

    def test_invalid_max_warnings_per_code(self) -> None:
        """
        Test that invalid max_warnings_per_code raises ModelOnexError.

        Should raise error for values < 1.
        """
        with pytest.raises(ModelOnexError) as exc_info:
            WorkflowLinter(max_warnings_per_code=0)

        assert "max_warnings_per_code must be >= 1" in str(exc_info.value)

        with pytest.raises(ModelOnexError) as exc_info:
            WorkflowLinter(max_warnings_per_code=-1)

        assert "max_warnings_per_code must be >= 1" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
