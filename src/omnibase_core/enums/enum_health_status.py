"""Canonical health status enum for ONEX framework.

**BREAKING CHANGE** (OMN-1310): This enum consolidates multiple previous
health status enums into a single canonical source. No backwards
compatibility is provided.

**Consolidated enums**:
- EnumHealthStatusType (deleted from enum_health_status_type.py)
- EnumNodeHealthStatus (deleted from enum_node_health_status.py)

**Usage**: Import directly from omnibase_core.enums::

    from omnibase_core.enums import EnumHealthStatus

**Semantic Category**: Health (system/component health states)

**Migration**: Replace all imports of EnumHealthStatusType or
EnumNodeHealthStatus with EnumHealthStatus from omnibase_core.enums.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumHealthStatus(StrValueHelper, str, Enum):
    """Canonical health status enum for all ONEX system components.

    This is the single source of truth for health status values across
    the ONEX framework. Use for all health monitoring, health checks,
    and component status reporting.

    **Semantic Category**: Health (system/component health states)

    **Applies To**:
    - LLM providers
    - Nodes
    - Services
    - Tools
    - Registries
    - All other system components

    Values:
        HEALTHY: Component is fully operational
        DEGRADED: Component is operational with reduced capability
        UNHEALTHY: Component is not functioning correctly
        CRITICAL: Component has critical issues requiring immediate attention
        UNKNOWN: Health state cannot be determined
        WARNING: Component has issues that may lead to degradation
        UNREACHABLE: Component cannot be reached for health check
        AVAILABLE: Component is available for use
        UNAVAILABLE: Component is not available
        ERROR: Component encountered an error
        INITIALIZING: Component is starting up
        DISPOSING: Component is shutting down

    Helper Methods:
        - :meth:`is_operational`: Check if component can serve requests
        - :meth:`requires_attention`: Check if immediate action needed
        - :meth:`is_transitional`: Check if component is starting/stopping

    .. versionchanged:: 0.6.4
        Consolidated EnumHealthStatusType and EnumNodeHealthStatus
        into this enum (OMN-1310)
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
    INITIALIZING = "initializing"
    DISPOSING = "disposing"

    def is_operational(self) -> bool:
        """Check if the service is operational despite potential issues."""
        return self in {self.HEALTHY, self.DEGRADED, self.AVAILABLE, self.WARNING}

    def requires_attention(self) -> bool:
        """Check if this status requires immediate attention."""
        return self in {self.UNHEALTHY, self.CRITICAL, self.ERROR, self.UNREACHABLE}

    def is_transitional(self) -> bool:
        """Check if this status indicates a transitional state."""
        return self in {self.INITIALIZING, self.DISPOSING}
