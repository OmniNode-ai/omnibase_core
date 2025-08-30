"""Discovery status enumeration for ONEX tool discovery operations."""

from enum import Enum


class EnumDiscoveryStatus(str, Enum):
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
