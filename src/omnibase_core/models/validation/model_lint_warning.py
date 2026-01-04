"""
Lint warning model for workflow contract validation.

This module provides the ModelLintWarning model used by the WorkflowContractLinter
to report non-semantic validation issues such as unused configurations, duplicate
names, unreachable steps, and priority clamping.

Note on naming:
    This module intentionally uses "ModelLintWarning" rather than a name containing
    "ValidationError" to avoid confusion with pydantic.ValidationError. The "Lint"
    prefix clearly indicates this is for static analysis/linting, not runtime
    validation errors.

    Why "LintWarning" and not "ValidationError":
        1. pydantic.ValidationError is a standard exception in the Pydantic ecosystem
           that users expect to represent model validation failures at runtime
        2. Using a similar name (e.g., "ValidationWarning") could cause import
           confusion and cognitive overhead when debugging
        3. "Lint" is industry-standard terminology (ESLint, pylint, flake8) that
           clearly signals static analysis rather than runtime validation
        4. This separation allows ModelOnexError to be used for actual validation
           failures while ModelLintWarning remains purely informational

Example:
    Basic usage for creating lint warnings::

        from omnibase_core.models.validation.model_lint_warning import ModelLintWarning

        # Step-specific warning
        warning = ModelLintWarning(
            code="W001",
            message="parallel_group is ignored in SEQUENTIAL mode",
            step_reference="550e8400-e29b-41d4-a716-446655440000",
            severity="warning",
        )

        # Workflow-level warning (no specific step)
        warning = ModelLintWarning(
            code="W002",
            message="Duplicate step name 'process_data' found (2 occurrences)",
            step_reference=None,
            severity="info",
        )

Warning Codes:
    - W001: Unused parallel_group configuration in SEQUENTIAL mode
    - W002: Duplicate step names detected
    - W003: Unreachable steps (depend on non-existent steps)
    - W004: Priority values that will be clamped (outside [1, 1000])
    - W005: Isolated steps (no incoming or outgoing edges)

See Also:
    - :class:`omnibase_core.validation.checker_workflow_linter.WorkflowLinter`
    - :class:`omnibase_core.models.validation.model_validation_error.ModelValidationError`
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelLintWarning"]


class ModelLintWarning(BaseModel):
    """
    Immutable linting warning for workflow contract static analysis.

    This model represents a single warning detected during workflow linting.
    Warnings are informational only and do NOT affect workflow execution or
    prevent workflows from running. They serve as hints for potential issues
    or suboptimal configurations.

    This class is intentionally named "ModelLintWarning" rather than anything
    containing "ValidationError" to avoid confusion with pydantic.ValidationError,
    which is used for runtime model validation. Lint warnings are for static
    analysis only.

    The model is frozen (immutable) for thread safety and to prevent accidental
    modification of warning data after creation.

    Attributes:
        code: Standardized warning code (e.g., 'W001', 'W002').
            Used for programmatic filtering and categorization.
        message: Human-readable description of the warning.
            Should clearly explain the issue and potential consequences.
        step_reference: UUID string of the affected step, or None for
            workflow-level warnings that don't apply to a specific step.
        severity: Warning severity level. "warning" indicates potential
            issues that may cause unexpected behavior; "info" indicates
            suggestions or informational notices.

    Example:
        Creating a step-specific warning::

            warning = ModelLintWarning(
                code="W004",
                message="Step 'heavy_compute' has priority 1500 which exceeds "
                        "maximum (1000) - will be clamped to 1000",
                step_reference="550e8400-e29b-41d4-a716-446655440000",
                severity="warning",
            )

        Creating a workflow-level warning::

            warning = ModelLintWarning(
                code="W002",
                message="Duplicate step name 'process_data' found (2 occurrences)",
                step_reference=None,
                severity="info",
            )

    Note:
        This model is frozen (immutable). Attempting to modify attributes
        after creation will raise a ValidationError.
    """

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
        frozen=True,
        from_attributes=True,  # pytest-xdist compatibility
    )

    code: str = Field(
        ...,
        description=(
            "Standardized warning code (e.g., 'W001'). "
            "Used for programmatic filtering and categorization of warnings."
        ),
        min_length=1,
        max_length=20,
    )

    message: str = Field(
        ...,
        description=(
            "Human-readable warning message explaining the issue "
            "and its potential consequences."
        ),
        min_length=1,
    )

    step_reference: str | None = Field(
        default=None,
        description=(
            "UUID string of the affected workflow step, or None for "
            "workflow-level warnings that don't apply to a specific step."
        ),
    )

    severity: Literal["info", "warning"] = Field(
        default="warning",
        description=(
            "Warning severity level. 'warning' indicates potential issues "
            "that may cause unexpected behavior at runtime; 'info' indicates "
            "suggestions or informational notices that are less urgent."
        ),
    )
