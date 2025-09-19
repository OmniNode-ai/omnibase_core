"""
Node operational status enum for lifecycle management.

Defines the operational states that nodes can be in during their lifecycle
for monitoring, management, and debugging purposes.
"""

from enum import Enum


class EnumNodeStatus(str, Enum):
    """Node operational status states."""

    # Active operational states
    ACTIVE = "active"
    RUNNING = "running"
    IDLE = "idle"
    HEALTHY = "healthy"

    # Transition states
    STARTING = "starting"
    STOPPING = "stopping"
    RESTARTING = "restarting"
    UPDATING = "updating"

    # Problem states
    ERROR = "error"
    FAILED = "failed"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRASHED = "crashed"

    # Administrative states
    DISABLED = "disabled"
    MAINTENANCE = "maintenance"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"

    # Registration states
    REGISTERED = "registered"
    PENDING = "pending"
    UNREGISTERED = "unregistered"

    # Unknown/default
    UNKNOWN = "unknown"
