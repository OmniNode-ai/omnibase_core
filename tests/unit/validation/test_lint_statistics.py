"""
Unit tests for ModelLintStatistics.

Tests comprehensive lint statistics functionality including:
- Model creation and validation
- Immutability (frozen model)
- Helper methods (get_warnings_per_step, get_most_common_warning_code, etc.)
- JSON serialization
- Integration with WorkflowLinter.get_statistics()
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

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
from omnibase_core.models.validation.model_lint_statistics import ModelLintStatistics
from omnibase_core.models.validation.model_lint_warning import ModelLintWarning
from omnibase_core.validation.workflow_linter import WorkflowLinter


@pytest.fixture
def version() -> ModelSemVer:
    """Common version for all test fixtures."""
    return ModelSemVer(major=1, minor=0, patch=0)


@pytest.fixture
def sample_statistics() -> ModelLintStatistics:
    """Create sample lint statistics for testing."""
    return ModelLintStatistics(
        workflow_name="test_workflow",
        total_warnings=10,
        warnings_by_code={"W001": 4, "W002": 3, "W003": 2, "W005": 1},
        warnings_by_severity={"warning": 8, "info": 2},
        step_count=20,
        lint_duration_ms=15.5,
    )


@pytest.mark.unit
class TestModelLintStatisticsCreation:
    """Test ModelLintStatistics creation and validation."""

    def test_create_statistics_with_all_fields(self) -> None:
        """
        Test creating statistics with all fields specified.

        Should create valid ModelLintStatistics instance.
        """
        stats = ModelLintStatistics(
            workflow_name="my_workflow",
            total_warnings=5,
            warnings_by_code={"W001": 3, "W002": 2},
            warnings_by_severity={"warning": 4, "info": 1},
            step_count=10,
            lint_duration_ms=8.25,
        )

        assert stats.workflow_name == "my_workflow"
        assert stats.total_warnings == 5
        assert stats.warnings_by_code == {"W001": 3, "W002": 2}
        assert stats.warnings_by_severity == {"warning": 4, "info": 1}
        assert stats.step_count == 10
        assert stats.lint_duration_ms == 8.25
        assert stats.timestamp is not None

    def test_create_statistics_with_defaults(self) -> None:
        """
        Test creating statistics with default values.

        Should use defaults for optional fields.
        """
        stats = ModelLintStatistics(
            workflow_name="minimal_workflow",
            total_warnings=0,
            step_count=5,
            lint_duration_ms=1.0,
        )

        assert stats.workflow_name == "minimal_workflow"
        assert stats.total_warnings == 0
        assert stats.warnings_by_code == {}
        assert stats.warnings_by_severity == {"warning": 0, "info": 0}
        assert stats.step_count == 5
        assert stats.lint_duration_ms == 1.0

    def test_create_statistics_with_custom_timestamp(self) -> None:
        """
        Test creating statistics with custom timestamp.

        Should use provided timestamp instead of default.
        """
        custom_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        stats = ModelLintStatistics(
            workflow_name="timed_workflow",
            total_warnings=0,
            step_count=1,
            lint_duration_ms=0.5,
            timestamp=custom_time,
        )

        assert stats.timestamp == custom_time

    def test_validation_negative_total_warnings(self) -> None:
        """
        Test that negative total_warnings raises ValidationError.

        total_warnings must be >= 0.
        """
        with pytest.raises(ValidationError) as exc_info:
            ModelLintStatistics(
                workflow_name="invalid",
                total_warnings=-1,  # Invalid
                step_count=5,
                lint_duration_ms=1.0,
            )

        assert "total_warnings" in str(exc_info.value).lower()

    def test_validation_negative_step_count(self) -> None:
        """
        Test that negative step_count raises ValidationError.

        step_count must be >= 0.
        """
        with pytest.raises(ValidationError) as exc_info:
            ModelLintStatistics(
                workflow_name="invalid",
                total_warnings=0,
                step_count=-1,  # Invalid
                lint_duration_ms=1.0,
            )

        assert "step_count" in str(exc_info.value).lower()

    def test_validation_negative_duration(self) -> None:
        """
        Test that negative lint_duration_ms raises ValidationError.

        lint_duration_ms must be >= 0.0.
        """
        with pytest.raises(ValidationError) as exc_info:
            ModelLintStatistics(
                workflow_name="invalid",
                total_warnings=0,
                step_count=5,
                lint_duration_ms=-1.0,  # Invalid
            )

        assert "lint_duration_ms" in str(exc_info.value).lower()

    def test_validation_empty_workflow_name(self) -> None:
        """
        Test that empty workflow_name raises ValidationError.

        workflow_name must have min_length=1.
        """
        with pytest.raises(ValidationError) as exc_info:
            ModelLintStatistics(
                workflow_name="",  # Invalid
                total_warnings=0,
                step_count=5,
                lint_duration_ms=1.0,
            )

        assert "workflow_name" in str(exc_info.value).lower()


@pytest.mark.unit
class TestModelLintStatisticsImmutability:
    """Test that ModelLintStatistics is immutable (frozen)."""

    def test_frozen_workflow_name(self, sample_statistics: ModelLintStatistics) -> None:
        """
        Test that workflow_name cannot be modified.

        Should raise ValidationError on assignment.
        """
        with pytest.raises(ValidationError) as exc_info:
            sample_statistics.workflow_name = "new_name"  # type: ignore[misc]

        assert (
            "frozen" in str(exc_info.value).lower()
            or "immutable" in str(exc_info.value).lower()
        )

    def test_frozen_total_warnings(
        self, sample_statistics: ModelLintStatistics
    ) -> None:
        """
        Test that total_warnings cannot be modified.

        Should raise ValidationError on assignment.
        """
        with pytest.raises(ValidationError) as exc_info:
            sample_statistics.total_warnings = 100  # type: ignore[misc]

        assert (
            "frozen" in str(exc_info.value).lower()
            or "immutable" in str(exc_info.value).lower()
        )


@pytest.mark.unit
class TestModelLintStatisticsHelperMethods:
    """Test helper methods on ModelLintStatistics."""

    def test_get_warnings_per_step(self) -> None:
        """
        Test get_warnings_per_step calculation.

        Should return total_warnings / step_count.
        """
        stats = ModelLintStatistics(
            workflow_name="test",
            total_warnings=10,
            step_count=5,
            lint_duration_ms=1.0,
        )

        assert stats.get_warnings_per_step() == 2.0

    def test_get_warnings_per_step_zero_steps(self) -> None:
        """
        Test get_warnings_per_step with zero steps.

        Should return 0.0 to avoid division by zero.
        """
        stats = ModelLintStatistics(
            workflow_name="empty",
            total_warnings=0,
            step_count=0,
            lint_duration_ms=1.0,
        )

        assert stats.get_warnings_per_step() == 0.0

    def test_get_most_common_warning_code(self) -> None:
        """
        Test get_most_common_warning_code returns highest count.

        Should return the code with most occurrences.
        """
        stats = ModelLintStatistics(
            workflow_name="test",
            total_warnings=10,
            warnings_by_code={"W001": 2, "W002": 5, "W003": 3},
            step_count=10,
            lint_duration_ms=1.0,
        )

        assert stats.get_most_common_warning_code() == "W002"

    def test_get_most_common_warning_code_empty(self) -> None:
        """
        Test get_most_common_warning_code with no warnings.

        Should return None when no warnings exist.
        """
        stats = ModelLintStatistics(
            workflow_name="clean",
            total_warnings=0,
            warnings_by_code={},
            step_count=10,
            lint_duration_ms=1.0,
        )

        assert stats.get_most_common_warning_code() is None

    def test_has_critical_warnings_true(self) -> None:
        """
        Test has_critical_warnings returns True for W003.

        W003 (unreachable steps) is a critical warning.
        """
        stats = ModelLintStatistics(
            workflow_name="test",
            total_warnings=2,
            warnings_by_code={"W001": 1, "W003": 1},
            step_count=10,
            lint_duration_ms=1.0,
        )

        assert stats.has_critical_warnings() is True

    def test_has_critical_warnings_w005(self) -> None:
        """
        Test has_critical_warnings returns True for W005.

        W005 (isolated steps) is a critical warning.
        """
        stats = ModelLintStatistics(
            workflow_name="test",
            total_warnings=1,
            warnings_by_code={"W005": 1},
            step_count=10,
            lint_duration_ms=1.0,
        )

        assert stats.has_critical_warnings() is True

    def test_has_critical_warnings_false(self) -> None:
        """
        Test has_critical_warnings returns False for non-critical codes.

        W001, W002, W004 are not critical warnings.
        """
        stats = ModelLintStatistics(
            workflow_name="test",
            total_warnings=3,
            warnings_by_code={"W001": 1, "W002": 1, "W004": 1},
            step_count=10,
            lint_duration_ms=1.0,
        )

        assert stats.has_critical_warnings() is False

    def test_is_clean_true(self) -> None:
        """
        Test is_clean returns True when no warnings.

        Should return True for total_warnings=0.
        """
        stats = ModelLintStatistics(
            workflow_name="clean",
            total_warnings=0,
            step_count=10,
            lint_duration_ms=1.0,
        )

        assert stats.is_clean() is True

    def test_is_clean_false(self) -> None:
        """
        Test is_clean returns False when warnings exist.

        Should return False for total_warnings>0.
        """
        stats = ModelLintStatistics(
            workflow_name="dirty",
            total_warnings=1,
            step_count=10,
            lint_duration_ms=1.0,
        )

        assert stats.is_clean() is False


@pytest.mark.unit
class TestModelLintStatisticsSerialization:
    """Test JSON serialization of ModelLintStatistics."""

    def test_model_dump(self, sample_statistics: ModelLintStatistics) -> None:
        """
        Test model_dump() produces valid dictionary.

        Should include all fields with correct values.
        """
        data = sample_statistics.model_dump()

        assert data["workflow_name"] == "test_workflow"
        assert data["total_warnings"] == 10
        assert data["warnings_by_code"] == {"W001": 4, "W002": 3, "W003": 2, "W005": 1}
        assert data["warnings_by_severity"] == {"warning": 8, "info": 2}
        assert data["step_count"] == 20
        assert data["lint_duration_ms"] == 15.5
        assert "timestamp" in data

    def test_model_dump_json(self, sample_statistics: ModelLintStatistics) -> None:
        """
        Test model_dump_json() produces valid JSON string.

        Should be deserializable back to dict.
        """
        import json

        json_str = sample_statistics.model_dump_json()
        data = json.loads(json_str)

        assert data["workflow_name"] == "test_workflow"
        assert data["total_warnings"] == 10

    def test_round_trip_serialization(
        self, sample_statistics: ModelLintStatistics
    ) -> None:
        """
        Test round-trip serialization.

        Should be able to serialize and deserialize back.
        """
        # Serialize
        data = sample_statistics.model_dump()

        # Deserialize
        restored = ModelLintStatistics.model_validate(data)

        assert restored.workflow_name == sample_statistics.workflow_name
        assert restored.total_warnings == sample_statistics.total_warnings
        assert restored.warnings_by_code == sample_statistics.warnings_by_code
        assert restored.step_count == sample_statistics.step_count
        assert restored.lint_duration_ms == sample_statistics.lint_duration_ms


@pytest.mark.unit
class TestWorkflowLinterGetStatistics:
    """Test WorkflowLinter.get_statistics() integration."""

    def test_get_statistics_basic(self, version: ModelSemVer) -> None:
        """
        Test basic get_statistics() functionality.

        Should return ModelLintStatistics with correct values.
        """
        linter = WorkflowLinter()

        workflow = ModelWorkflowDefinition(
            version=version,
            workflow_metadata=ModelWorkflowDefinitionMetadata(
                version=version,
                workflow_name="test_workflow",
                workflow_version=version,
                description="Test workflow",
                execution_mode="sequential",
            ),
            execution_graph=ModelExecutionGraph(
                version=version,
                nodes=[],
            ),
        )

        warnings = [
            ModelLintWarning(code="W001", message="Test 1", severity="warning"),
            ModelLintWarning(code="W001", message="Test 2", severity="warning"),
            ModelLintWarning(code="W002", message="Test 3", severity="info"),
        ]

        stats = linter.get_statistics(workflow, warnings, 10.5)

        assert stats.workflow_name == "test_workflow"
        assert stats.total_warnings == 3
        assert stats.warnings_by_code == {"W001": 2, "W002": 1}
        assert stats.warnings_by_severity == {"warning": 2, "info": 1}
        assert stats.step_count == 0  # Empty execution graph
        assert stats.lint_duration_ms == 10.5

    def test_get_statistics_empty_warnings(self, version: ModelSemVer) -> None:
        """
        Test get_statistics() with no warnings.

        Should return statistics indicating clean workflow.
        """
        linter = WorkflowLinter()

        workflow = ModelWorkflowDefinition(
            version=version,
            workflow_metadata=ModelWorkflowDefinitionMetadata(
                version=version,
                workflow_name="clean_workflow",
                workflow_version=version,
                description="Clean workflow",
                execution_mode="parallel",
            ),
            execution_graph=ModelExecutionGraph(
                version=version,
                nodes=[],
            ),
        )

        stats = linter.get_statistics(workflow, [], 5.0)

        assert stats.workflow_name == "clean_workflow"
        assert stats.total_warnings == 0
        assert stats.warnings_by_code == {}
        assert stats.warnings_by_severity == {"warning": 0, "info": 0}
        assert stats.is_clean() is True

    def test_get_statistics_with_critical_warnings(self, version: ModelSemVer) -> None:
        """
        Test get_statistics() with critical warning codes.

        Should correctly identify critical warnings.
        """
        linter = WorkflowLinter()

        workflow = ModelWorkflowDefinition(
            version=version,
            workflow_metadata=ModelWorkflowDefinitionMetadata(
                version=version,
                workflow_name="critical_workflow",
                workflow_version=version,
                description="Workflow with critical warnings",
                execution_mode="sequential",
            ),
            execution_graph=ModelExecutionGraph(
                version=version,
                nodes=[],
            ),
        )

        warnings = [
            ModelLintWarning(
                code="W003", message="Unreachable step", severity="warning"
            ),
            ModelLintWarning(code="W005", message="Isolated step", severity="warning"),
        ]

        stats = linter.get_statistics(workflow, warnings, 2.5)

        assert stats.has_critical_warnings() is True
        assert "W003" in stats.warnings_by_code
        assert "W005" in stats.warnings_by_code


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
