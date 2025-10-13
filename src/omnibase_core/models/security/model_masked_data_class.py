"""Masked Data Model.

Masked data structure container.
"""

from typing import Any

from pydantic import BaseModel, Field

# Recursive data structure without Any usage
ModelMaskedDataValue = dict[str, Any] | list[Any] | str | int | float | bool | None


class ModelMaskedData(BaseModel):
    """Masked data structure container."""

    data: dict[str, ModelMaskedDataValue] = Field(
        default_factory=dict,
        description="The masked data structure",
    )
