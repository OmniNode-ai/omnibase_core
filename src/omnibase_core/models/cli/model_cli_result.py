"""
CLI Result Model.

Universal CLI execution result model that captures the complete
outcome of CLI command execution with proper typing.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_config_category import EnumConfigCategory
from omnibase_core.models.cli.model_cli_performance_metrics import (
    ModelPerformanceMetrics,
)
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.infrastructure.model_duration import ModelDuration
from omnibase_core.models.validation.model_validation_error import ModelValidationError
from omnibase_core.types.type_serializable_value import SerializedDict

from .model_cli_debug_info import ModelCliDebugInfo
from .model_cli_execution import ModelCliExecution
from .model_cli_output_data import ModelCliOutputData
from .model_cli_result_metadata import ModelCliResultMetadata
from .model_result_summary import ModelResultSummary
from .model_trace_data import ModelTraceData


class ModelCliResult(BaseModel):
    """
    Universal CLI execution result model.

    This model captures the complete outcome of CLI command execution
    including success/failure, output data, errors, and performance metrics.
    Properly typed for MyPy compliance.
    Implements Core protocols:
    - Serializable: Data serialization/deserialization
    - Nameable: Name management interface
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
            stdout="",
            stderr="",
            execution_time_ms=0.0,
            memory_usage_mb=0.0,
        ),
        description="Structured output data from execution",
    )

    output_text: str = Field(default="", description="Human-readable output text")

    error_message: str | None = Field(
        default=None,
        description="Primary error message if execution failed",
    )

    error_details: str = Field(default="", description="Detailed error information")

    validation_errors: list[ModelValidationError] = Field(
        default_factory=list,
        description="Validation errors encountered",
    )

    warnings: list[str] = Field(default_factory=list, description="Warning messages")

    execution_time: ModelDuration = Field(
        default=..., description="Total execution time"
    )

    end_time: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Execution completion time",
    )

    retry_count: int = Field(default=0, description="Number of retries attempted", ge=0)

    performance_metrics: ModelPerformanceMetrics | None = Field(
        default=None,
        description="Performance metrics and timing data",
    )

    debug_info: ModelCliDebugInfo | None = Field(
        default=None,
        description="Debug information",
    )

    trace_data: ModelTraceData | None = Field(
        default=None,
        description="Trace data",
    )

    result_metadata: ModelCliResultMetadata | None = Field(
        default=None,
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
        if self.error_message is not None:
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
        if self.error_message is not None:
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
        value: object,
        unit: str = "",
        category: EnumConfigCategory = EnumConfigCategory.GENERAL,
    ) -> None:
        """Add a performance metric with proper typing."""
        # Create performance metrics if not exists
        if self.performance_metrics is None:
            self.performance_metrics = ModelPerformanceMetrics(
                execution_time_ms=0.0,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                io_operations=0,
                network_calls=0,
            )

        # Add through the performance metrics model's typed interface
        if hasattr(self.performance_metrics, "add_metric"):
            self.performance_metrics.add_metric(name, value, unit, category)

    def add_debug_info(self, key: str, value: object) -> None:
        """Add debug information with proper typing."""
        if self.execution.is_debug_enabled:
            # Create debug info if not exists
            if self.debug_info is None:
                self.debug_info = ModelCliDebugInfo()

            # Pass value directly - set_custom_field handles type conversion
            schema_value = ModelSchemaValue.from_value(value)
            self.debug_info.set_custom_field(key, schema_value.to_value())

    def add_trace_data(
        self,
        key: str,
        value: object,
        operation: str = "",
    ) -> None:
        """Add trace data with proper typing."""
        # Create trace data if not exists
        if self.trace_data is None:
            now = datetime.now(UTC)
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

    def add_metadata(self, key: str, value: object) -> None:
        """Add result metadata with proper typing."""
        # Create result metadata if not exists
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

        # Pass value directly - set_custom_field handles type conversion
        schema_value = ModelSchemaValue.from_value(value)
        self.result_metadata.set_custom_field(key, schema_value.to_value())

    def get_metadata(self, key: str, default: object = None) -> object:
        """Get result metadata with proper typing."""
        if self.result_metadata is None:
            return default

        # Get ModelValue - provide a default ModelValue for empty string
        from omnibase_core.models.infrastructure.model_value import ModelValue

        default_cli_value = ModelValue.from_string(
            str(default) if default is not None else "",
        )
        cli_value = self.result_metadata.get_custom_field(key, default_cli_value)

        if cli_value is not None:
            # Convert ModelValue to Python value
            python_value = cli_value.to_python_value()
            value_str = str(python_value)

            # Simple type conversion based on default type
            if isinstance(default, bool):
                return value_str.lower() in ("true", "1", "yes", "on")
            if isinstance(default, int):
                try:
                    return int(value_str)
                except (TypeError, ValueError):
                    return default
            if isinstance(default, float):
                try:
                    return float(value_str)
                except (TypeError, ValueError):
                    return default
            return value_str

        return default

    def get_typed_metadata(
        self,
        key: str,
        field_type: type[object],
        default: object,
    ) -> object:
        """Get result metadata with specific type checking."""
        if self.result_metadata is None:
            return default
        value = self.result_metadata.get_custom_field(key)
        if value is not None and isinstance(value, field_type):
            return value
        return default

    def get_output_value(
        self,
        key: str,
        default: object = None,
    ) -> object:
        """Get a specific output value with proper typing."""
        value = self.output_data.get_field_value(
            key,
            str(default) if default is not None else "",
        )
        # Simple type conversion based on default type
        if value is not None and value != "":
            if isinstance(default, bool):
                return value.lower() in ("true", "1", "yes", "on")
            if isinstance(default, int):
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return default
            if isinstance(default, float):
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return default
            return value
        return default

    def set_output_value(self, key: str, value: object) -> None:
        """Set a specific output value with proper typing."""
        # Convert value to string for storage
        self.output_data.set_field_value(key, str(value))

    def get_formatted_output(self) -> str:
        """Get formatted output for display."""
        from omnibase_core.utils.util_cli_result_formatter import UtilCliResultFormatter

        return UtilCliResultFormatter.format_output(self.output_text, self.output_data)

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
            error_level_count=len(self.validation_errors),
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
        # Use provided execution time or calculate from execution
        if execution_time is None:
            execution_time_final = ModelDuration(
                milliseconds=execution.get_elapsed_ms(),
            )
        else:
            execution_time_final = execution_time

        # Mark execution as completed
        execution.mark_completed()

        # Use provided output data or create empty one
        if output_data is None:
            output_data_obj = ModelCliOutputData(
                stdout="",
                stderr="",
                execution_time_ms=0.0,
                memory_usage_mb=0.0,
            )
        else:
            output_data_obj = output_data

        output_text_final = output_text if output_text is not None else ""

        return cls(
            execution=execution,
            success=True,
            exit_code=0,
            output_data=output_data_obj,
            performance_metrics=None,
            trace_data=None,
            output_text=output_text_final,
            error_message=None,
            error_details="",
            debug_info=None,
            result_metadata=None,
            execution_time=execution_time_final,
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
        # Use provided execution time or calculate from execution
        if execution_time is None:
            execution_time_final = ModelDuration(
                milliseconds=execution.get_elapsed_ms(),
            )
        else:
            execution_time_final = execution_time

        # Mark execution as completed
        execution.mark_completed()

        error_details_final = error_details if error_details is not None else ""
        validation_errors_final = (
            validation_errors if validation_errors is not None else []
        )

        return cls(
            execution=execution,
            success=False,
            exit_code=exit_code,
            error_message=error_message,
            error_details=error_details_final,
            validation_errors=validation_errors_final,
            output_text="",
            debug_info=None,
            result_metadata=None,
            execution_time=execution_time_final,
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
        # Use provided execution time or calculate from execution
        if execution_time is None:
            execution_time_final = ModelDuration(
                milliseconds=execution.get_elapsed_ms(),
            )
        else:
            execution_time_final = execution_time

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
            error_details="",
            validation_errors=validation_errors,
            output_text="",
            debug_info=None,
            result_metadata=None,
            execution_time=execution_time_final,
            performance_metrics=None,
            trace_data=None,
        )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def get_name(self) -> str:
        """Get name (Nameable protocol)."""
        # Try common name field patterns
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        return f"Unnamed {self.__class__.__name__}"

    def set_name(self, name: str) -> None:
        """Set name (Nameable protocol)."""
        # Try to set the most appropriate name field
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                setattr(self, field, name)
                return

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Raises:
            Exception: If validation logic fails
        """
        # Basic validation - ensure required fields exist
        # Override in specific models for custom validation
        return True


# Export for use
__all__ = ["ModelCliResult"]
