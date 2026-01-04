"""
Lint statistics model for workflow linting telemetry.

This module provides the ModelLintStatistics model for capturing telemetry
data from workflow linting operations, including warning counts by code and
severity, timing information, and workflow metrics.

Example:
    Basic usage for creating lint statistics::

        from omnibase_core.models.validation.model_lint_statistics import ModelLintStatistics

        stats = ModelLintStatistics(
            workflow_name="my_workflow",
            total_warnings=5,
            warnings_by_code={"W001": 2, "W002": 3},
            warnings_by_severity={"warning": 4, "info": 1},
            step_count=10,
            lint_duration_ms=15.5,
        )

        # Check if workflow is clean
        if stats.is_clean():
            print("No warnings found!")

        # Get most common warning
        print(f"Most common: {stats.get_most_common_warning_code()}")

See Also:
    - :class:`omnibase_core.validation.checker_workflow_linter.WorkflowLinter`
    - :class:`omnibase_core.models.validation.model_lint_warning.ModelLintWarning`
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelLintStatistics"]


class ModelLintStatistics(BaseModel):
    """
    Immutable statistics model for workflow linting telemetry.

    This model captures telemetry data from a workflow linting operation,
    including warning distribution by code and severity, timing information,
    and workflow size metrics. It is designed for observability and
    performance monitoring.

    The model is frozen (immutable) for thread safety and to prevent
    accidental modification of statistics after creation.

    Attributes:
        workflow_name: Name of the workflow that was linted.
        total_warnings: Total number of warnings produced.
        warnings_by_code: Count of warnings grouped by warning code.
        warnings_by_severity: Count of warnings grouped by severity level.
        step_count: Number of steps in the workflow.
        lint_duration_ms: Time taken to lint the workflow in milliseconds.
        timestamp: When the linting operation was performed.

    Example:
        Creating statistics after linting::

            stats = ModelLintStatistics(
                workflow_name="data_pipeline",
                total_warnings=3,
                warnings_by_code={"W003": 2, "W005": 1},
                warnings_by_severity={"warning": 3, "info": 0},
                step_count=15,
                lint_duration_ms=8.2,
            )

            # Analyze results
            if stats.has_critical_warnings():
                print("Critical issues detected!")
            print(f"Warnings per step: {stats.get_warnings_per_step():.2f}")
    """

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=False,
        validate_assignment=True,
        frozen=True,
        from_attributes=True,  # pytest-xdist compatibility
    )

    workflow_name: str = Field(
        ...,
        description="Name of the workflow that was linted.",
        min_length=1,
    )

    total_warnings: int = Field(
        ...,
        description="Total number of warnings produced during linting.",
        ge=0,
    )

    warnings_by_code: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Count of warnings grouped by warning code. "
            "Keys are warning codes (e.g., 'W001'), values are counts."
        ),
    )

    warnings_by_severity: dict[str, int] = Field(
        default_factory=lambda: {"warning": 0, "info": 0},
        description=(
            "Count of warnings grouped by severity level. "
            "Keys are 'warning' or 'info', values are counts."
        ),
    )

    step_count: int = Field(
        ...,
        description="Number of steps in the workflow that was linted.",
        ge=0,
    )

    lint_duration_ms: float = Field(
        ...,
        description="Time taken to lint the workflow, in milliseconds.",
        ge=0.0,
    )

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the linting operation was performed.",
    )

    def get_warnings_per_step(self) -> float:
        """
        Calculate the average number of warnings per workflow step.

        Returns:
            float: Average warnings per step, or 0.0 if no steps.

        Example:
            >>> stats = ModelLintStatistics(
            ...     workflow_name="test",
            ...     total_warnings=10,
            ...     step_count=5,
            ...     lint_duration_ms=1.0,
            ... )
            >>> stats.get_warnings_per_step()
            2.0
        """
        if self.step_count == 0:
            return 0.0
        return self.total_warnings / self.step_count

    def get_most_common_warning_code(self) -> str | None:
        """
        Get the warning code that occurred most frequently.

        Returns:
            str | None: The most common warning code, or None if no warnings.

        Example:
            >>> stats = ModelLintStatistics(
            ...     workflow_name="test",
            ...     total_warnings=5,
            ...     warnings_by_code={"W001": 3, "W002": 2},
            ...     step_count=10,
            ...     lint_duration_ms=1.0,
            ... )
            >>> stats.get_most_common_warning_code()
            'W001'
        """
        if not self.warnings_by_code:
            return None
        return max(self.warnings_by_code, key=lambda k: self.warnings_by_code[k])

    def has_critical_warnings(self) -> bool:
        """
        Check if the workflow has any critical warning patterns.

        Critical warnings are:
        - W003 (unreachable steps): Indicates broken dependency chains
        - W005 (isolated steps): Indicates disconnected workflow components

        Returns:
            bool: True if critical warnings exist, False otherwise.

        Example:
            >>> stats = ModelLintStatistics(
            ...     workflow_name="test",
            ...     total_warnings=2,
            ...     warnings_by_code={"W003": 1, "W001": 1},
            ...     step_count=5,
            ...     lint_duration_ms=1.0,
            ... )
            >>> stats.has_critical_warnings()
            True
        """
        critical_codes = {"W003", "W005"}
        return any(code in critical_codes for code in self.warnings_by_code)

    def is_clean(self) -> bool:
        """
        Check if the workflow linting produced no warnings.

        Returns:
            bool: True if no warnings were produced, False otherwise.

        Example:
            >>> stats = ModelLintStatistics(
            ...     workflow_name="clean_workflow",
            ...     total_warnings=0,
            ...     step_count=5,
            ...     lint_duration_ms=1.0,
            ... )
            >>> stats.is_clean()
            True
        """
        return self.total_warnings == 0
