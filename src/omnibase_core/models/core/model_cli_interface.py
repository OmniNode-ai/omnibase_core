"""
CLI interface model for node CLI specification.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_cli_command import ModelCLICommand


class ModelCLIInterface(BaseModel):
    """Model for CLI interface specification."""

    entrypoint: str = Field(default=..., description="CLI entrypoint command")
    commands: list[ModelCLICommand] = Field(
        default_factory=list,
        description="CLI commands this node provides",
    )
    exit_codes: list[int] = Field(default=..., description="Possible exit codes")
    supports_introspect: bool = Field(
        default=True,
        description="Whether node supports --introspect",
    )
