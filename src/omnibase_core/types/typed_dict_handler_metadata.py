"""
TypedDict for handler metadata.

This TypedDict defines the structure returned by ProtocolHandler.describe(),
providing typed access to handler registration and discovery metadata.

The TypedDict uses `total=False` with explicit `Required[]` and `NotRequired[]`
markers to distinguish between mandatory fields (name, version) and optional
fields (description, capabilities).

Related:
    - OMN-226: ProtocolHandler protocol
    - ProtocolHandler.describe(): Returns this type

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = ["TypedDictHandlerMetadata"]

from typing import TYPE_CHECKING, NotRequired, Required, TypedDict

if TYPE_CHECKING:
    from omnibase_core.models.primitives.model_semver import ModelSemVer


class TypedDictHandlerMetadata(TypedDict, total=False):
    """TypedDict for handler metadata returned by ProtocolHandler.describe().

    This TypedDict defines the contract for handler metadata with explicit
    required and optional fields.

    Required Fields:
        name: Human-readable handler name (e.g., "http_handler").
        version: Handler version as ModelSemVer.

    Optional Fields:
        description: Brief description of the handler's purpose.
        capabilities: List of supported operations/features.

    Example:
        >>> metadata: TypedDictHandlerMetadata = {
        ...     "name": "http_handler",
        ...     "version": ModelSemVer(major=1, minor=0, patch=0),
        ...     "description": "Handles HTTP requests",  # optional
        ... }
    """

    name: Required[str]
    version: Required[ModelSemVer]
    description: NotRequired[str]
    capabilities: NotRequired[list[str]]
