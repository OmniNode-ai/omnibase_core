"""
CLI command model for strongly typed CLI interface representation.

Provides structured representation of CLI commands with proper validation.
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from .model_cli_option import ModelCliOption


class ModelCliCommand(BaseModel):
    """Strongly typed CLI command definition."""

    name: str = Field(..., description="Command name (e.g., 'info', 'health')")
    description: str = Field(..., description="Command description")
    args: list[str] | None = Field(
        default_factory=list,
        description="Command arguments",
    )
    options: list[ModelCliOption] | None = Field(
        default_factory=list,
        description="Command options/flags",
    )
    examples: list[str] | None = Field(
        default_factory=list,
        description="Usage examples",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """Validate command name format."""
        if not v or not isinstance(v, str):
            msg = "Command name must be a non-empty string"
            raise ValueError(msg)
        if not v.replace("_", "").replace("-", "").isalnum():
            msg = "Command name must contain only alphanumeric characters, hyphens, and underscores"
            raise ValueError(
                msg,
            )
        return v.lower()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v):
        """Validate command description."""
        if not v or not isinstance(v, str):
            msg = "Command description must be a non-empty string"
            raise ValueError(msg)
        return v

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelCliCommand":
        """Create from dictionary data."""
        if isinstance(data, str):
            # Handle legacy string format
            return cls(name=data, description=f"Execute {data} command")

        # Handle both "name" and "command_name" fields for compatibility
        name = data.get("name") or data.get("command_name", "")

        # Process options - handle both string and object formats
        options = []
        for option_data in data.get("options", []):
            if isinstance(option_data, str | dict):
                options.append(ModelCliOption.from_dict(option_data))

        return cls(
            name=name,
            description=data.get("description", ""),
            args=data.get("args", []),
            options=options,
            examples=data.get("examples", []),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return self.model_dump(exclude_none=True)
