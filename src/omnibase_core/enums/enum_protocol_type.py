"""
Protocol Type Enum.

Defines communication protocols for node configurations.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumProtocolType(StrValueHelper, str, Enum):
    """Communication protocol types."""

    HTTP = "http"
    HTTPS = "https"
    TCP = "tcp"
    UDP = "udp"
    WEBSOCKET = "websocket"
    GRPC = "grpc"
    REST = "rest"
    GRAPHQL = "graphql"


# Export for use
__all__ = ["EnumProtocolType"]
