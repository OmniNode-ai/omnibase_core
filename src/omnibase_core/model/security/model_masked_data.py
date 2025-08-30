"""
ModelMaskedData: Model for representing masked data structures.

This model represents data structures with credentials masked for security.
"""

from typing import Dict, List, Union

from pydantic import BaseModel, Field

# Recursive data structure without Any usage
ModelMaskedDataValue = Union[
    str, int, float, bool, None, "ModelMaskedDataDict", "ModelMaskedDataList"
]


class ModelMaskedDataDict(BaseModel):
    """Dictionary container for masked data."""

    data: Dict[str, ModelMaskedDataValue] = Field(default_factory=dict)


class ModelMaskedDataList(BaseModel):
    """List container for masked data."""

    items: List[ModelMaskedDataValue] = Field(default_factory=list)


class ModelMaskedData(BaseModel):
    """Masked data structure container."""

    data: Dict[str, ModelMaskedDataValue] = Field(
        default_factory=dict, description="The masked data structure"
    )

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True
