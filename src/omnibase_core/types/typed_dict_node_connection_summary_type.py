"""
TypedDict for node connection summary.

Strongly-typed representation for node connection settings summary data.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictNodeConnectionSummaryType(TypedDict):
    """
    Strongly-typed dictionary for node connection settings summary.

    Replaces dict[str, Any] return type from get_connection_summary()
    with proper type structure.
    """

    endpoint: str | None
    port: int | None
    protocol: str | None
    has_endpoint: bool
    has_port: bool
    has_protocol: bool
    is_fully_configured: bool
    is_secure: bool
    connection_url: str | None


__all__ = ["TypedDictNodeConnectionSummaryType"]
