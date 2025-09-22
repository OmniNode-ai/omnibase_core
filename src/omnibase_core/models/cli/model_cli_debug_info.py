"""
CLI debug information model.

Clean, strongly-typed replacement for dict[str, Any] in CLI debug info.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from ...enums.enum_debug_level import EnumDebugLevel
from ..infrastructure.model_cli_value import ModelCliValue


class ModelCliDebugInfo(BaseModel):
    """
    Clean model for CLI debug information.

    Replaces ModelGenericMetadata[Any] with structured debug model.
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

    def set_custom_field(self, key: str, value: str) -> None:
        """Set a custom debug field. CLI debug fields are typically strings."""
        self.custom_debug_fields[key] = ModelCliValue.from_string(value)

    def get_custom_field(self, key: str, default: str = "") -> str:
        """Get a custom debug field. CLI debug fields are strings."""
        cli_value = self.custom_debug_fields.get(key)
        if cli_value is not None:
            return cli_value.to_python_value()
        return default


# Export the model
__all__ = ["ModelCliDebugInfo"]
