"""Service Dependency Model.

Represents a service dependency with health check requirements.
"""

from dataclasses import dataclass

from omnibase_core.enums.enum_service_tier import EnumServiceTier


@dataclass
class ModelServiceDependency:
    """Represents a service dependency with health check requirements."""

    service_name: str
    condition: str = (
        "service_healthy"  # service_healthy, service_started, service_completed
    )
    optional: bool = False
    tier: EnumServiceTier = EnumServiceTier.APPLICATION
