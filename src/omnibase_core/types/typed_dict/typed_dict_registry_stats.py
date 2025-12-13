"""TypedDict for registry statistics from MixinServiceRegistry."""

from __future__ import annotations

from typing import TypedDict


class TypedDictRegistryStats(TypedDict):
    """TypedDict for registry statistics from MixinServiceRegistry."""

    total_services: int
    online_services: int
    offline_services: int
    domain_filter: str | None
    registry_started: bool


__all__ = ["TypedDictRegistryStats"]
