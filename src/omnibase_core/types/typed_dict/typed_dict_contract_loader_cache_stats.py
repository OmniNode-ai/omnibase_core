# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""TypedDict for contract loader cache statistics.

See Also:
    OMN-554: Optional caching for contract loading in high-throughput scenarios.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictContractLoaderCacheStats(TypedDict):
    """TypedDict for contract loader cache hit/miss/size statistics."""

    enabled: bool
    entries: int
    hits: int
    misses: int
    evictions: int
    hit_ratio: float


__all__ = ["TypedDictContractLoaderCacheStats"]
