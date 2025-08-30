"""
IO contract model for ONEX node metadata.
"""

from typing import List

from pydantic import BaseModel

from omnibase_core.model.core.model_io_block import ModelIOBlock


class ModelIOContract(BaseModel):
    """Contract defining inputs and outputs for ONEX nodes."""

    inputs: List[ModelIOBlock]
    outputs: List[ModelIOBlock]
