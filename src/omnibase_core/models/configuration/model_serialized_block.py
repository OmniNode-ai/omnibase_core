"""
SerializedBlock model.
"""

from pydantic import BaseModel, Field


class ModelSerializedBlock(BaseModel):
    """
    Result model for serialize_block protocol method.
    """

    serialized: str = Field(
        default=..., description="Serialized metadata block as a string."
    )
