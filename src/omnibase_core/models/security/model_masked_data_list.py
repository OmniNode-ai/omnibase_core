"""Masked Data List Model.

List container for masked data.
"""

from pydantic import BaseModel, Field

from omnibase_core.types.json_types import JsonValue


class ModelMaskedDataList(BaseModel):
    """List container for masked data.

    Uses JsonValue for type-safe storage of JSON-compatible list items.
    """

    items: list[JsonValue] = Field(default_factory=list)
