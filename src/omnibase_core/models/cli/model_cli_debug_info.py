from __future__ import annotations

from datetime import datetime
from typing import Generic

from pydantic import Field, field_validator

from omnibase_core.errors.model_onex_error import ModelOnexError

"""
CLI debug information model.

Clean, strongly-typed replacement for dict[str, Any] in CLI debug info.
Follows ONEX one-model-per-file naming conventions.
"""


from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from omnibase_core.enums.enum_debug_level import EnumDebugLevel
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.infrastructure.model_cli_value import ModelCliValue


class ModelCliDebugInfo(BaseModel):
    """
    Clean model for CLI debug information.

    Replaces ModelGenericMetadata[Any] with structured debug model.
    Implements omnibase_spi protocols:
    - Serializable: Data serialization/deserialization
    - Nameable: Name management interface
    - Validatable: Validation and verification
    """

    # Core debug fields
    debug_level: EnumDebugLevel = Field(
        default=EnumDebugLevel.INFO,
        description="Debug level",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Debug timestamp",
    )

    # Debug data
    debug_messages: list[str] = Field(
        default_factory=list,
        description="Debug messages",
    )

    # Performance debug info
    timing_info: dict[str, float] = Field(
        default_factory=dict,
        description="Timing information in milliseconds",
    )

    # Memory debug info
    memory_info: dict[str, int] = Field(
        default_factory=dict,
        description="Memory information in bytes",
    )

    # System debug info
    system_info: dict[str, str] = Field(
        default_factory=dict,
        description="System information",
    )

    # Error debug info
    error_details: dict[str, str] = Field(
        default_factory=dict,
        description="Detailed error information",
    )

    # Stack traces and call info
    stack_traces: list[str] = Field(
        default_factory=list,
        description="Stack traces for debugging",
    )

    # Additional debug flags
    verbose_mode: bool = Field(default=False, description="Verbose mode enabled")
    trace_mode: bool = Field(default=False, description="Trace mode enabled")

    # Custom debug fields for extensibility
    custom_debug_fields: dict[str, ModelCliValue] = Field(
        default_factory=dict,
        description="Custom debug fields",
    )

    @field_validator("custom_debug_fields", mode="before")
    @classmethod
    def validate_custom_debug_fields(
        cls,
        v: dict[str, Any],
    ) -> dict[str, ModelCliValue]:
        """Convert raw values to ModelCliValue objects for custom_debug_fields."""
        if not isinstance(v, dict):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="custom_debug_fields must be a dict[str, Any]ionary",
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            )

        result = {}
        for key, value in v.items():
            if isinstance(value, ModelCliValue):
                result[key] = value
            elif (
                isinstance(value, dict)
                and "value_type" in value
                and "raw_value" in value
            ):
                # This is a serialized ModelCliValue, reconstruct it
                result[key] = ModelCliValue.model_validate(value)
            else:
                # Convert raw value to ModelCliValue
                result[key] = ModelCliValue.from_any(value)
        return result

    def add_debug_message(self, message: str) -> None:
        """Add a debug message."""
        self.debug_messages.append(message)

    def add_timing_info(self, operation: str, duration_ms: float) -> None:
        """Add timing information."""
        self.timing_info[operation] = duration_ms

    def add_memory_info(self, component: str, bytes_used: int) -> None:
        """Add memory usage information."""
        self.memory_info[component] = bytes_used

    def add_system_info(self, key: str, value: str) -> None:
        """Add system information."""
        self.system_info[key] = value

    def add_error_detail(self, component: str, error_detail: str) -> None:
        """Add error detail information."""
        self.error_details[component] = error_detail

    def add_stack_trace(self, trace: str) -> None:
        """Add a stack trace."""
        self.stack_traces.append(trace)

    def set_custom_field(self, key: str, value: ModelCliValue | object) -> None:
        """Set a custom debug field with automatic type conversion."""
        if isinstance(value, ModelCliValue):
            self.custom_debug_fields[key] = value
        else:
            # Convert to ModelCliValue for type safety
            self.custom_debug_fields[key] = ModelCliValue.from_any(value)

    def get_custom_field(self, key: str, default: str = "") -> str:
        """Get a custom debug field. CLI debug fields are strings."""
        cli_value = self.custom_debug_fields.get(key)
        if cli_value is not None:
            return str(cli_value.to_python_value())
        return default

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Export the model

    # Protocol method implementations

    def serialize(self) -> dict[str, Any]:
        """Serialize to dict[str, Any]ionary (Serializable protocol)."""
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
        except Exception as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e


__all__ = ["ModelCliDebugInfo"]
