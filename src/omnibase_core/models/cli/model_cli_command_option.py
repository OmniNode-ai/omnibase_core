"""
CLI Command Option Model.

Represents command-line options and flags with proper validation.
Replaces dict[str, Any] for command options with structured typing.
"""

from typing import Union
from uuid import UUID

from pydantic import BaseModel, Field


class ModelCliCommandOption(BaseModel):
    """
    Structured command option with proper typing.

    Replaces dict[str, Any] for command options to provide
    type safety and validation for CLI command configurations.
    """

    # Option identification
    name: str = Field(..., description="Option name (e.g., '--verbose', '-v')")
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


# Export for use
__all__ = ["ModelCliCommandOption"]
