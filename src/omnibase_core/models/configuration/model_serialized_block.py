from pydantic import Field

"""
SerializedBlock model.
"""

from pydantic import BaseModel


class ModelSerializedBlock(BaseModel):
    """
    Result model for serialize_block protocol method.
    """

    serialized: str = Field(
        default=..., description="Serialized metadata block as a string."
    )
