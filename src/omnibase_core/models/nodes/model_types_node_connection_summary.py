"""
TypedDict for node connection summary.

Replaces dict[str, Any] return type with structured typing.
"""

from __future__ import annotations

from typing import Any, TypedDict


class ModelNodeConnectionSummaryType(TypedDict):
    """
    Typed dictionary for node connection settings summary.

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


# Export for use
__all__ = ["ModelNodeConnectionSummaryType"]
