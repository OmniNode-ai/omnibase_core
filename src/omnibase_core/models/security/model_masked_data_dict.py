"""Masked Data Dict Model.

Dictionary container for masked data.
"""

from pydantic import BaseModel, Field

from omnibase_core.types.json_types import JsonValue


class ModelMaskedDataDict(BaseModel):
    """Dictionary container for masked data.

    Uses JsonValue for type-safe storage of JSON-compatible data.
    """

    data: dict[str, JsonValue] = Field(default_factory=dict)
