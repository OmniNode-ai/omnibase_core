# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Retrieval Source Type Enum for Context Integrity.

Defines the types of retrieval sources available for context integrity
constraints: VECTOR (vector database), STRUCTURED (relational/structured
data), and FILE (filesystem).
"""

from __future__ import annotations

from enum import Enum


class EnumRetrievalSourceType(str, Enum):
    """Type of retrieval source for context integrity."""

    VECTOR = "vector"
    STRUCTURED = "structured"
    FILE = "file"


__all__ = [
    "EnumRetrievalSourceType",
]
