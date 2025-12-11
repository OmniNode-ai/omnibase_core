"""
Matrix strategy model.
"""

from pydantic import BaseModel, Field

from omnibase_core.types import SerializableValue


class ModelMatrixStrategy(BaseModel):
    """Matrix strategy configuration."""

    matrix: dict[str, list[SerializableValue]] = Field(
        default=..., description="Matrix dimensions"
    )
    include: list[dict[str, SerializableValue]] | None = Field(
        default=None,
        description="Matrix inclusions",
    )
    exclude: list[dict[str, SerializableValue]] | None = Field(
        default=None,
        description="Matrix exclusions",
    )
