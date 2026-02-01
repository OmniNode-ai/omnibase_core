"""
Canonical enum for Consul KV watch event types.

Defines the types of events that can be triggered by Consul KV watchers.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumWatchEventType(StrValueHelper, str, Enum):
    """
    Watch event types for Consul KV monitoring.

    Represents different types of events that can be detected
    when watching Consul KV changes.
    """

    KV_CHANGED = "kv_changed"
    KV_DELETED = "kv_deleted"
    KV_CREATED = "kv_created"
    SERVICE_REGISTERED = "service_registered"
    SERVICE_DEREGISTERED = "service_deregistered"
    SERVICE_HEALTH_CHANGED = "service_health_changed"
    WATCH_ERROR = "watch_error"
    WATCH_TIMEOUT = "watch_timeout"
    WATCH_RECONNECTED = "watch_reconnected"


__all__ = ["EnumWatchEventType"]
