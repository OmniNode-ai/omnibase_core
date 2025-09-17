"""
Contract model for node introspection.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_cli_interface import ModelCLIInterface


class ModelContract(BaseModel):
    """Model for node contract specification."""

    input_state_schema: str = Field(..., description="Input state JSON schema filename")
    output_state_schema: str = Field(
        ...,
        description="Output state JSON schema filename",
    )
    cli_interface: ModelCLIInterface = Field(
        ...,
        description="CLI interface specification",
    )
    protocol_version: str = Field(..., description="ONEX protocol version")
