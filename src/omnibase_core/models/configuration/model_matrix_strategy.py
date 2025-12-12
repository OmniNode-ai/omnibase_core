"""
Matrix strategy model.
"""

from pydantic import BaseModel, Field


class ModelMatrixStrategy(BaseModel):
    """Matrix strategy configuration."""

    matrix: dict[str, list[object]] = Field(
        default=..., description="Matrix dimensions"
    )
    include: list[dict[str, object]] | None = Field(
        default=None,
        description="Matrix inclusions",
    )
    exclude: list[dict[str, object]] | None = Field(
        default=None,
        description="Matrix exclusions",
    )
