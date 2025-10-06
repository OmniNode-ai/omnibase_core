from __future__ import annotations

from typing import Any, Dict, Union

from omnibase_core.models.core.model_sem_ver import ModelSemVer

"""
Version Union Type Enum.

Strongly typed enumeration for version union type discriminators.
"""


from enum import Enum, unique


@unique
class EnumVersionUnionType(str, Enum):
    """
    Strongly typed version union type discriminators.

    Used for discriminated union patterns in version handling.
    Replaces Union[ModelSemVer, VersionDictType, None] patterns
    with structured typing.
    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    SEMANTIC_VERSION = "semantic_version"
    VERSION_DICT = "version_dict"
    NONE_VERSION = "none_version"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_semantic_version(cls, version_type: EnumVersionUnionType) -> bool:
        """Check if the version type represents a semantic version."""
        return version_type == cls.SEMANTIC_VERSION

    @classmethod
    def is_version_dict(cls, version_type: EnumVersionUnionType) -> bool:
        """Check if the version type represents a version dict[str, Any]ionary."""
        return version_type == cls.VERSION_DICT

    @classmethod
    def is_none_version(cls, version_type: EnumVersionUnionType) -> bool:
        """Check if the version type represents no version."""
        return version_type == cls.NONE_VERSION

    @classmethod
    def is_version_related(cls, version_type: EnumVersionUnionType) -> bool:
        """Check if the version type is related to versioning."""
        # Future-proof: derive from all enum members
        return version_type in set(cls)

    @classmethod
    def get_all_version_types(cls) -> list[EnumVersionUnionType]:
        """Get all version union types."""
        # Future-proof: derive from all enum members
        return list(cls)


# Export for use
__all__ = ["EnumVersionUnionType"]
