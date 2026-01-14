"""
Connection type enumeration for network operations.

Provides strongly typed connection type values for network configurations.
Follows ONEX one-enum-per-file naming conventions.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumConnectionType(StrValueHelper, str, Enum):
    """
    Strongly typed connection type for network operations.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    TCP = "tcp"
    HTTP = "http"
    HTTPS = "https"
    WEBSOCKET = "websocket"
    WEBSOCKET_SECURE = "websocket_secure"
    GRPC = "grpc"
    UDP = "udp"
    UNIX_SOCKET = "unix_socket"

    @classmethod
    def is_secure(cls, connection_type: EnumConnectionType) -> bool:
        """Check if the connection type is secure."""
        return connection_type in {cls.HTTPS, cls.WEBSOCKET_SECURE, cls.GRPC}

    @classmethod
    def is_persistent(cls, connection_type: EnumConnectionType) -> bool:
        """Check if the connection type supports persistent connections."""
        return connection_type in {
            cls.TCP,
            cls.WEBSOCKET,
            cls.WEBSOCKET_SECURE,
            cls.GRPC,
            cls.UNIX_SOCKET,
        }

    @classmethod
    def default_port(cls, connection_type: EnumConnectionType) -> int | None:
        """Get the default port for the connection type."""
        port_map = {
            cls.HTTP: 80,
            cls.HTTPS: 443,
            cls.WEBSOCKET: 80,
            cls.WEBSOCKET_SECURE: 443,
            cls.GRPC: 9090,
        }
        return port_map.get(connection_type)


# Export for use
__all__ = ["EnumConnectionType"]
