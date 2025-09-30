"""
CLI Result Model.

Universal CLI execution result model that captures the complete
outcome of CLI command execution with proper typing.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_config_category import EnumConfigCategory
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.infrastructure.model_duration import ModelDuration
from omnibase_core.models.validation.model_validation_error import ModelValidationError

from .model_cli_debug_info import ModelCliDebugInfo
from .model_cli_execution import ModelCliExecution
from .model_cli_output_data import ModelCliOutputData
from .model_cli_result_metadata import ModelCliResultMetadata
from .model_performance_metrics import ModelPerformanceMetrics
from .model_result_summary import ModelResultSummary
from .model_trace_data import ModelTraceData

# Removed Any import - using object for ONEX compliance


class ModelCliResult(BaseModel):
    """
    Universal CLI execution result model.

    This model captures the complete outcome of CLI command execution
    including success/failure, output data, errors, and performance metrics.
    Properly typed for MyPy compliance.
    Implements omnibase_spi protocols:
    - Serializable: Data serialization/deserialization
    - Nameable: Name management interface
    - Validatable: Validation and verification
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
            stdout="",
            stderr="",
            execution_time_ms=0.0,
            memory_usage_mb=0.0,
        ),
        description="Structured output data from execution",
    )

    output_text: str = Field(default="", description="Human-readable output text")

    error_message: ModelSchemaValue = Field(
        default_factory=lambda: ModelSchemaValue.from_value(None),
        description="Primary error message if execution failed (string or null)",
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

    performance_metrics: ModelSchemaValue = Field(
        default_factory=lambda: ModelSchemaValue.from_value(None),
        description="Performance metrics and timing data (ModelPerformanceMetrics or null)",
    )

    debug_info: ModelSchemaValue = Field(
        default_factory=lambda: ModelSchemaValue.from_value(None),
        description="Debug information (ModelCliDebugInfo or null)",
    )

    trace_data: ModelSchemaValue = Field(
        default_factory=lambda: ModelSchemaValue.from_value(None),
        description="Trace data (ModelTraceData or null)",
    )

    result_metadata: ModelSchemaValue = Field(
        default_factory=lambda: ModelSchemaValue.from_value(None),
        description="Additional result metadata (ModelCliResultMetadata or null)",
    )

    def is_success(self) -> bool:
        """Check if execution was successful."""
        return self.success and self.exit_code == 0

    def is_failure(self) -> bool:
        """Check if execution failed."""
        return not self.success or self.exit_code != 0

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        # Check if error_message is not null
        error_msg_value = self.error_message.to_value()
        return error_msg_value is not None or len(self.validation_errors) > 0

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

    def get_primary_error(self) -> ModelSchemaValue:
        """Get the primary error message."""
        error_msg_value = self.error_message.to_value()
        if error_msg_value is not None:
            return self.error_message
        if self.validation_errors:
            critical_errors = [e for e in self.validation_errors if e.is_critical()]
            if critical_errors:
                return ModelSchemaValue.from_value(str(critical_errors[0].message))
            return ModelSchemaValue.from_value(str(self.validation_errors[0].message))
        return ModelSchemaValue.from_value(None)

    def get_all_errors(self) -> list[str]:
        """Get all error messages."""
        errors: list[str] = []
        error_msg_value = self.error_message.to_value()
        if error_msg_value is not None:
            errors.append(str(error_msg_value))
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
        # Performance metrics are now strongly typed - use proper model
        perf_metrics_value = self.performance_metrics.to_value()
        if perf_metrics_value is None:
            perf_metrics = ModelPerformanceMetrics(
                execution_time_ms=0.0,
                memory_usage_mb=0.0,  # Use default value instead of None
                cpu_usage_percent=0.0,  # Use default value instead of None
                io_operations=0,  # Use default value instead of None
                network_calls=0,  # Use default value instead of None
            )
            self.performance_metrics = ModelSchemaValue.from_value(perf_metrics)
        # Type check the extracted value
        elif isinstance(perf_metrics_value, ModelPerformanceMetrics):
            perf_metrics = perf_metrics_value
        else:
            # Create new if type is wrong
            perf_metrics = ModelPerformanceMetrics(
                execution_time_ms=0.0,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                io_operations=0,
                network_calls=0,
            )
            self.performance_metrics = ModelSchemaValue.from_value(perf_metrics)
        # Add through the performance metrics model's typed interface
        if hasattr(perf_metrics, "add_metric"):
            perf_metrics.add_metric(name, value, unit, category)

    def add_debug_info(self, key: str, value: object) -> None:
        """Add debug information with proper typing."""
        if self.execution.is_debug_enabled:
            debug_info_value = self.debug_info.to_value()
            if debug_info_value is None:
                debug_info = ModelCliDebugInfo()
                self.debug_info = ModelSchemaValue.from_value(debug_info)
            # Type check the extracted value
            elif isinstance(debug_info_value, ModelCliDebugInfo):
                debug_info = debug_info_value
            else:
                # Create new if type is wrong
                debug_info = ModelCliDebugInfo()
                self.debug_info = ModelSchemaValue.from_value(debug_info)
            # Convert value to ModelSchemaValue for proper typing
            schema_value = ModelSchemaValue.from_value(value)
            debug_info.set_custom_field(key, str(schema_value.to_value()))

    def add_trace_data(
        self,
        key: str,
        value: object,
        operation: str = "",
    ) -> None:
        """Add trace data with proper typing."""
        trace_data_value = self.trace_data.to_value()
        if trace_data_value is None:
            from datetime import UTC, datetime
            from uuid import uuid4

            now = datetime.now(UTC)
            trace_data = ModelTraceData(
                trace_id=uuid4(),
                span_id=uuid4(),
                parent_span_id=None,
                start_time=now,
                end_time=now,
                duration_ms=0.0,
            )
            self.trace_data = ModelSchemaValue.from_value(trace_data)
        # Type check the extracted value
        elif isinstance(trace_data_value, ModelTraceData):
            trace_data = trace_data_value
        else:
            # Create new if type is wrong
            from datetime import UTC, datetime
            from uuid import uuid4

            now = datetime.now(UTC)
            trace_data = ModelTraceData(
                trace_id=uuid4(),
                span_id=uuid4(),
                parent_span_id=None,
                start_time=now,
                end_time=now,
                duration_ms=0.0,
            )
            self.trace_data = ModelSchemaValue.from_value(trace_data)
        # Add through the trace data model's typed interface
        if hasattr(trace_data, "add_trace_info"):
            trace_data.add_trace_info(key, value, operation)

    def add_metadata(self, key: str, value: object) -> None:
        """Add result metadata with proper typing."""
        result_metadata_value = self.result_metadata.to_value()
        if result_metadata_value is None:
            result_metadata = ModelCliResultMetadata(
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
            self.result_metadata = ModelSchemaValue.from_value(result_metadata)
        # Type check the extracted value
        elif isinstance(result_metadata_value, ModelCliResultMetadata):
            result_metadata = result_metadata_value
        else:
            # Create new if type is wrong
            result_metadata = ModelCliResultMetadata(
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
            self.result_metadata = ModelSchemaValue.from_value(result_metadata)
        # Convert value to ModelSchemaValue for proper typing
        schema_value = ModelSchemaValue.from_value(value)
        # TODO: Fix the signature mismatch - set_custom_field expects ModelCliValue, not str
        from omnibase_core.models.infrastructure.model_cli_value import ModelCliValue

        result_metadata.set_custom_field(
            key,
            ModelCliValue.from_string(str(schema_value.to_value())),
        )

    def get_metadata(self, key: str, default: object = None) -> object:
        """Get result metadata with proper typing."""
        result_metadata_value = self.result_metadata.to_value()
        if result_metadata_value is None or not isinstance(
            result_metadata_value,
            ModelCliResultMetadata,
        ):
            return default

        # Get ModelCliValue - provide a default ModelCliValue for empty string
        from omnibase_core.models.infrastructure.model_cli_value import ModelCliValue

        default_cli_value = ModelCliValue.from_string(
            str(default) if default is not None else "",
        )
        cli_value = result_metadata_value.get_custom_field(key, default_cli_value)

        if cli_value is not None:
            # Convert ModelCliValue to Python value
            python_value = cli_value.to_python_value()
            value_str = str(python_value)

            if value_str != "":
                # Convert string value to match the type of default
                if isinstance(default, bool):
                    return value_str.lower() in ("true", "1", "yes", "on")
                if isinstance(default, int):
                    try:
                        return int(value_str)
                    except ValueError:
                        return default
                elif isinstance(default, float):
                    try:
                        return float(value_str)
                    except ValueError:
                        return default
                else:  # str
                    return value_str
        return default

    def get_typed_metadata(
        self,
        key: str,
        field_type: type[object],
        default: object,
    ) -> object:
        """Get result metadata with specific type checking."""
        result_metadata_value = self.result_metadata.to_value()
        if result_metadata_value is None or not isinstance(
            result_metadata_value,
            ModelCliResultMetadata,
        ):
            return default
        value = result_metadata_value.get_custom_field(key)
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
        if value is not None and value != "":
            # Convert string value to match the type of default
            if isinstance(default, bool):
                return value.lower() in ("true", "1", "yes", "on")
            if isinstance(default, int):
                try:
                    return int(value)
                except ValueError:
                    return default
            elif isinstance(default, float):
                try:
                    return float(value)
                except ValueError:
                    return default
            else:  # str
                return value
        return default

    def set_output_value(self, key: str, value: object) -> None:
        """Set a specific output value with proper typing."""
        # Convert value to ModelSchemaValue for proper typing
        schema_value = ModelSchemaValue.from_value(value)
        self.output_data.set_field_value(key, str(schema_value.to_value()))

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
        output_data: ModelSchemaValue = ModelSchemaValue.from_value(None),
        output_text: ModelSchemaValue = ModelSchemaValue.from_value(None),
        execution_time: ModelSchemaValue = ModelSchemaValue.from_value(None),
    ) -> ModelCliResult:
        """Create a successful result."""
        execution_time_value = execution_time.to_value()
        if execution_time_value is None:
            execution_time_final = ModelDuration(
                milliseconds=execution.get_elapsed_ms(),
            )
        # Type check the extracted value
        elif isinstance(execution_time_value, ModelDuration):
            execution_time_final = execution_time_value
        else:
            execution_time_final = ModelDuration(
                milliseconds=execution.get_elapsed_ms(),
            )

        # Mark execution as completed
        execution.mark_completed()

        # Use provided output data or create empty one
        output_data_value = output_data.to_value()
        if output_data_value is not None and isinstance(
            output_data_value,
            ModelCliOutputData,
        ):
            output_data_obj = output_data_value
        else:
            output_data_obj = ModelCliOutputData(
                stdout="",
                stderr="",
                execution_time_ms=0.0,
                memory_usage_mb=0.0,
            )

        output_text_value = output_text.to_value()
        output_text_final = (
            str(output_text_value) if output_text_value is not None else ""
        )

        return cls(
            execution=execution,
            success=True,
            exit_code=0,
            output_data=output_data_obj,
            performance_metrics=ModelSchemaValue.from_value(None),
            trace_data=ModelSchemaValue.from_value(None),
            output_text=output_text_final,
            error_message=ModelSchemaValue.from_value(None),
            error_details="",
            debug_info=ModelSchemaValue.from_value(None),
            result_metadata=ModelSchemaValue.from_value(None),
            execution_time=execution_time_final,
        )

    @classmethod
    def create_failure(
        cls,
        execution: ModelCliExecution,
        error_message: str,
        exit_code: int = 1,
        error_details: ModelSchemaValue = ModelSchemaValue.from_value(None),
        validation_errors: ModelSchemaValue = ModelSchemaValue.from_value(None),
        execution_time: ModelSchemaValue = ModelSchemaValue.from_value(None),
    ) -> ModelCliResult:
        """Create a failure result."""
        execution_time_value = execution_time.to_value()
        if execution_time_value is None:
            execution_time_final = ModelDuration(
                milliseconds=execution.get_elapsed_ms(),
            )
        # Type check the extracted value
        elif isinstance(execution_time_value, ModelDuration):
            execution_time_final = execution_time_value
        else:
            execution_time_final = ModelDuration(
                milliseconds=execution.get_elapsed_ms(),
            )

        # Mark execution as completed
        execution.mark_completed()

        error_details_value = error_details.to_value()
        error_details_final = (
            str(error_details_value) if error_details_value is not None else ""
        )

        validation_errors_value = validation_errors.to_value()
        if validation_errors_value is not None and isinstance(
            validation_errors_value,
            list,
        ):
            validation_errors_final = validation_errors_value
        else:
            validation_errors_final = []

        return cls(
            execution=execution,
            success=False,
            exit_code=exit_code,
            error_message=ModelSchemaValue.from_value(error_message),
            error_details=error_details_final,
            validation_errors=validation_errors_final,
            output_text="",
            debug_info=ModelSchemaValue.from_value(None),
            result_metadata=ModelSchemaValue.from_value(None),
            execution_time=execution_time_final,
            performance_metrics=ModelSchemaValue.from_value(None),
            trace_data=ModelSchemaValue.from_value(None),
        )

    @classmethod
    def create_validation_failure(
        cls,
        execution: ModelCliExecution,
        validation_errors: list[ModelValidationError],
        execution_time: ModelSchemaValue = ModelSchemaValue.from_value(None),
    ) -> ModelCliResult:
        """Create a result for validation failures."""
        execution_time_value = execution_time.to_value()
        if execution_time_value is None:
            execution_time_final = ModelDuration(
                milliseconds=execution.get_elapsed_ms(),
            )
        # Type check the extracted value
        elif isinstance(execution_time_value, ModelDuration):
            execution_time_final = execution_time_value
        else:
            execution_time_final = ModelDuration(
                milliseconds=execution.get_elapsed_ms(),
            )

        # Mark execution as completed
        execution.mark_completed()

        primary_error = (
            validation_errors[0].message if validation_errors else "Validation failed"
        )

        return cls(
            execution=execution,
            success=False,
            exit_code=2,  # Exit code 2 for validation errors
            error_message=ModelSchemaValue.from_value(primary_error),
            error_details="",
            validation_errors=validation_errors,
            output_text="",
            debug_info=ModelSchemaValue.from_value(None),
            result_metadata=ModelSchemaValue.from_value(None),
            execution_time=execution_time_final,
            performance_metrics=ModelSchemaValue.from_value(None),
            trace_data=ModelSchemaValue.from_value(None),
        )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def serialize(self) -> dict[str, Any]:
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
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
            return False


# Export for use
__all__ = ["ModelCliResult"]
