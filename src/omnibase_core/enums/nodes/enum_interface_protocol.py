"""
Interface protocol enum for EFFECT node configurations.
"""

from enum import Enum


class EnumInterfaceProtocol(str, Enum):
    """Supported interface protocols for EFFECT nodes."""

    HTTP = "http"
    HTTPS = "https"
    GRPC = "grpc"
    WEBSOCKET = "websocket"
    WEBSOCKET_SECURE = "websocket_secure"
    TCP = "tcp"
    UDP = "udp"
    AMQP = "amqp"
    KAFKA = "kafka"
    REDIS = "redis"
    MQTT = "mqtt"
