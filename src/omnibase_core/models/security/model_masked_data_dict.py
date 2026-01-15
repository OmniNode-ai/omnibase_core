"""Masked Data Dict Model.

Dictionary container for masked data.
"""

from pydantic import BaseModel, Field

from omnibase_core.types.type_json import JsonType


class ModelMaskedDataDict(BaseModel):
    """Dictionary container for masked data.

    Uses JsonType for type-safe storage of JSON-compatible data.
    """

    data: dict[str, JsonType] = Field(default_factory=dict)
