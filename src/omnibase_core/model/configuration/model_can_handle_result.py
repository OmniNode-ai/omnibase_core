"""
CanHandleResult model.
"""

from pydantic import BaseModel, Field


class ModelCanHandleResult(BaseModel):
    """
    Result model for can_handle protocol method.
    """

    can_handle: bool = Field(
        ..., description="Whether the handler can process the file/content."
    )

    def __bool__(self):
        return self.can_handle
