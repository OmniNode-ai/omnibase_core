"""
Signature contract model.
"""

from pydantic import BaseModel

from omnibase_core.models.core.model_io_block import ModelIOBlock


class ModelSignatureContract(BaseModel):
    """Function signature contract definition."""

    function_name: str
    parameters: list[ModelIOBlock]
    return_type: str
    raises: list[str] = []
