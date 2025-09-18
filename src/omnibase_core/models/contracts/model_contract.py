"""
Contract model for node introspection.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_cli_interface import ModelCLIInterface
from omnibase_core.models.core.model_semver import SemVerField


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
    protocol_version: SemVerField = Field(..., description="ONEX protocol version")
