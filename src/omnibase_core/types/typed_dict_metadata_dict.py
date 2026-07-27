# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
TypedDictMetadataDict.

Typed structure for metadata dictionary in protocol methods.
"""

from typing import TYPE_CHECKING, TypedDict

from omnibase_core.types.type_serializable_value import SerializableValue

if TYPE_CHECKING:
    from omnibase_core.types.type_semver import ProtocolSemVer


class TypedDictMetadataDict(TypedDict, total=False):
    """Typed structure for metadata dictionary in protocol methods."""

    name: str
    description: str
    version: "ProtocolSemVer"
    tags: list[str]
    metadata: dict[str, SerializableValue]


__all__ = ["TypedDictMetadataDict"]
