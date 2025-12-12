"""TypedDict for node capability flags.

Describes what features and behaviors a node supports.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictNodeCapabilities(TypedDict):
    """
    TypedDict for node capability flags.

    Describes what features and behaviors a node supports.
    """

    supports_async_processing: bool
    supports_lifecycle_management: bool
    supports_metrics_collection: bool
    supports_event_emission: bool
    supports_contract_loading: bool
    supports_introspection: bool
    supports_dependency_injection: bool


__all__ = ["TypedDictNodeCapabilities"]
