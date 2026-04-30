# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""TypedDict contract for Python symbol extraction metadata."""

from __future__ import annotations

from typing import Literal, TypedDict

type SymbolKind = Literal["function", "class", "method"]


class TypedDictSymbolMetadata(TypedDict):
    kind: SymbolKind
    signature: str
    body_hash: str
    start_line: int
    end_line: int


type SymbolTable = dict[str, TypedDictSymbolMetadata]

__all__ = ["SymbolKind", "SymbolTable", "TypedDictSymbolMetadata"]
