"""Masked Data List Model.

List container for masked data.
"""

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from omnibase_core.models.security.model_masked_data_dict import ModelMaskedDataDict


# Recursive data structure without Any usage
ModelMaskedDataValue = dict[str, Any] | list[Any] | str | int | float | bool | None


class ModelMaskedDataList(BaseModel):
    """List container for masked data."""

    items: list[ModelMaskedDataValue] = Field(default_factory=list)
