"""
Health Check Type Enumeration

Defines types of health checks that can be performed on services.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumHealthCheckType(StrValueHelper, str, Enum):
    """Types of health checks available."""

    HTTP_GET = "http_get"
    HTTP_POST = "http_post"
    HTTP_HEAD = "http_head"
    TCP = "tcp"
    COMMAND = "command"
    GRPC = "grpc"
    CUSTOM = "custom"


__all__ = ["EnumHealthCheckType"]
