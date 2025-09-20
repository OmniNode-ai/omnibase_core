"""
Examples demonstrating how ModelValidationContainer standardizes validation
across all domains, replacing scattered validation patterns.

This file shows:
1. Current scattered validation patterns in CLI models
2. How to refactor using ModelValidationContainer
3. Benefits of the unified approach
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from src.omnibase_core.models.cli.model_cli_execution import ModelCliExecution
from src.omnibase_core.models.cli.model_cli_output_data import ModelCliOutputData
from src.omnibase_core.models.infrastructure.model_duration import ModelDuration
from src.omnibase_core.models.metadata.model_generic_metadata import ModelGenericMetadata
from src.omnibase_core.models.validation.model_validation_container import (
    ModelValidationContainer,
    ValidatedModel,
)
from src.omnibase_core.models.validation.model_validation_error import ModelValidationError


# =============================================================================
# BEFORE: Scattered validation patterns (current approach)
# =============================================================================

class ModelCliResultBefore(BaseModel):
    """Current CLI result model with scattered validation logic."""

    execution: ModelCliExecution = Field(..., description="Execution details")
    success: bool = Field(..., description="Whether execution was successful")
    exit_code: int = Field(..., description="Process exit code", ge=0, le=255)

    # SCATTERED VALIDATION FIELDS - Different patterns across models
    validation_errors: list[ModelValidationError] = Field(
        default_factory=list,
        description="Validation errors encountered",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Warning messages"
    )

    # MANUAL VALIDATION METHODS - Duplicated across models
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.validation_errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0

    def has_critical_errors(self) -> bool:
        """Check if there are any critical validation errors."""
        return any(error.is_critical() for error in self.validation_errors)

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        if warning not in self.warnings:
            self.warnings.append(warning)

    def add_validation_error(self, error: ModelValidationError) -> None:
        """Add a validation error."""
        self.validation_errors.append(error)


class ModelWorkflowResultBefore(BaseModel):
    """Example workflow model with different validation pattern."""

    workflow_id: str = Field(..., description="Workflow identifier")
    status: str = Field(..., description="Workflow status")

    # DIFFERENT VALIDATION PATTERN - Inconsistent with CLI model
    errors: list[str] = Field(default_factory=list, description="Error messages")
    validation_issues: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Validation issues"
    )
    warnings: list[str] = Field(default_factory=list, description="Warnings")

    # DIFFERENT METHOD NAMES - No standardization
    def is_valid(self) -> bool:
        return len(self.errors) == 0 and len(self.validation_issues) == 0

    def get_error_count(self) -> int:
        return len(self.errors) + len(self.validation_issues)


# =============================================================================
# AFTER: Unified validation with ModelValidationContainer
# =============================================================================

class ModelCliResultAfter(ValidatedModel):
    """
    Refactored CLI result model using ModelValidationContainer.

    Benefits:
    - Standardized validation interface
    - Consistent error aggregation
    - Reduced code duplication
    - Better type safety
    """

    execution: ModelCliExecution = Field(..., description="Execution details")
    success: bool = Field(..., description="Whether execution was successful")
    exit_code: int = Field(..., description="Process exit code", ge=0, le=255)

    # NO MORE SCATTERED VALIDATION FIELDS
    # ValidationContainer provides: errors, warnings, and all methods

    def validate_model_data(self) -> None:
        """Custom validation logic using the container."""
        # Validate exit code consistency
        if self.success and self.exit_code != 0:
            self.validation.add_error(
                "Success flag is True but exit_code is not 0",
                field="exit_code",
                error_code="INCONSISTENT_EXIT_CODE"
            )

        if not self.success and self.exit_code == 0:
            self.validation.add_error(
                "Success flag is False but exit_code is 0",
                field="success",
                error_code="INCONSISTENT_SUCCESS_FLAG"
            )

        # Add performance warnings
        if hasattr(self.execution, 'get_elapsed_ms'):
            elapsed_ms = self.execution.get_elapsed_ms()
            if elapsed_ms > 30000:  # 30 seconds
                self.validation.add_warning(
                    f"Execution took {elapsed_ms}ms, consider optimization"
                )


class ModelWorkflowResultAfter(ValidatedModel):
    """
    Refactored workflow model using the same validation standard.

    Now consistent with CLI model and all other models.
    """

    workflow_id: str = Field(..., description="Workflow identifier")
    status: str = Field(..., description="Workflow status")

    # NO MORE SCATTERED VALIDATION FIELDS
    # Uses inherited validation container

    def validate_model_data(self) -> None:
        """Custom validation logic using the standard container."""
        # Validate workflow ID format
        if not self.workflow_id.startswith(("wf_", "workflow_")):
            self.validation.add_error(
                "Workflow ID must start with 'wf_' or 'workflow_'",
                field="workflow_id",
                error_code="INVALID_WORKFLOW_ID_FORMAT"
            )

        # Validate status
        valid_statuses = ["pending", "running", "completed", "failed", "cancelled"]
        if self.status not in valid_statuses:
            self.validation.add_critical_error(
                f"Invalid status '{self.status}'. Must be one of: {valid_statuses}",
                field="status",
                error_code="INVALID_STATUS"
            )

        # Add warnings for certain statuses
        if self.status == "running":
            self.validation.add_warning(
                "Workflow is still running, results may be incomplete"
            )


# =============================================================================
# Usage Examples showing the benefits
# =============================================================================

def demonstrate_usage():
    """Demonstrate the usage patterns and benefits."""

    print("=== ModelValidationContainer Usage Examples ===\n")

    # Create sample execution
    execution = ModelCliExecution(
        execution_id="exec_123",
        command_args=["test", "command"],
        target_node="test_node",
    )

    # Example 1: CLI Result with validation
    print("1. CLI Result Validation:")
    cli_result = ModelCliResultAfter(
        execution=execution,
        success=True,
        exit_code=1,  # Inconsistent - will generate error
    )

    # Perform validation
    is_valid = cli_result.perform_validation()
    print(f"   Is valid: {is_valid}")
    print(f"   Summary: {cli_result.get_validation_summary()}")
    print(f"   Errors: {cli_result.validation.get_all_error_messages()}")
    print()

    # Example 2: Workflow Result with validation
    print("2. Workflow Result Validation:")
    workflow_result = ModelWorkflowResultAfter(
        workflow_id="invalid_id",  # Invalid format
        status="invalid_status",   # Invalid status
    )

    workflow_result.perform_validation()
    print(f"   Is valid: {workflow_result.is_valid()}")
    print(f"   Summary: {workflow_result.get_validation_summary()}")
    print(f"   Critical errors: {workflow_result.validation.get_critical_error_count()}")
    print()

    # Example 3: Manual validation container usage
    print("3. Manual Validation Container Usage:")
    container = ModelValidationContainer()

    # Add various types of validation issues
    container.add_error("Field validation failed", field="field1", error_code="FIELD_INVALID")
    container.add_critical_error("Critical system error", error_code="SYSTEM_ERROR")
    container.add_warning("Performance warning")
    container.add_warning("Configuration recommendation")

    print(f"   Error count: {container.get_error_count()}")
    print(f"   Critical errors: {container.get_critical_error_count()}")
    print(f"   Warning count: {container.get_warning_count()}")
    print(f"   Summary: {container.get_error_summary()}")
    print(f"   Dictionary format: {container.to_dict()}")
    print()

    # Example 4: Merging validation results
    print("4. Merging Validation Results:")
    container1 = ModelValidationContainer()
    container1.add_error("Error from system A")
    container1.add_warning("Warning from system A")

    container2 = ModelValidationContainer()
    container2.add_critical_error("Critical error from system B")
    container2.add_warning("Warning from system B")

    # Merge results
    merged = ModelValidationContainer()
    merged.merge_from(container1)
    merged.merge_from(container2)

    print(f"   Merged summary: {merged.get_error_summary()}")
    print(f"   Total errors: {merged.get_error_count()}")
    print(f"   All warnings: {merged.warnings}")


# =============================================================================
# Benefits Summary
# =============================================================================

"""
BENEFITS OF ModelValidationContainer:

1. STANDARDIZATION:
   - All models use the same validation interface
   - Consistent method names across domains
   - Unified error/warning collection

2. REDUCED CODE DUPLICATION:
   - No more copying validation methods
   - Single source of truth for validation logic
   - Inheritance provides standard functionality

3. BETTER TYPE SAFETY:
   - Strongly typed validation errors
   - MyPy compliance out of the box
   - Structured error information

4. ENHANCED FUNCTIONALITY:
   - Error categorization (critical vs normal)
   - Field-specific error tracking
   - Error code support for programmatic handling
   - Validation result merging

5. CONSISTENT REPORTING:
   - Standardized error summaries
   - Unified dictionary serialization
   - Consistent error counting

6. EXTENSIBILITY:
   - Easy to add new validation features
   - Custom validation in subclasses
   - Flexible error details structure

MIGRATION PATH:

Current patterns to replace:
- validation_errors: List[ModelValidationError] → validation: ModelValidationContainer
- warnings: List[str] → validation.warnings (accessed via container)
- errors: List[str] → validation.errors (with proper error objects)
- Custom has_errors() methods → validation.has_errors()
- Custom validation logic → validate_model_data() override

Examples in codebase:
- ModelCliResult.validation_errors → ModelCliResult.validation.errors
- All add_validation_error() methods → validation.add_error()
- All has_errors() methods → validation.has_errors()
- Custom error counting → validation.get_error_count()
"""


if __name__ == "__main__":
    demonstrate_usage()