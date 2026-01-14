"""Metadata-related factory parameters."""

from __future__ import annotations

from typing import TypedDict


class TypedDictMetadataParams(TypedDict, total=False):
    name: str
    value: str
    description: str
    deprecated: bool
    experimental: bool


__all__ = ["TypedDictMetadataParams"]
