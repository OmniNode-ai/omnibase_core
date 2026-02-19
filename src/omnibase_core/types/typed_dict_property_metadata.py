# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
TypedDict for property metadata structures.

This TypedDict provides type safety for property metadata dict[str, Any]ionaries
used in environment properties collection systems.
"""

from typing_extensions import TypedDict


class TypedDictPropertyMetadata(TypedDict, total=False):
    """Metadata for environment properties."""

    description: str
    source: str


__all__ = ["TypedDictPropertyMetadata"]
