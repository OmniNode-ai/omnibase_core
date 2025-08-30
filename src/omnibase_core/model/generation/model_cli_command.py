"""
CLI command model for strongly typed CLI interface representation.

Provides structured representation of CLI commands with proper validation.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from .model_cli_option import ModelCliOption


class ModelCliCommand(BaseModel):
    """Strongly typed CLI command definition."""

    name: str = Field(..., description="Command name (e.g., 'info', 'health')")
    description: str = Field(..., description="Command description")
    args: Optional[List[str]] = Field(
        default_factory=list, description="Command arguments"
    )
    options: Optional[List[ModelCliOption]] = Field(
        default_factory=list, description="Command options/flags"
    )
    examples: Optional[List[str]] = Field(
        default_factory=list, description="Usage examples"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """Validate command name format."""
        if not v or not isinstance(v, str):
            raise ValueError("Command name must be a non-empty string")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Command name must contain only alphanumeric characters, hyphens, and underscores"
            )
        return v.lower()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v):
        """Validate command description."""
        if not v or not isinstance(v, str):
            raise ValueError("Command description must be a non-empty string")
        return v

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelCliCommand":
        """Create from dictionary data."""
        if isinstance(data, str):
            # Handle legacy string format
            return cls(name=data, description=f"Execute {data} command")

        # Handle both "name" and "command_name" fields for compatibility
        name = data.get("name") or data.get("command_name", "")

        # Process options - handle both string and object formats
        options = []
        for option_data in data.get("options", []):
            if isinstance(option_data, str):
                options.append(ModelCliOption.from_dict(option_data))
            elif isinstance(option_data, dict):
                options.append(ModelCliOption.from_dict(option_data))

        return cls(
            name=name,
            description=data.get("description", ""),
            args=data.get("args", []),
            options=options,
            examples=data.get("examples", []),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return self.model_dump(exclude_none=True)
