"""
TypedDict for handler metadata.

This TypedDict defines the structure returned by ProtocolHandler.describe(),
providing typed access to handler registration and discovery metadata.

The TypedDict uses `total=False` to allow handler implementations to include
only the fields relevant to their specific handler type.

Related:
    - OMN-226: ProtocolHandler protocol
    - ProtocolHandler.describe(): Returns this type

.. versionadded:: 0.4.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = ["TypedDictHandlerMetadata"]


class TypedDictHandlerMetadata(TypedDict, total=False):
    """TypedDict for handler metadata returned by ProtocolHandler.describe().

    All fields are optional (total=False) to allow handler implementations
    flexibility in what metadata they expose. Common fields are defined here
    for type safety and IDE support.

    Attributes:
        name: Human-readable handler name (e.g., "http_handler").
        version: Handler version as ModelSemVer.
        description: Brief description of the handler's purpose.
        capabilities: List of supported operations/features.
    """

    name: str
    version: ModelSemVer
    description: str
    capabilities: list[str]
