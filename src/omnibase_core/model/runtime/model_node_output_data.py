"""Node output data model."""

from pydantic import BaseModel, Field


class ModelNodeOutputData(BaseModel):
    """Individual node output data."""

    value: str | int | float | bool | list[str] | None = Field(
        ...,
        description="Output value",
    )
    status: str = Field(..., description="Output status")
    timestamp: str | None = Field(default=None, description="Output timestamp")
    metadata: str | None = Field(default=None, description="Output metadata")
