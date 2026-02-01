"""Canonical health status enum for ONEX framework.

**BREAKING CHANGE** (OMN-1310): This enum consolidates and replaces:

- ``EnumHealthStatusType`` (deleted from ``enum_health_status_type.py``)
- ``EnumNodeHealthStatus`` (deleted from ``enum_node_health_status.py``)

**What breaks**:

- Import paths ``from omnibase_core.enums import EnumHealthStatusType`` and
  ``from omnibase_core.enums import EnumNodeHealthStatus`` no longer exist.
- The old enum files have been deleted; there are no aliases or deprecation
  warnings.

**Why no backwards compatibility**:

- Maintaining multiple enums with overlapping semantics (HEALTHY, UNHEALTHY,
  etc.) caused confusion and inconsistent usage across the codebase.
- A clean break ensures all code converges on a single canonical enum,
  eliminating ambiguity about which enum to use for health status.

**Migration**:

1. Find all imports of ``EnumHealthStatusType`` or ``EnumNodeHealthStatus``.
2. Replace with ``from omnibase_core.enums import EnumHealthStatus``.
3. Update any value references (e.g., ``EnumHealthStatusType.HEALTHY`` becomes
   ``EnumHealthStatus.HEALTHY``).

**Usage**::

    from omnibase_core.enums import EnumHealthStatus

**Semantic Category**: Health (system/component health states)
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
    INITIALIZING = "initializing"
    DISPOSING = "disposing"
    ERROR = "error"

    def is_operational(self) -> bool:
        """Check if the service is operational despite potential issues."""
        return self in {self.HEALTHY, self.DEGRADED, self.AVAILABLE, self.WARNING}

    def requires_attention(self) -> bool:
        """Check if this status requires immediate attention."""
        return self in {self.UNHEALTHY, self.CRITICAL, self.ERROR, self.UNREACHABLE}

    def is_transitional(self) -> bool:
        """Check if this status indicates a transitional state."""
        return self in {self.INITIALIZING, self.DISPOSING}


__all__ = ["EnumHealthStatus"]
