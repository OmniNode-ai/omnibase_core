"""
State contract block model.
"""

from pydantic import BaseModel

from omnibase_core.models.core.model_io_block import ModelIOBlock


class ModelStateContractBlock(BaseModel):
    """State contract with preconditions and postconditions."""

    preconditions: list[ModelIOBlock]
    postconditions: list[ModelIOBlock]
    transitions: list[ModelIOBlock] | None = None
