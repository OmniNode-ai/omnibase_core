from pydantic import Field

"""
Matrix strategy model.
"""

from typing import Any

from pydantic import BaseModel


class ModelMatrixStrategy(BaseModel):
    """Matrix strategy configuration."""

    matrix: dict[str, list[Any]] = Field(default=..., description="Matrix dimensions")
    include: list[dict[str, Any]] | None = Field(
        default=None,
        description="Matrix inclusions",
    )
    exclude: list[dict[str, Any]] | None = Field(
        default=None,
        description="Matrix exclusions",
    )
