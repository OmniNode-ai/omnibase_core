# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
TypedDict for service health status representation.

Used by ProtocolServiceDiscovery to type the returned health status dictionaries
without requiring dict[str, Any] anti-patterns.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictServiceHealthStatus(TypedDict):
    """Typed representation of a service health status.

    Attributes:
        status: Health status string — one of "passing", "warning",
            "critical", or "unknown".
        message: Human-readable status message.
        last_check: ISO 8601 timestamp of the last health check.
    """

    status: str
    message: str
    last_check: str


__all__ = ["TypedDictServiceHealthStatus"]
