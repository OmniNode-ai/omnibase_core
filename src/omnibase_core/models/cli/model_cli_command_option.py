"""
CLI Command Option Model.

Represents command-line options and flags with proper validation.
Replaces dict[str, Any] for command options with structured typing.
"""

from __future__ import annotations

from typing import Union
from uuid import UUID

from pydantic import BaseModel, Field

from ...utils.uuid_helpers import uuid_from_string


class ModelCliCommandOption(BaseModel):
    """
    Structured command option with proper typing.

    Replaces dict[str, Any] for command options to provide
    type safety and validation for CLI command configurations.
    """

    # Option identification - UUID-based entity references
    option_id: UUID = Field(..., description="Unique identifier for the option")
    option_display_name: str | None = Field(None, description="Human-readable option name (e.g., '--verbose', '-v')")
    value: Union[str, int, bool, float, list[str], UUID] = Field(
        ..., description="Option value with restricted types"
    )

    # Option metadata
    is_flag: bool = Field(default=False, description="Whether this is a boolean flag")
    is_required: bool = Field(default=False, description="Whether option is required")
    is_multiple: bool = Field(
        default=False, description="Whether option accepts multiple values"
    )

    # Validation
    description: str = Field(default="", description="Option description")
    valid_choices: list[str] = Field(
        default_factory=list, description="Valid choices for option value"
    )

    def get_string_value(self) -> str:
        """Get value as string representation."""
        if isinstance(self.value, list):
            return ",".join(str(v) for v in self.value)
        return str(self.value)

    def get_typed_value(self) -> Union[str, int, bool, float, list[str], UUID]:
        """Get the properly typed value."""
        return self.value

    def is_boolean_flag(self) -> bool:
        """Check if this is a boolean flag option."""
        return self.is_flag and isinstance(self.value, bool)

    @property
    def option_name(self) -> str:
        """Get option name with fallback to UUID-based name."""
        return self.option_display_name or f"option_{str(self.option_id)[:8]}"

    @option_name.setter
    def option_name(self, value: str) -> None:
        """Set option name (for backward compatibility)."""
        self.option_display_name = value
        # Update option_id to be deterministic based on name
        self.option_id = uuid_from_string(value, "option")

    @classmethod
    def create_legacy(
        cls,
        option_name: str,
        value: Union[str, int, bool, float, list[str], UUID],
        **kwargs,
    ) -> "ModelCliCommandOption":
        """Create option with legacy name parameter for backward compatibility."""
        return cls(
            option_id=uuid_from_string(option_name, "option"),
            option_display_name=option_name,
            value=value,
            **kwargs,
        )


# Export for use
__all__ = ["ModelCliCommandOption"]
