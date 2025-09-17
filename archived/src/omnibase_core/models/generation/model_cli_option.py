"""
CLI option model for structured CLI option representation.

Provides structured representation of CLI options with proper validation.
"""

from typing import Any

from pydantic import BaseModel, Field


class ModelCliOptionData(BaseModel):
    """Structured data model for CLI option deserialization."""

    name: str = Field(..., description="Option name")
    type: str = Field(default="string", description="Option type")
    description: str = Field(default="", description="Option description")
    required: bool = Field(default=False, description="Whether option is required")
    multiple: bool = Field(
        default=False,
        description="Whether option accepts multiple values",
    )
    default: str | None = Field(None, description="Default value")
    choices: list[str] | None = Field(None, description="Valid choices")


class ModelCliOption(BaseModel):
    """Strongly typed CLI option definition."""

    name: str = Field(..., description="Option name (e.g., '--verbose', '-v')")
    type: str = Field(
        default="string",
        description="Option type (e.g., 'string', 'flag', 'int')",
    )
    description: str = Field(..., description="Option description")
    required: bool = Field(default=False, description="Whether option is required")
    multiple: bool = Field(
        default=False,
        description="Whether option can be specified multiple times",
    )
    default: Any | None = Field(None, description="Default value if optional")
    choices: list[str] | None = Field(
        None,
        description="Valid choices for the option",
    )

    @classmethod
    def from_dict(cls, data: str | ModelCliOptionData) -> "ModelCliOption":
        """Create from structured data or string."""
        if isinstance(data, str):
            # Handle legacy string format - just the option name
            return cls(name=data, description=f"Command option {data}")

        # Handle structured format using proper model
        return cls(
            name=data.name,
            type=data.type,
            description=data.description,
            required=data.required,
            multiple=data.multiple,
            default=data.default,
            choices=data.choices,
        )

    def to_dict(self) -> ModelCliOptionData:
        """Convert to structured data format."""
        # Custom transformation to structured data format
        return ModelCliOptionData(
            name=self.name,
            type=self.type,
            description=self.description,
            required=self.required,
            multiple=self.multiple,
            default=self.default,
            choices=self.choices,
        )
