"""Masked Data Model.

Masked data structure container.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.common.model_typed_value import ModelTypedMapping


class ModelMaskedData(BaseModel):
    """Masked data structure container.

    Uses ModelTypedMapping for type-safe storage of heterogeneous data.
    """

    data: ModelTypedMapping = Field(
        default_factory=ModelTypedMapping,
        description="The masked data structure",
    )
