"""Masked Data Models.

Re-export module for masked data components including dictionary and list containers,
main data class, and configuration.
"""

from omnibase_core.models.security.model_masked_data_class import ModelMaskedData
from omnibase_core.models.security.model_masked_data_config import ModelConfig
from omnibase_core.models.security.model_masked_data_dict import ModelMaskedDataDict
from omnibase_core.models.security.model_masked_data_list import ModelMaskedDataList

# Export the type alias for convenience
ModelMaskedDataValue = (
    dict[str, object] | list[object] | str | int | float | bool | None
)

__all__ = [
    "ModelMaskedDataDict",
    "ModelMaskedDataList",
    "ModelMaskedData",
    "ModelConfig",
    "ModelMaskedDataValue",
]
