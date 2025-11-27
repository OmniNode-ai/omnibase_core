from __future__ import annotations

from omnibase_core.types.typed_dict_execution_params import TypedDictExecutionParams
from omnibase_core.types.typed_dict_message_params import TypedDictMessageParams
from omnibase_core.types.typed_dict_metadata_params import TypedDictMetadataParams

__all__ = [
    "TypedDictExecutionParams",
    "TypedDictFactoryKwargs",
    "TypedDictMessageParams",
    "TypedDictMetadataParams",
]

"""
Typed dictionary for factory method parameters.

Provides structured parameter types for model factory operations.
Restructured using composition to reduce string field count and follow ONEX one-model-per-file pattern.
"""


# Main factory kwargs that combines sub-groups
class TypedDictFactoryKwargs(
    TypedDictExecutionParams,
    TypedDictMetadataParams,
    TypedDictMessageParams,
    total=False,
):
    """
    Typed dictionary for factory method parameters.

    Restructured using composition to reduce string field count.
    Follows ONEX one-model-per-file architecture pattern.
    """
