"""Masked Data Dict Model.

Dictionary container for masked data.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.common.model_typed_value import ModelTypedMapping


class ModelMaskedDataDict(BaseModel):
    """Dictionary container for masked data.

    Uses ModelTypedMapping for type-safe storage of heterogeneous data.
    """

    data: ModelTypedMapping = Field(default_factory=ModelTypedMapping)
