"""
Routing strategy enum for ORCHESTRATOR node configurations.
"""

from enum import Enum


class EnumRoutingStrategy(str, Enum):
    """Supported routing strategies for ORCHESTRATOR nodes."""

    ROUND_ROBIN = "round_robin"
    HASH = "hash"
    WEIGHTED = "weighted"
    RANDOM = "random"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_RESPONSE_TIME = "least_response_time"
    HEALTH_BASED = "health_based"
    GEOGRAPHIC = "geographic"
    CUSTOM = "custom"
