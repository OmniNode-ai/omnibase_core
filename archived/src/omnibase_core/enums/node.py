#!/usr/bin/env python3
"""
Node-related enums for ONEX architecture.

Defines node types, status values, and health monitoring states
for the ONEX distributed node system.
"""

from enum import Enum


class EnumNodeType(str, Enum):
    """
    Node type classification for 4-node RSD architecture.

    Defines the specialized node types with their functional characteristics:
    - COMPUTE: Pure computation without side effects
    - EFFECT: Side effects, I/O operations, external interactions
    - REDUCER: Data aggregation, streaming, conflict resolution
    - ORCHESTRATOR: Workflow coordination, thunk emission, event management
    """

    COMPUTE = "COMPUTE"
    EFFECT = "EFFECT"
    REDUCER = "REDUCER"
    ORCHESTRATOR = "ORCHESTRATOR"


class EnumNodeStatus(str, Enum):
    """
    Operational status values for ONEX nodes.

    Represents the current operational state of nodes in the system.
    """

    ACTIVE = "active"
    INACTIVE = "inactive"
    STARTING = "starting"
    STOPPING = "stopping"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class EnumHealthStatus(str, Enum):
    """
    Health status for system monitoring and health checks.

    Provides strongly-typed health status values for provider health checks
    and monitoring components.
    """

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"
    WARNING = "warning"
    UNREACHABLE = "unreachable"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ERROR = "error"
