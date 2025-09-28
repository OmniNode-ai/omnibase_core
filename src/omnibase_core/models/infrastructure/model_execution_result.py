"""
Enhanced Execution Result Model.

Unified execution result pattern that extends Result[T, E] with
timing, metadata, and execution tracking capabilities.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar, cast
from uuid import UUID, uuid4

from pydantic import Field

from omnibase_core.core.type_constraints import Configurable
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.exceptions.onex_error import OnexError
from omnibase_core.models.core.model_custom_properties import ModelCustomProperties

from .model_cli_result_data import ModelCliResultData
from .model_cli_value import ModelCliValue
from .model_duration import ModelDuration
from .model_execution_summary import ModelExecutionSummary
from .model_result import ModelResult

# Type variables for execution result pattern
T = TypeVar("T")  # Success type
E = TypeVar("E")  # Error type
# Type variable for metadata value types
MetadataValueType = TypeVar("MetadataValueType", str, int, float, bool)


class ModelExecutionResult(ModelResult[T, E], Generic[T, E]):
    """
    Enhanced result for execution operations with timing and metadata.

    Extends the base Result[T, E] pattern with execution-specific features:
    - Execution tracking and timing
    - Warning collection
    - Metadata storage
    - CLI execution result formatting
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    """

    execution_id: UUID = Field(
        default_factory=uuid4,
        description="Unique execution identifier",
    )

    start_time: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Execution start time",
    )

    end_time: datetime | None = Field(None, description="Execution end time")

    duration: ModelDuration | None = Field(
        None,
        description="Execution duration",
    )

    warnings: list[str] = Field(
        default_factory=list,
        description="Warning messages collected during execution",
    )

    metadata: ModelCustomProperties = Field(
        default_factory=lambda: ModelCustomProperties(),
        description="Execution metadata and context",
    )

    def __init__(self, **data: Any) -> None:
        """Initialize execution result with proper timing setup."""
        if "success" in data and "value" not in data and "error" not in data:
            if data["success"]:
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="Success result must have a value",
                )
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Error result must have an error",
            )

        super().__init__(**data)

    @classmethod
    def ok(
        cls,
        value: T,
        execution_id: UUID | None = None,
        metadata: ModelCustomProperties | None = None,
        **kwargs: Any,
    ) -> ModelExecutionResult[T, E]:
        """Create a successful execution result."""
        return cls(
            success=True,
            value=value,
            error=None,
            execution_id=execution_id or uuid4(),
            metadata=metadata or ModelCustomProperties(),
            **kwargs,
        )

    @classmethod
    def err(
        cls,
        error: E,
        execution_id: UUID | None = None,
        metadata: ModelCustomProperties | None = None,
        **kwargs: Any,
    ) -> ModelExecutionResult[T, E]:
        """Create an error execution result."""
        return cls(
            success=False,
            value=None,
            error=error,
            execution_id=execution_id or uuid4(),
            metadata=metadata or ModelCustomProperties(),
            **kwargs,
        )

    @classmethod
    def create_cli_success(
        cls,
        output_data: Any,
        execution_id: UUID | None = None,
        tool_name: str | None = None,
        **kwargs: Any,
    ) -> ModelExecutionResult[Any, str]:
        """
        Create successful CLI execution result.
        """
        metadata = kwargs.pop("metadata", ModelCustomProperties())
        if not isinstance(metadata, ModelCustomProperties):
            # Convert dict to ModelCustomProperties if needed
            metadata = ModelCustomProperties.from_metadata(metadata)
        if tool_name:
            metadata.set_custom_string("tool_name", tool_name)

        # Create instance with explicit type parameters
        instance = cls(
            success=True,
            value=output_data,
            error=None,
            execution_id=execution_id or uuid4(),
            metadata=metadata,
            **kwargs,
        )
        return instance  # type: ignore[return-value]

    @classmethod
    def create_cli_failure(
        cls,
        error_message: str,
        execution_id: UUID | None = None,
        tool_name: str | None = None,
        status_code: int = 1,
        **kwargs: Any,
    ) -> ModelExecutionResult[Any, str]:
        """
        Create failed CLI execution result.
        """
        metadata = kwargs.pop("metadata", ModelCustomProperties())
        if not isinstance(metadata, ModelCustomProperties):
            # Convert dict to ModelCustomProperties if needed
            metadata = ModelCustomProperties.from_metadata(metadata)
        if tool_name:
            metadata.set_custom_string("tool_name", tool_name)
        metadata.set_custom_number("status_code", float(status_code))

        # Create instance with explicit type parameters
        instance = cls(
            success=False,
            value=None,
            error=error_message,
            execution_id=execution_id or uuid4(),
            metadata=metadata,
            **kwargs,
        )
        return instance  # type: ignore[return-value]

    @classmethod
    def create_cli_success_with_output_data(
        cls,
        output_data: Any = None,
        tool_id: UUID | None = None,
        tool_display_name: str | None = None,
        execution_time_ms: float | None = None,
        **kwargs: Any,
    ) -> ModelExecutionResult[Any, str]:
        """
        Create successful CLI execution result with ModelCliExecutionResult compatibility.

        This method provides full compatibility with ModelCliExecutionResult.create_success()
        while leveraging the enhanced capabilities of ModelExecutionResult.

        Args:
            output_data: Tool execution output (any type)
            tool_id: UUID of executed tool
            tool_display_name: Human-readable name of executed tool
            execution_time_ms: Execution duration
            **kwargs: Additional fields

        Returns:
            Success result instance with CLI compatibility
        """
        metadata = kwargs.pop("metadata", ModelCustomProperties())
        if not isinstance(metadata, ModelCustomProperties):
            metadata = ModelCustomProperties.from_metadata(metadata)

        if tool_display_name:
            metadata.set_custom_string("tool_display_name", tool_display_name)
        if tool_id:
            metadata.set_custom_string("tool_id", str(tool_id))
        if execution_time_ms is not None:
            metadata.set_custom_number("execution_time_ms", float(execution_time_ms))

        instance = cls(
            success=True,
            value=output_data,
            error=None,
            execution_id=kwargs.pop("execution_id", uuid4()),
            metadata=metadata,
            **kwargs,
        )
        return instance  # type: ignore[return-value]

    @classmethod
    def create_cli_error_with_output_data(
        cls,
        error_message: str,
        tool_id: UUID | None = None,
        tool_display_name: str | None = None,
        status_code: int = 1,
        output_data: Any = None,
        **kwargs: Any,
    ) -> ModelExecutionResult[Any, str]:
        """
        Create error CLI execution result with ModelCliExecutionResult compatibility.

        This method provides full compatibility with ModelCliExecutionResult.create_error()
        while leveraging the enhanced capabilities of ModelExecutionResult.

        Args:
            error_message: Description of the error
            tool_id: UUID of tool that failed
            tool_display_name: Human-readable name of tool that failed
            status_code: Numeric error code
            output_data: Any partial output data
            **kwargs: Additional fields

        Returns:
            Error result instance with CLI compatibility
        """
        metadata = kwargs.pop("metadata", ModelCustomProperties())
        if not isinstance(metadata, ModelCustomProperties):
            metadata = ModelCustomProperties.from_metadata(metadata)

        if tool_display_name:
            metadata.set_custom_string("tool_display_name", tool_display_name)
        if tool_id:
            metadata.set_custom_string("tool_id", str(tool_id))
        metadata.set_custom_number("status_code", float(status_code))

        instance = cls(
            success=False,
            value=output_data,  # Allow partial output data on errors
            error=error_message,
            execution_id=kwargs.pop("execution_id", uuid4()),
            metadata=metadata,
            **kwargs,
        )
        return instance  # type: ignore[return-value]

    def add_warning(self, warning: str) -> None:
        """Add a warning message if not already present."""
        if warning not in self.warnings:
            self.warnings.append(warning)

    def add_warnings(self, warnings: list[str]) -> None:
        """Add multiple warning messages."""
        for warning in warnings:
            self.add_warning(warning)

    def add_metadata(self, key: str, value: MetadataValueType) -> None:
        """Add metadata entry."""
        from omnibase_core.models.common.model_schema_value import ModelSchemaValue

        self.metadata.set_custom_value(key, ModelSchemaValue.from_value(value))

    def get_metadata(self, key: str, default: MetadataValueType) -> MetadataValueType:
        """Get metadata entry with optional default."""
        value = self.metadata.get_custom_value(key)
        return cast(MetadataValueType, value if value is not None else default)

    def mark_completed(self) -> None:
        """Mark execution as completed and calculate duration."""
        if self.end_time is None:
            self.end_time = datetime.now(UTC)

        if self.duration is None:
            elapsed = self.end_time - self.start_time
            self.duration = ModelDuration(
                milliseconds=int(elapsed.total_seconds() * 1000),
            )

    def get_duration_ms(self) -> int | None:
        """Get execution duration in milliseconds."""
        if self.duration is not None:
            return self.duration.total_milliseconds()

        # Calculate from timestamps if duration not set
        if self.end_time is not None:
            elapsed = self.end_time - self.start_time
            return int(elapsed.total_seconds() * 1000)

        return None

    def get_duration_seconds(self) -> float | None:
        """Get execution duration in seconds."""
        duration_ms = self.get_duration_ms()
        return duration_ms / 1000.0 if duration_ms is not None else None

    def has_warnings(self) -> bool:
        """Check if execution has any warnings."""
        return len(self.warnings) > 0

    def is_completed(self) -> bool:
        """Check if execution is marked as completed."""
        return self.end_time is not None

    def get_execution_summary(self) -> ModelExecutionSummary:
        """Get a summary of execution details."""
        return ModelExecutionSummary(
            execution_id=self.execution_id,
            success=self.success,
            duration_ms=self.get_duration_ms(),
            warning_count=len(self.warnings),
            has_metadata=not self.metadata.is_empty(),
            completed=self.is_completed(),
        )

    def to_cli_result(self) -> ModelCliResultData:
        """
        Convert to CLI result data format.
        """
        # Convert value to CLI value object for type safety
        cli_value: ModelCliValue | None = None
        if self.success and self.value is not None:
            cli_value = ModelCliValue.from_any(self.value)

        return ModelCliResultData(
            success=self.success,
            execution_id=self.execution_id,
            output_data=cli_value,
            error_message=(
                str(self.error) if not self.success and self.error is not None else None
            ),
            tool_id=None,  # Default to None if no tool_id metadata available
            tool_display_name=(
                str(self.get_metadata("tool_name", ""))
                if self.get_metadata("tool_name", "")
                else None
            ),
            execution_time_ms=self.get_duration_ms(),
            status_code=int(
                self.get_metadata("status_code", 0 if self.success else 1)
                or (0 if self.success else 1),
            ),
            warnings=self.warnings,
            metadata=self.metadata,
        )

    def __repr__(self) -> str:
        """Enhanced string representation with execution details."""
        base_repr = super().__repr__()
        duration_info = f" (duration: {self.duration})" if self.duration else ""
        warning_info = f" ({len(self.warnings)} warnings)" if self.warnings else ""
        return f"{base_repr}{duration_info}{warning_info}"

    # Protocol method implementations

    def execute(self, **kwargs: Any) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:
            return False

    def configure(self, **kwargs: Any) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:
            return False

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


# Convenience type aliases for common execution result patterns


# Factory functions for common execution patterns
def execution_ok(
    value: T,
    execution_id: UUID | None = None,
    tool_name: str | None = None,
    **kwargs: Any,
) -> ModelExecutionResult[T, str]:
    """Create successful execution result with optional tool context."""
    metadata = kwargs.pop("metadata", ModelCustomProperties())
    if not isinstance(metadata, ModelCustomProperties):
        # Convert dict to ModelCustomProperties if needed
        metadata = ModelCustomProperties.from_metadata(metadata)
    if tool_name:
        metadata.set_custom_string("tool_name", tool_name)

    return ModelExecutionResult.ok(
        value,
        execution_id=execution_id,
        metadata=metadata,
        **kwargs,
    )


def execution_err(
    error: str,
    execution_id: UUID | None = None,
    tool_name: str | None = None,
    status_code: int = 1,
    **kwargs: Any,
) -> ModelExecutionResult[Any, str]:
    """Create error execution result with optional tool context."""
    metadata = kwargs.pop("metadata", ModelCustomProperties())
    if not isinstance(metadata, ModelCustomProperties):
        # Convert dict to ModelCustomProperties if needed
        metadata = ModelCustomProperties.from_metadata(metadata)
    if tool_name:
        metadata.set_custom_string("tool_name", tool_name)
    if status_code != 1:
        metadata.set_custom_number("status_code", float(status_code))

    return ModelExecutionResult.err(
        error,
        execution_id=execution_id,
        metadata=metadata,
        **kwargs,
    )


def try_execution(
    f: Callable[[], Any],
    execution_id: UUID | None = None,
    tool_name: str | None = None,
    **kwargs: Any,
) -> ModelExecutionResult[Any, str]:
    """
    Execute function and wrap result/exception in execution result.

    Args:
        f: Function to execute
        execution_id: Optional execution identifier
        tool_name: Optional tool name for context
        **kwargs: Additional metadata

    Returns:
        ModelExecutionResult containing either the return value or error
    """
    metadata = kwargs.pop("metadata", ModelCustomProperties())
    if not isinstance(metadata, ModelCustomProperties):
        # Convert dict to ModelCustomProperties if needed
        metadata = ModelCustomProperties.from_metadata(metadata)
    if tool_name:
        metadata.set_custom_string("tool_name", tool_name)

    try:
        value = f()
        success_result: ModelExecutionResult[Any, str] = ModelExecutionResult(
            success=True,
            value=value,
            error=None,
            execution_id=execution_id or uuid4(),
            metadata=metadata,
            **kwargs,
        )
        success_result.mark_completed()
        return success_result
    except Exception as e:
        error_result: ModelExecutionResult[Any, str] = ModelExecutionResult(
            success=False,
            value=None,
            error=str(e),
            execution_id=execution_id or uuid4(),
            metadata=metadata,
            **kwargs,
        )
        error_result.mark_completed()
        return error_result


# Export for use
__all__ = [
    "ModelExecutionResult",
    "execution_err",
    "execution_ok",
    "try_execution",
]
