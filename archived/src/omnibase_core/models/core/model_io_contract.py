"""
IO contract model for ONEX node metadata.
"""

from pydantic import BaseModel

from omnibase_core.models.core.model_io_block import ModelIOBlock


class ModelIOContract(BaseModel):
    """Contract defining inputs and outputs for ONEX nodes."""

    inputs: list[ModelIOBlock]
    outputs: list[ModelIOBlock]
