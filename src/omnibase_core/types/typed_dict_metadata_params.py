from __future__ import annotations

from typing import TypedDict

"""Metadata-related factory parameters."""


class TypedDictMetadataParams(TypedDict, total=False):
    """Metadata-related factory parameters."""

    name: str
    value: str
    description: str
    deprecated: bool
    experimental: bool


__all__ = ["TypedDictMetadataParams"]
