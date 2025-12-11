"""Masked Data List Model.

List container for masked data.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.common.model_typed_value import ModelTypedValue


class ModelMaskedDataList(BaseModel):
    """List container for masked data.

    Uses ModelTypedValue for type-safe storage of heterogeneous list items.
    """

    items: list[ModelTypedValue] = Field(default_factory=list)
