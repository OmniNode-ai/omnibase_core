"""Masked Data List Model.

List container for masked data.
"""

from typing import Any

from pydantic import BaseModel, Field


class ModelMaskedDataList(BaseModel):
    """List container for masked data.

    Uses Any for storage of heterogeneous list items.
    """

    items: list[Any] = Field(default_factory=list)
