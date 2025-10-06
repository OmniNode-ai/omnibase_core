from __future__ import annotations

"""
Protocol Type Enum.

Defines communication protocols for node configurations.
"""


from enum import Enum, unique


@unique
class EnumProtocolType(str, Enum):
    """Communication protocol types."""

    HTTP = "http"
    HTTPS = "https"
    TCP = "tcp"
    UDP = "udp"
    WEBSOCKET = "websocket"
    GRPC = "grpc"
    REST = "rest"
    GRAPHQL = "graphql"

    def __str__(self) -> str:
        return self.value


# Export for use
__all__ = ["EnumProtocolType"]
