"""
Single field preview showing before/after state for one config override.

.. versionadded:: 0.4.0
    Added Configuration Override Injection (OMN-1205)
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.replay.enum_override_injection_point import (
    EnumOverrideInjectionPoint,
)

__all__ = ["ModelConfigOverrideFieldPreview"]


class ModelConfigOverrideFieldPreview(BaseModel):
    """
    Single field preview showing before/after for one override.

    Represents the state change for a single configuration field when an
    override is applied. Used for dry-run preview and user confirmation.

    Attributes:
        path: Dot-separated path to the field (e.g., "retry.max_attempts").
        injection_point: Where this override will be applied in the pipeline.
        old_value: Value before override (or MISSING sentinel for new fields).
        new_value: Value after override.
        value_type: Type of the new value (for display purposes).
        path_exists: Whether the path exists in the original configuration.

    Thread Safety:
        Immutable (frozen=True) after creation - thread-safe for concurrent reads.

    Example:
        >>> preview = ModelConfigOverrideFieldPreview(
        ...     path="timeout",
        ...     injection_point=EnumOverrideInjectionPoint.HANDLER_CONFIG,
        ...     old_value=30,
        ...     new_value=60,
        ...     value_type="int",
        ...     path_exists=True,
        ... )
        >>> preview.to_markdown_row()
        '| timeout | handler_config | `30` | `60` | exists |'

    .. versionadded:: 0.4.0
    """

    # from_attributes=True: Enables construction from ORM/dataclass instances
    # and ensures pytest-xdist compatibility across worker processes where
    # class identity may differ due to independent imports.
    # See CLAUDE.md "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(..., description="Dot-separated path to the field")
    injection_point: EnumOverrideInjectionPoint = Field(
        ..., description="Where this override will be applied"
    )
    old_value: Any = Field(
        ..., description="Value before override (or MISSING sentinel)"
    )
    new_value: Any = Field(..., description="Value after override")
    value_type: str = Field(default="unknown", description="Type of the new value")
    path_exists: bool = Field(
        default=True, description="Whether the path exists in original"
    )

    def to_markdown_row(self) -> str:
        """Generate markdown table row for this preview.

        Creates a formatted markdown table row showing the field path,
        injection point, before/after values, and existence status.

        Returns:
            A markdown table row string with pipe delimiters.
        """
        old_str = self._format_value(self.old_value)
        new_str = self._format_value(self.new_value)
        status = "exists" if self.path_exists else "NEW"
        return f"| {self.path} | {self.injection_point.value} | {old_str} | {new_str} | {status} |"

    def _format_value(self, value: Any) -> str:
        """Format value for markdown display.

        Wraps values in backticks for code formatting. Handles None
        specially as `null` and strings with quotes.

        Args:
            value: The value to format.

        Returns:
            A markdown-formatted string representation of the value.
        """
        if value is None:
            return "`null`"
        if isinstance(value, str):
            return f'`"{value}"`'
        return f"`{value}`"
