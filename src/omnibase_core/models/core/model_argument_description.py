"""
CLI Argument Description Model

Defines the structure for CLI arguments discovered from node contracts.
This enables dynamic CLI argument parsing based on contract specifications.
"""

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_argument_type import EnumArgumentType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelArgumentDescription(BaseModel):
    """
    CLI argument description for dynamic argument parsing.

    This model describes how a CLI argument should be parsed, validated,
    and displayed in help text. Arguments are discovered from node contracts.
    """

    name: str = Field(
        default=...,
        description="Argument name (without -- prefix)",
        pattern=r"^[a-z][a-z0-9_-]*$",
    )

    type: EnumArgumentType = Field(default=..., description="Argument data type")

    description: str = Field(
        default=..., description="Human-readable argument description"
    )

    required: bool = Field(default=False, description="Whether argument is required")

    default_value: str | int | float | bool | None = Field(
        default=None,
        description="Default value if not provided (any JSON-serializable primitive)",
    )

    choices: list[str] | None = Field(
        default=None,
        description="Valid choices for enum-like arguments",
    )

    validation_pattern: str | None = Field(
        default=None,
        description="Regex validation pattern",
    )

    examples: list[str] = Field(default_factory=list, description="Usage examples")

    short_name: str | None = Field(
        default=None,
        description="Short argument name (single letter)",
        pattern=r"^[a-z]$",
    )

    hidden: bool = Field(
        default=False,
        description="Hide from help display (for internal/debug args)",
    )

    def get_cli_flags(self) -> list[str]:
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

    def validate_value(self, value: str) -> str | int | float | bool | list[str]:
        """Validate and convert a string value to the appropriate type."""
        if self.type == EnumArgumentType.STRING:
            if self.choices and value not in self.choices:
                msg = f"Value '{value}' not in valid choices: {self.choices}"
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                )
            return value

        if self.type == EnumArgumentType.INTEGER:
            try:
                return int(value)
            except ValueError:
                msg = f"Invalid integer value: '{value}'"
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                )

        elif self.type == EnumArgumentType.FLOAT:
            try:
                return float(value)
            except ValueError:
                msg = f"Invalid float value: '{value}'"
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                )

        elif self.type == EnumArgumentType.BOOLEAN:
            if value.lower() in ("true", "1", "yes", "on"):
                return True
            if value.lower() in ("false", "0", "no", "off"):
                return False
            msg = f"Invalid boolean value: '{value}'"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        elif self.type == EnumArgumentType.LIST:
            # Assume comma-separated values
            return [item.strip() for item in value.split(",") if item.strip()]

        else:
            # Default to string
            return value
