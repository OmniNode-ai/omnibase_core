"""Discovery status enumeration for ONEX tool discovery operations."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumDiscoveryStatus(StrValueHelper, str, Enum):
    """Discovery status values for tool discovery operations."""

    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    PARTIAL = "partial"
    CACHED = "cached"
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    COMPLETED = "completed"


__all__ = ["EnumDiscoveryStatus"]
