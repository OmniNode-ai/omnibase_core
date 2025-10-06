from pydantic import Field

"""
States model for node introspection.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_state import ModelState


class ModelStates(BaseModel):
    """Model for input/output state models."""

    input: ModelState = Field(..., description="Input state model specification")
    output: ModelState = Field(..., description="Output state model specification")
