"""Node output data model."""

from typing import List, Optional, Union

from pydantic import BaseModel, Field


class ModelNodeOutputData(BaseModel):
    """Individual node output data."""

    value: Union[str, int, float, bool, List[str], None] = Field(
        ..., description="Output value"
    )
    status: str = Field(..., description="Output status")
    timestamp: Optional[str] = Field(default=None, description="Output timestamp")
    metadata: Optional[str] = Field(default=None, description="Output metadata")
