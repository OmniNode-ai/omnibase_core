"""
States model for node introspection.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.infrastructure.model_state import ModelState


class ModelStates(BaseModel):
    """Model for input/output state models."""

    input: ModelState = Field(
        default=..., description="Input state model specification"
    )
    output: ModelState = Field(
        default=..., description="Output state model specification"
    )
