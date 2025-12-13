"""
CLI command model for node command specification.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_cli_argument import ModelCLIArgument
from omnibase_core.models.core.model_event_type import ModelEventType


class ModelCLICommand(BaseModel):
    """Model for CLI command specification."""

    command_name: str = Field(
        default=...,
        description="CLI command name (e.g., 'validate', 'health-check')",
    )
    action: str = Field(
        default=..., description="Node action to execute for this command"
    )
    description: str = Field(
        default=..., description="Command description for help text"
    )
    event_type: ModelEventType = Field(
        default=...,
        description="Event type to publish when command is invoked",
    )
    target_node: str = Field(
        default=..., description="Target node that handles this command"
    )
    required_args: list[ModelCLIArgument] = Field(
        default_factory=list,
        description="Required arguments for this command",
    )
    optional_args: list[ModelCLIArgument] = Field(
        default_factory=list,
        description="Optional arguments for this command",
    )
    examples: list[str] = Field(
        default_factory=list,
        description="Usage examples for this command",
    )
