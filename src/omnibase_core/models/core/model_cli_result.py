"""
CLI Result Model - ONEX Standards Compliant.

Universal CLI execution result model that captures the complete
outcome of CLI command execution with comprehensive error handling,
validation, and performance metrics.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports:
- omnibase_core.errors.error_codes (imports only from types.core_types and enums)
- omnibase_core.models.core.model_cli_execution (no circular risk)
- omnibase_core.models.core.model_cli_output_data (no circular risk)
- omnibase_core.models.core.model_duration (no circular risk)
- omnibase_core.models.validation.model_validation_error (no circular risk)
- pydantic, typing, datetime (standard library)

Import Chain Position:
1. errors.error_codes → types.core_types
2. THIS MODULE → errors.error_codes (OK - no circle)
3. types.constraints → TYPE_CHECKING import of errors.error_codes
4. models.* → types.constraints

This module can safely import error_codes because error_codes only imports
from types.core_types (not from models or types.constraints).
"""

from datetime import UTC, datetime
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.models.core.model_cli_execution import ModelCliExecution
from omnibase_core.models.core.model_cli_output_data import ModelCliOutputData
from omnibase_core.models.core.model_duration import ModelDuration

# Safe runtime import - error_codes only imports from types.core_types
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.validation.model_validation_error import ModelValidationError


class ModelCliResult(BaseModel):
    """
    Enterprise-grade CLI execution result model with comprehensive error handling,
    validation, and performance metrics.

    This model captures the complete outcome of CLI command execution
    including success/failure, output data, errors, and performance metrics.
    Implements omnibase_spi protocols:
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    execution: ModelCliExecution = Field(
        default=...,
        description="Execution details and context",
    )

    success: bool = Field(default=..., description="Whether execution was successful")

    exit_code: int = Field(
        default=...,
        description="Process exit code (0 = success, >0 = error)",
        ge=0,
        le=255,
    )

    output_data: ModelCliOutputData = Field(
        default_factory=lambda: ModelCliOutputData(
            message=None,
            status=None,
            nodes=None,
            node_info=None,
            node_metadata=None,
            registry_count=None,
            registry_status=None,
            validation_passed=None,
            test_results=None,
            scenario_name=None,
            scenario_status=None,
            config_details=None,
            files_processed=None,
            files_created=None,
            files_modified=None,
            count=None,
            total=None,
            processed=None,
            failed=None,
            skipped=None,
            custom_fields=None,
            raw_data=None,
        ),
        description="Structured output data from execution",
    )

    output_text: str | None = Field(
        default=None, description="Human-readable output text"
    )

    error_message: str | None = Field(
        default=None,
        description="Primary error message if execution failed",
        max_length=1000,
    )

    error_details: str | None = Field(
        default=None,
        description="Detailed error information",
        max_length=5000,
    )

    validation_errors: list[ModelValidationError] = Field(
        default_factory=list,
        description="Validation errors encountered",
    )

    warnings: list[str] = Field(
        default_factory=list,
        description="Warning messages",
    )

    execution_time: ModelDuration = Field(
        default=..., description="Total execution time"
    )

    end_time: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Execution completion time",
    )

    retry_count: int = Field(
        default=0,
        description="Number of retries attempted",
        ge=0,
    )

    performance_metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Performance metrics and timing data",
    )

    debug_info: dict[str, Any] = Field(
        default_factory=dict,
        description="Debug information (only included if debug enabled)",
    )

    trace_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Trace data (only included if tracing enabled)",
    )

    result_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional result metadata",
    )

    model_config = ConfigDict(
        extra="ignore",
        arbitrary_types_allowed=True,
        use_enum_values=False,
        validate_assignment=True,
    )

    def is_success(self) -> bool:
        """Check if execution was successful."""
        return self.success and self.exit_code == 0

    def is_failure(self) -> bool:
        """Check if execution failed."""
        return not self.success or self.exit_code != 0

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return self.error_message is not None or len(self.validation_errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0

    def has_critical_errors(self) -> bool:
        """Check if there are any critical validation errors."""
        return any(error.is_critical() for error in self.validation_errors)

    def get_duration_ms(self) -> int:
        """Get execution duration in milliseconds."""
        return self.execution_time.total_milliseconds()

    def get_duration_seconds(self) -> float:
        """Get execution duration in seconds."""
        return self.execution_time.total_seconds()

    def get_primary_error(self) -> str | None:
        """Get the primary error message."""
        if self.error_message:
            return self.error_message
        if self.validation_errors:
            critical_errors = [e for e in self.validation_errors if e.is_critical()]
            if critical_errors:
                return critical_errors[0].message
            return self.validation_errors[0].message
        return None

    def get_all_errors(self) -> list[str]:
        """Get all error messages."""
        errors = []
        if self.error_message:
            errors.append(self.error_message)
        for validation_error in self.validation_errors:
            errors.append(validation_error.message)
        return errors

    def get_critical_errors(self) -> list[ModelValidationError]:
        """Get all critical validation errors."""
        return [error for error in self.validation_errors if error.is_critical()]

    def get_non_critical_errors(self) -> list[ModelValidationError]:
        """Get all non-critical validation errors."""
        return [error for error in self.validation_errors if not error.is_critical()]

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        if warning not in self.warnings:
            self.warnings.append(warning)

    def add_validation_error(self, error: ModelValidationError) -> None:
        """Add a validation error."""
        self.validation_errors.append(error)

    def add_performance_metric(self, name: str, value: Any) -> None:
        """Add a performance metric."""
        self.performance_metrics[name] = value

    def add_debug_info(self, key: str, value: Any) -> None:
        """Add debug information."""
        if self.execution.is_debug_enabled():
            self.debug_info[key] = value

    def add_trace_data(self, key: str, value: Any) -> None:
        """Add trace data."""
        if self.execution.is_trace_enabled():
            self.trace_data[key] = value

    def add_metadata(self, key: str, value: Any) -> None:
        """Add result metadata."""
        self.result_metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get result metadata."""
        return self.result_metadata.get(key, default)

    def get_output_value(self, key: str, default: Any = None) -> Any:
        """Get a specific output value."""
        return self.output_data.get_field_value(key, default)

    def set_output_value(self, key: str, value: Any) -> None:
        """Set a specific output value."""
        self.output_data.set_field_value(key, value)

    def get_formatted_output(self) -> str:
        """Get formatted output for display."""
        if self.output_text:
            return self.output_text

        if self.output_data:
            # Try to format structured data nicely
            import json

            try:
                return json.dumps(self.output_data.to_dict(), indent=2, default=str)
            except (TypeError, ValueError):
                return str(self.output_data)

        return ""

    def get_summary(self) -> dict[str, Any]:
        """Get result summary for logging/monitoring."""
        return {
            "execution_id": str(self.execution.execution_id),
            "command": self.execution.get_command_name(),
            "target_node": self.execution.get_target_node_name(),
            "success": self.success,
            "exit_code": self.exit_code,
            "duration_ms": self.get_duration_ms(),
            "retry_count": self.retry_count,
            "has_errors": self.has_errors(),
            "has_warnings": self.has_warnings(),
            "error_count": len(self.validation_errors),
            "warning_count": len(self.warnings),
            "critical_error_count": len(self.get_critical_errors()),
            "primary_error": self.get_primary_error(),
            "end_time": self.end_time.isoformat(),
            "is_dry_run": self.execution.is_dry_run,
            "is_test": self.execution.is_test_execution,
        }

    @classmethod
    def create_success(
        cls,
        execution: ModelCliExecution,
        output_data: dict[str, Any] | ModelCliOutputData | None = None,
        output_text: str | None = None,
        execution_time: ModelDuration | None = None,
    ) -> Self:
        """Create a successful result."""
        if execution_time is None:
            execution_time = ModelDuration(milliseconds=execution.get_elapsed_ms())

        # Mark execution as completed
        execution.mark_completed()

        # Convert dict[str, Any] to ModelCliOutputData if needed
        if output_data is None:
            output_data = ModelCliOutputData(
                message=None,
                status=None,
                nodes=None,
                node_info=None,
                node_metadata=None,
                registry_count=None,
                registry_status=None,
                validation_passed=None,
                test_results=None,
                scenario_name=None,
                scenario_status=None,
                config_details=None,
                files_processed=None,
                files_created=None,
                files_modified=None,
                count=None,
                total=None,
                processed=None,
                failed=None,
                skipped=None,
                custom_fields=None,
                raw_data=None,
            )
        elif isinstance(output_data, dict):
            # Create ModelCliOutputData with required fields
            output_data = ModelCliOutputData(
                message=output_data.get("message"),
                status=output_data.get("status"),
                nodes=output_data.get("nodes"),
                node_info=output_data.get("node_info"),
                node_metadata=output_data.get("node_metadata"),
                registry_count=output_data.get("registry_count"),
                registry_status=output_data.get("registry_status"),
                validation_passed=output_data.get("validation_passed"),
                test_results=output_data.get("test_results"),
                scenario_name=output_data.get("scenario_name"),
                scenario_status=output_data.get("scenario_status"),
                config_details=output_data.get("config_details"),
                files_processed=output_data.get("files_processed"),
                files_created=output_data.get("files_created"),
                files_modified=output_data.get("files_modified"),
                count=output_data.get("count"),
                total=output_data.get("total"),
                processed=output_data.get("processed"),
                failed=output_data.get("failed"),
                skipped=output_data.get("skipped"),
                custom_fields=output_data.get("custom_fields"),
                raw_data=output_data.get("raw_data"),
            )

        return cls(
            execution=execution,
            success=True,
            exit_code=0,
            output_data=output_data,
            output_text=output_text,
            error_message=None,
            error_details=None,
            execution_time=execution_time,
        )

    @classmethod
    def create_failure(
        cls,
        execution: ModelCliExecution,
        error_message: str,
        exit_code: int = 1,
        error_details: str | None = None,
        validation_errors: list[ModelValidationError] | None = None,
        execution_time: ModelDuration | None = None,
    ) -> Self:
        """Create a failure result."""
        if execution_time is None:
            execution_time = ModelDuration(milliseconds=execution.get_elapsed_ms())

        # Mark execution as completed
        execution.mark_completed()

        return cls(
            execution=execution,
            success=False,
            exit_code=exit_code,
            output_data=ModelCliOutputData(
                message=None,
                status=None,
                nodes=None,
                node_info=None,
                node_metadata=None,
                registry_count=None,
                registry_status=None,
                validation_passed=None,
                test_results=None,
                scenario_name=None,
                scenario_status=None,
                config_details=None,
                files_processed=None,
                files_created=None,
                files_modified=None,
                count=None,
                total=None,
                processed=None,
                failed=None,
                skipped=None,
                custom_fields=None,
                raw_data=None,
            ),  # Default empty output data
            output_text=None,
            error_message=error_message,
            error_details=error_details,
            validation_errors=validation_errors or [],
            execution_time=execution_time,
        )

    @classmethod
    def create_validation_failure(
        cls,
        execution: ModelCliExecution,
        validation_errors: list[ModelValidationError],
        execution_time: ModelDuration | None = None,
    ) -> Self:
        """Create a result for validation failures."""
        if execution_time is None:
            execution_time = ModelDuration(milliseconds=execution.get_elapsed_ms())

        # Mark execution as completed
        execution.mark_completed()

        primary_error = (
            validation_errors[0].message if validation_errors else "Validation failed"
        )

        return cls(
            execution=execution,
            success=False,
            exit_code=2,  # Exit code 2 for validation errors
            output_data=ModelCliOutputData(
                message=None,
                status=None,
                nodes=None,
                node_info=None,
                node_metadata=None,
                registry_count=None,
                registry_status=None,
                validation_passed=None,
                test_results=None,
                scenario_name=None,
                scenario_status=None,
                config_details=None,
                files_processed=None,
                files_created=None,
                files_modified=None,
                count=None,
                total=None,
                processed=None,
                failed=None,
                skipped=None,
                custom_fields=None,
                raw_data=None,
            ),  # Default empty output data
            output_text=None,
            error_message=primary_error,
            error_details=None,
            validation_errors=validation_errors,
            execution_time=execution_time,
        )
