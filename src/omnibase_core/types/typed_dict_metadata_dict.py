"""
TypedDictMetadataDict.

Typed structure for metadata dictionary in protocol methods.
"""

from typing import TYPE_CHECKING, TypedDict

from omnibase_core.types.type_serializable_value import SerializableValue

if TYPE_CHECKING:
    from omnibase_core.models.primitives.model_semver import ModelSemVer


class TypedDictMetadataDict(TypedDict, total=False):
    """Typed structure for metadata dictionary in protocol methods."""

    name: str
    description: str
    version: "ModelSemVer"
    tags: list[str]
    metadata: dict[str, SerializableValue]


__all__ = ["TypedDictMetadataDict"]
