"""API endpoint patterns for proxy."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumProxyEndpoint(StrValueHelper, str, Enum):
    """API endpoint patterns for proxy."""

    V1_MESSAGES = "v1/messages"
    V1_COMPLETE = "v1/complete"


__all__ = ["EnumProxyEndpoint"]
