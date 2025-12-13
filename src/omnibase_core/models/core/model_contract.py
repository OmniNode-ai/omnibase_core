"""
Contract model for node introspection.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_cli_interface import ModelCLIInterface
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelContract(BaseModel):
    """Model for node contract specification."""

    input_state_schema: str = Field(
        default=..., description="Input state JSON schema filename"
    )
    output_state_schema: str = Field(
        default=...,
        description="Output state JSON schema filename",
    )
    cli_interface: ModelCLIInterface = Field(
        default=...,
        description="CLI interface specification",
    )
    protocol_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="ONEX protocol version",
    )
