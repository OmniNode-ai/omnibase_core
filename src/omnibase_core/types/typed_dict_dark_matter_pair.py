# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""TypedDict definition for a co-change dark matter pair."""

from typing import TypedDict


class TypedDictDarkMatterPair(TypedDict):
    """A file pair with strong co-change correlation not explained by static imports."""

    a: str
    b: str
    npmi: float
    co_changes: int


__all__ = [
    "TypedDictDarkMatterPair",
]
