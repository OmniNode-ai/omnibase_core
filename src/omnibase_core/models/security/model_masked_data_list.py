"""Masked Data List Model.

List container for masked data.
"""

from pydantic import BaseModel, Field

from omnibase_core.types.json_types import JsonValue


class ModelMaskedDataList(BaseModel):
    """List container for masked data."""

    items: list[JsonValue] = Field(default_factory=list)
