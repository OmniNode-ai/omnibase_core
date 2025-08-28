"""
CLI interface model for node CLI specification.
"""

from typing import List

from pydantic import BaseModel, Field

from omnibase.model.core.model_cli_argument import ModelCLIArgument
from omnibase.model.core.model_cli_command import ModelCLICommand


class ModelCLIInterface(BaseModel):
    """Model for CLI interface specification."""

    entrypoint: str = Field(..., description="CLI entrypoint command")
    commands: List[ModelCLICommand] = Field(
        default_factory=list, description="CLI commands this node provides"
    )
    # Legacy fields for backward compatibility
    required_args: List[ModelCLIArgument] = Field(
        default_factory=list, description="Required CLI arguments (legacy)"
    )
    optional_args: List[ModelCLIArgument] = Field(
        default_factory=list, description="Optional CLI arguments (legacy)"
    )
    exit_codes: List[int] = Field(..., description="Possible exit codes")
    supports_introspect: bool = Field(
        True, description="Whether node supports --introspect"
    )
