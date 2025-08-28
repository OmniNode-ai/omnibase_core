"""
CLI Argument Description Model

Defines the structure for CLI arguments discovered from node contracts.
This enables dynamic CLI argument parsing based on contract specifications.
"""

from typing import List, Optional, Union

from pydantic import BaseModel, Field

from omnibase.enums.enum_argument_type import EnumArgumentType


class ModelArgumentDescription(BaseModel):
    """
    CLI argument description for dynamic argument parsing.

    This model describes how a CLI argument should be parsed, validated,
    and displayed in help text. Arguments are discovered from node contracts.
    """

    name: str = Field(
        ...,
        description="Argument name (without -- prefix)",
        pattern=r"^[a-z][a-z0-9_-]*$",
    )

    type: EnumArgumentType = Field(..., description="Argument data type")

    description: str = Field(..., description="Human-readable argument description")

    required: bool = Field(default=False, description="Whether argument is required")

    default_value: Optional[Union[str, int, bool, float, List[str]]] = Field(
        None, description="Default value if not provided"
    )

    choices: Optional[List[str]] = Field(
        None, description="Valid choices for enum-like arguments"
    )

    validation_pattern: Optional[str] = Field(
        None, description="Regex validation pattern"
    )

    examples: List[str] = Field(default_factory=list, description="Usage examples")

    short_name: Optional[str] = Field(
        None, description="Short argument name (single letter)", pattern=r"^[a-z]$"
    )

    hidden: bool = Field(
        default=False, description="Hide from help display (for internal/debug args)"
    )

    def get_cli_flags(self) -> List[str]:
        """Get CLI flags for this argument (--name and -n if short_name exists)."""
        flags = [f"--{self.name}"]
        if self.short_name:
            flags.append(f"-{self.short_name}")
        return flags

    def get_help_line(self) -> str:
        """Generate a help line for this argument."""
        flags = ", ".join(self.get_cli_flags())
        type_hint = (
            f" ({self.type.value})" if self.type != EnumArgumentType.BOOLEAN else ""
        )
        required_hint = " [REQUIRED]" if self.required else ""
        default_hint = (
            f" (default: {self.default_value})"
            if self.default_value is not None
            else ""
        )

        return f"{flags}{type_hint}: {self.description}{required_hint}{default_hint}"

    def validate_value(self, value: str) -> Union[str, int, bool, float, List[str]]:
        """Validate and convert a string value to the appropriate type."""
        if self.type == EnumArgumentType.STRING:
            if self.choices and value not in self.choices:
                raise ValueError(
                    f"Value '{value}' not in valid choices: {self.choices}"
                )
            return value

        elif self.type == EnumArgumentType.INTEGER:
            try:
                return int(value)
            except ValueError:
                raise ValueError(f"Invalid integer value: '{value}'")

        elif self.type == EnumArgumentType.FLOAT:
            try:
                return float(value)
            except ValueError:
                raise ValueError(f"Invalid float value: '{value}'")

        elif self.type == EnumArgumentType.BOOLEAN:
            if value.lower() in ("true", "1", "yes", "on"):
                return True
            elif value.lower() in ("false", "0", "no", "off"):
                return False
            else:
                raise ValueError(f"Invalid boolean value: '{value}'")

        elif self.type == EnumArgumentType.LIST:
            # Assume comma-separated values
            return [item.strip() for item in value.split(",") if item.strip()]

        else:
            # Default to string
            return value
