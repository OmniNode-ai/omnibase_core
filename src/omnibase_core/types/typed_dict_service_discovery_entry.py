# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
TypedDict for service discovery entry representation.

Used by ProtocolServiceDiscovery to type the returned service dictionaries
without requiring dict[str, Any] anti-patterns.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictServiceDiscoveryEntry(TypedDict, total=False):
    """Typed representation of a discovered service instance.

    All fields are optional (total=False) since different discovery backends
    may return different subsets of metadata.

    Attributes:
        id: Unique service instance identifier.
        name: Service name (e.g. "omnibase-runtime").
        address: Service host/IP address.
        port: Service port number.
        tags: List of service tags for filtering.
        metadata: Additional key-value metadata (string values only).
    """

    id: str
    name: str
    address: str
    port: int
    tags: list[str]
    metadata: dict[str, str]


__all__ = ["TypedDictServiceDiscoveryEntry"]
