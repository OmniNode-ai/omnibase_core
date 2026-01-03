"""Masked Data Model.

Masked data structure container.
"""

from pydantic import BaseModel, Field

from omnibase_core.types.type_json import JsonType


class ModelMaskedData(BaseModel):
    """Masked data structure container.

    Uses JsonType for type-safe storage of JSON-compatible data.
    """

    data: dict[str, JsonType] = Field(
        default_factory=dict,
        description="The masked data structure",
    )
