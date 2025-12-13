"""TypedDict for discovery statistics from MixinDiscoveryResponder."""

from __future__ import annotations

from typing import TypedDict


class TypedDictDiscoveryStats(TypedDict):
    """TypedDict for discovery statistics from MixinDiscoveryResponder."""

    node_id: str
    node_name: str
    discovery_count: int
    last_discovery_time: str | None
    is_available: bool
    capabilities: list[str]


__all__ = ["TypedDictDiscoveryStats"]
