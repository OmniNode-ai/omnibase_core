"""API endpoint patterns for proxy."""

from enum import Enum, unique


@unique
class EnumProxyEndpoint(str, Enum):
    """API endpoint patterns for proxy."""

    V1_MESSAGES = "v1/messages"
    V1_COMPLETE = "v1/complete"
