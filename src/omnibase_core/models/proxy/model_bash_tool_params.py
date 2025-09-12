"""Strongly typed model for Bash tool parameters."""

from pydantic import Field, field_validator

from omnibase_core.models.proxy.model_tool_parameter_base import ModelToolParameterBase


class ModelBashToolParams(ModelToolParameterBase):
    """Parameters for Bash tool with strong typing."""

    command: str = Field(..., description="Command to execute", min_length=1)
    description: str | None = Field(
        None,
        description="Command description",
        min_length=1,
        max_length=100,
    )
    timeout: int | None = Field(
        None,
        description="Timeout in milliseconds",
        ge=100,
        le=600000,  # Max 10 minutes
    )

    @field_validator("command")
    @classmethod
    def validate_command_not_empty(cls, v: str) -> str:
        """Ensure command is not just whitespace."""
        if not v.strip():
            msg = "Command cannot be empty or whitespace only"
            raise ValueError(msg)
        return v
