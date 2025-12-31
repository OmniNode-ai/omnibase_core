"""Masked Data List Model.

List container for masked data.
"""

from pydantic import BaseModel, Field

from omnibase_core.types.json_types import JsonType


class ModelMaskedDataList(BaseModel):
    """List container for masked data.

    Uses JsonType for type-safe storage of JSON-compatible list items.
    """

    items: list[JsonType] = Field(default_factory=list)
