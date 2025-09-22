"""
CLI Result Model.

Universal CLI execution result model that captures the complete
outcome of CLI command execution with proper typing.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TypeVar

# Type variable for generic metadata access
T = TypeVar("T")
# Type variable for metadata value types
MetadataValueType = TypeVar("MetadataValueType", str, int, float, bool)

# For methods that need to return a specific type from union, we'll use Any with runtime checking
from typing import Any, cast

from pydantic import BaseModel, Field

from ...enums.enum_config_category import EnumConfigCategory
from ..infrastructure.model_duration import ModelDuration
from ..validation.model_validation_error import ModelValidationError
from .model_cli_debug_info import ModelCliDebugInfo
from .model_cli_execution import ModelCliExecution
from .model_cli_output_data import ModelCliOutputData
from .model_cli_result_metadata import ModelCliResultMetadata
from .model_performance_metrics import ModelPerformanceMetrics
from .model_result_summary import ModelResultSummary
from .model_trace_data import ModelTraceData


class ModelCliResult(BaseModel):
    """
    Universal CLI execution result model.

    This model captures the complete outcome of CLI command execution
    including success/failure, output data, errors, and performance metrics.
    Properly typed for MyPy compliance.
    """

    execution: ModelCliExecution = Field(
        ...,
        description="Execution details and context",
    )

    success: bool = Field(..., description="Whether execution was successful")

    exit_code: int = Field(
        ...,
        description="Process exit code (0 = success, >0 = error)",
        ge=0,
        le=255,
    )

    output_data: ModelCliOutputData = Field(
        default_factory=lambda: ModelCliOutputData(
            stdout=None, stderr=None, execution_time_ms=None, memory_usage_mb=None
        ),
        description="Structured output data from execution",
    )

    output_text: str = Field(default="", description="Human-readable output text")

    error_message: str | None = Field(
        None,
        description="Primary error message if execution failed",
    )

    error_details: str = Field(default="", description="Detailed error information")

    validation_errors: list[ModelValidationError] = Field(
        default_factory=list,
        description="Validation errors encountered",
    )

    warnings: list[str] = Field(default_factory=list, description="Warning messages")

    execution_time: ModelDuration = Field(..., description="Total execution time")

    end_time: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Execution completion time",
    )

    retry_count: int = Field(default=0, description="Number of retries attempted", ge=0)

    performance_metrics: ModelPerformanceMetrics | None = Field(
        None,
        description="Performance metrics and timing data",
    )

    debug_info: ModelCliDebugInfo | None = Field(
        None,
        description="Debug information (only included if debug enabled)",
    )

    trace_data: ModelTraceData | None = Field(
        None,
        description="Trace data (only included if tracing enabled)",
    )

    result_metadata: ModelCliResultMetadata | None = Field(
        None,
        description="Additional result metadata",
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
        return int(self.execution_time.total_milliseconds())

    def get_duration_seconds(self) -> float:
        """Get execution duration in seconds."""
        return float(self.execution_time.total_seconds())

    def get_primary_error(self) -> str | None:
        """Get the primary error message."""
        if self.error_message:
            return self.error_message
        if self.validation_errors:
            critical_errors = [e for e in self.validation_errors if e.is_critical()]
            if critical_errors:
                return str(critical_errors[0].message)
            return str(self.validation_errors[0].message)
        return None

    def get_all_errors(self) -> list[str]:
        """Get all error messages."""
        errors: list[str] = []
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

    def add_performance_metric(
        self,
        name: str,
        value: T,
        unit: str = "",
        category: EnumConfigCategory = EnumConfigCategory.GENERAL,
    ) -> None:
        """Add a performance metric with proper typing."""
        # Performance metrics are now strongly typed - use proper model
        if self.performance_metrics is None:
            from .model_performance_metrics import ModelPerformanceMetrics

            self.performance_metrics = ModelPerformanceMetrics(
                execution_time_ms=0.0,
                memory_usage_mb=None,
                cpu_usage_percent=None,
                io_operations=None,
                network_calls=None,
            )
        # Add through the performance metrics model's typed interface
        if hasattr(self.performance_metrics, "add_metric"):
            self.performance_metrics.add_metric(name, value, unit, category)

    def add_debug_info(self, key: str, value: MetadataValueType) -> None:
        """Add debug information with proper typing."""
        if self.execution.config.is_debug_enabled:
            if self.debug_info is None:
                self.debug_info = ModelCliDebugInfo()
            self.debug_info.set_custom_field(key, value)

    def add_trace_data(
        self, key: str, value: MetadataValueType, operation: str = ""
    ) -> None:
        """Add trace data with proper typing."""
        if self.trace_data is None:
            from datetime import UTC, datetime
            from uuid import uuid4

            now = datetime.now(UTC).isoformat()
            self.trace_data = ModelTraceData(
                trace_id=uuid4(),
                span_id=uuid4(),
                parent_span_id=None,
                start_time=now,
                end_time=now,
                duration_ms=0.0,
            )
        # Add through the trace data model's typed interface
        if hasattr(self.trace_data, "add_trace_info"):
            self.trace_data.add_trace_info(key, value, operation)

    def add_metadata(self, key: str, value: MetadataValueType) -> None:
        """Add result metadata with proper typing."""
        if self.result_metadata is None:
            self.result_metadata = ModelCliResultMetadata(
                metadata_version=None,
                result_category=None,
                source_command=None,
                source_node=None,
                processor_version=None,
                quality_score=None,
                confidence_level=None,
                retention_policy=None,
                processing_time_ms=None,
            )
        self.result_metadata.set_custom_field(key, value)

    def get_metadata(self, key: str, default: MetadataValueType) -> MetadataValueType:
        """Get result metadata with proper typing."""
        if self.result_metadata is None:
            return default
        value = self.result_metadata.get_custom_field(key, default)
        return cast(MetadataValueType, value if value is not None else default)

    def get_typed_metadata(self, key: str, field_type: type[T], default: T) -> T:
        """Get result metadata with specific type checking."""
        if self.result_metadata is None:
            return default
        value = self.result_metadata.get_custom_field(key)
        if value is not None and isinstance(value, field_type):
            return value
        return default

    def get_output_value(
        self, key: str, default: MetadataValueType
    ) -> MetadataValueType:
        """Get a specific output value with proper typing."""
        value = self.output_data.get_field_value(key, default)
        return cast(MetadataValueType, value if value is not None else default)

    def set_output_value(self, key: str, value: MetadataValueType) -> None:
        """Set a specific output value with proper typing."""
        self.output_data.set_field_value(key, value)

    def get_formatted_output(self) -> str:
        """Get formatted output for display."""
        if self.output_text:
            return self.output_text

        if self.output_data:
            # Try to format structured data nicely
            import json

            try:
                return json.dumps(self.output_data.model_dump(), indent=2, default=str)
            except (TypeError, ValueError):
                return str(self.output_data)

        return ""

    def get_summary(self) -> ModelResultSummary:
        """Get result summary for logging/monitoring."""
        return ModelResultSummary(
            execution_id=self.execution.execution_id,
            command=self.execution.get_command_name(),
            target_node=self.execution.get_target_node_name(),
            success=self.success,
            exit_code=self.exit_code,
            duration_ms=self.get_duration_ms(),
            retry_count=self.retry_count,
            has_errors=self.has_errors(),
            has_warnings=self.has_warnings(),
            error_count=len(self.validation_errors),
            warning_count=len(self.warnings),
            critical_error_count=len(self.get_critical_errors()),
        )

    @classmethod
    def create_success(
        cls,
        execution: ModelCliExecution,
        output_data: ModelCliOutputData | None = None,
        output_text: str | None = None,
        execution_time: ModelDuration | None = None,
    ) -> ModelCliResult:
        """Create a successful result."""
        if execution_time is None:
            execution_time = ModelDuration(milliseconds=execution.get_elapsed_ms())

        # Mark execution as completed
        execution.mark_completed()

        # Use provided output data or create empty one
        output_data_obj = output_data or ModelCliOutputData(
            stdout=None, stderr=None, execution_time_ms=None, memory_usage_mb=None
        )

        return cls(
            execution=execution,
            success=True,
            exit_code=0,
            output_data=output_data_obj,
            performance_metrics=None,
            trace_data=None,
            output_text=output_text,
            error_message=None,
            error_details=None,
            debug_info=None,
            result_metadata=None,
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
    ) -> ModelCliResult:
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
            output_text=None,
            debug_info=None,
            result_metadata=None,
            execution_time=execution_time,
            performance_metrics=None,
            trace_data=None,
        )

    @classmethod
    def create_validation_failure(
        cls,
        execution: ModelCliExecution,
        validation_errors: list[ModelValidationError],
        execution_time: ModelDuration | None = None,
    ) -> ModelCliResult:
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
            error_details=None,
            validation_errors=validation_errors,
            output_text=None,
            debug_info=None,
            result_metadata=None,
            execution_time=execution_time,
            performance_metrics=None,
            trace_data=None,
        )


# Export for use
__all__ = ["ModelCliResult"]
