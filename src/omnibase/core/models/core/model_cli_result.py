"""
CLI Result Model

Universal CLI execution result model that captures the complete
outcome of CLI command execution.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from omnibase.model.core.model_cli_execution import ModelCliExecution
from omnibase.model.core.model_cli_output_data import ModelCliOutputData
from omnibase.model.core.model_duration import ModelDuration
from omnibase.model.validation.model_validation_error import ModelValidationError


class ModelCliResult(BaseModel):
    """
    Universal CLI execution result model.

    This model captures the complete outcome of CLI command execution
    including success/failure, output data, errors, and performance metrics.
    """

    execution: ModelCliExecution = Field(
        ..., description="Execution details and context"
    )

    success: bool = Field(..., description="Whether execution was successful")

    exit_code: int = Field(
        ..., description="Process exit code (0 = success, >0 = error)", ge=0, le=255
    )

    output_data: ModelCliOutputData = Field(
        default_factory=ModelCliOutputData,
        description="Structured output data from execution",
    )

    output_text: Optional[str] = Field(None, description="Human-readable output text")

    error_message: Optional[str] = Field(
        None, description="Primary error message if execution failed"
    )

    error_details: Optional[str] = Field(None, description="Detailed error information")

    validation_errors: List[ModelValidationError] = Field(
        default_factory=list, description="Validation errors encountered"
    )

    warnings: List[str] = Field(default_factory=list, description="Warning messages")

    execution_time: ModelDuration = Field(..., description="Total execution time")

    end_time: datetime = Field(
        default_factory=datetime.utcnow, description="Execution completion time"
    )

    retry_count: int = Field(default=0, description="Number of retries attempted", ge=0)

    performance_metrics: Dict[str, Any] = Field(
        default_factory=dict, description="Performance metrics and timing data"
    )

    debug_info: Dict[str, Any] = Field(
        default_factory=dict,
        description="Debug information (only included if debug enabled)",
    )

    trace_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Trace data (only included if tracing enabled)",
    )

    result_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional result metadata"
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

    def get_primary_error(self) -> Optional[str]:
        """Get the primary error message."""
        if self.error_message:
            return self.error_message
        if self.validation_errors:
            critical_errors = [e for e in self.validation_errors if e.is_critical()]
            if critical_errors:
                return critical_errors[0].message
            return self.validation_errors[0].message
        return None

    def get_all_errors(self) -> List[str]:
        """Get all error messages."""
        errors = []
        if self.error_message:
            errors.append(self.error_message)
        for validation_error in self.validation_errors:
            errors.append(validation_error.message)
        return errors

    def get_critical_errors(self) -> List[ModelValidationError]:
        """Get all critical validation errors."""
        return [error for error in self.validation_errors if error.is_critical()]

    def get_non_critical_errors(self) -> List[ModelValidationError]:
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

    def get_summary(self) -> Dict[str, Any]:
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
        output_data: Optional[Dict[str, Any]] = None,
        output_text: Optional[str] = None,
        execution_time: Optional[ModelDuration] = None,
    ) -> "ModelCliResult":
        """Create a successful result."""
        if execution_time is None:
            execution_time = ModelDuration(milliseconds=execution.get_elapsed_ms())

        # Mark execution as completed
        execution.mark_completed()

        # Convert dict to ModelCliOutputData if needed
        if output_data is not None and not isinstance(output_data, ModelCliOutputData):
            output_data = ModelCliOutputData.from_dict(output_data)
        elif output_data is None:
            output_data = ModelCliOutputData()

        return cls(
            execution=execution,
            success=True,
            exit_code=0,
            output_data=output_data,
            output_text=output_text,
            execution_time=execution_time,
        )

    @classmethod
    def create_failure(
        cls,
        execution: ModelCliExecution,
        error_message: str,
        exit_code: int = 1,
        error_details: Optional[str] = None,
        validation_errors: Optional[List[ModelValidationError]] = None,
        execution_time: Optional[ModelDuration] = None,
    ) -> "ModelCliResult":
        """Create a failure result."""
        if execution_time is None:
            execution_time = ModelDuration(milliseconds=execution.get_elapsed_ms())

        # Mark execution as completed
        execution.mark_completed()

        return cls(
            execution=execution,
            success=False,
            exit_code=exit_code,
            error_message=error_message,
            error_details=error_details,
            validation_errors=validation_errors or [],
            execution_time=execution_time,
        )

    @classmethod
    def create_validation_failure(
        cls,
        execution: ModelCliExecution,
        validation_errors: List[ModelValidationError],
        execution_time: Optional[ModelDuration] = None,
    ) -> "ModelCliResult":
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
            error_message=primary_error,
            validation_errors=validation_errors,
            execution_time=execution_time,
        )
