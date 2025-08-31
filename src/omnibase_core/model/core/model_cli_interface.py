"""
CLI interface model for node CLI specification.
"""

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_cli_argument import ModelCLIArgument
from omnibase_core.model.core.model_cli_command import ModelCLICommand


class ModelCLIInterface(BaseModel):
    """Model for CLI interface specification."""

    entrypoint: str = Field(..., description="CLI entrypoint command")
    commands: list[ModelCLICommand] = Field(
        default_factory=list,
        description="CLI commands this node provides",
    )
    # Legacy fields for backward compatibility
    required_args: list[ModelCLIArgument] = Field(
        default_factory=list,
        description="Required CLI arguments (legacy)",
    )
    optional_args: list[ModelCLIArgument] = Field(
        default_factory=list,
        description="Optional CLI arguments (legacy)",
    )
    exit_codes: list[int] = Field(..., description="Possible exit codes")
    supports_introspect: bool = Field(
        True,
        description="Whether node supports --introspect",
    )
