"""
State contract block model.
"""

from typing import List, Optional

from pydantic import BaseModel

from omnibase_core.model.core.model_io_block import ModelIOBlock


class ModelStateContractBlock(BaseModel):
    """State contract with preconditions and postconditions."""

    preconditions: List[ModelIOBlock]
    postconditions: List[ModelIOBlock]
    transitions: Optional[List[ModelIOBlock]] = None
