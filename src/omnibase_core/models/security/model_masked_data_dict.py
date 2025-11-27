"""Masked Data Dict Model.

Dictionary container for masked data.
"""

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

# Recursive data structure without Any usage
ModelMaskedDataValue = dict[str, Any] | list[Any] | str | int | float | bool | None


class ModelMaskedDataDict(BaseModel):
    """Dictionary container for masked data."""

    data: dict[str, ModelMaskedDataValue] = Field(default_factory=dict)
