"""Registry status model - implements ProtocolServiceRegistryStatus."""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums import (
    EnumHealthStatus,
    EnumInjectionScope,
    EnumOperationStatus,
    EnumServiceLifecycle,
)


class ModelServiceRegistryStatus(BaseModel):
    """
    Service registry status information.

    Implements ProtocolServiceRegistryStatus from omnibase_spi.
    Provides comprehensive status reporting including registration statistics,
    health monitoring, performance metrics, and distribution analysis.

    Attributes:
        registry_id: Unique registry identifier
        status: Overall operational status
        message: Human-readable status description
        total_registrations: Total number of service registrations
        active_instances: Number of currently active service instances
        failed_registrations: Number of failed registrations
        circular_dependencies: Number of detected circular dependencies
        lifecycle_distribution: Distribution of services by lifecycle type
        scope_distribution: Distribution of services by injection scope
        health_summary: Health status distribution across all services
        memory_usage_bytes: Current memory usage (if available)
        average_resolution_time_ms: Average dependency resolution time
        last_updated: When this status was last updated

    Example:
        ```python
        status = await registry.get_registry_status()
        print(f"Registry: {status.registry_id}")
        print(f"Services: {status.total_registrations}")
        print(f"Active instances: {status.active_instances}")
        ```
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    registry_id: UUID = Field(description="Unique registry identifier")
    status: EnumOperationStatus = Field(description="Operational status")
    message: str = Field(description="Status description")
    total_registrations: int = Field(
        default=0,
        description="Total service registrations",
    )
    active_instances: int = Field(
        default=0,
        description="Active service instances",
    )
    failed_registrations: int = Field(
        default=0,
        description="Failed registrations",
    )
    circular_dependencies: int = Field(
        default=0,
        description="Circular dependencies detected",
    )
    lifecycle_distribution: dict[EnumServiceLifecycle, int] = Field(
        default_factory=dict,
        description="Services by lifecycle type",
    )
    scope_distribution: dict[EnumInjectionScope, int] = Field(
        default_factory=dict,
        description="Services by injection scope",
    )
    health_summary: dict[EnumHealthStatus, int] = Field(
        default_factory=dict,
        description="Health status distribution",
    )
    memory_usage_bytes: int | None = Field(
        default=None,
        description="Current memory usage",
    )
    average_resolution_time_ms: float | None = Field(
        default=None,
        description="Average resolution time",
    )
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last update timestamp",
    )

    def is_healthy(self) -> bool:
        """
        Check if registry is in healthy state.

        Returns:
            True if status is success and no critical issues
        """
        return (
            self.status == EnumOperationStatus.SUCCESS
            and self.circular_dependencies == 0
            and self.failed_registrations == 0
        )

    def get_health_percentage(self) -> float:
        """
        Calculate percentage of healthy services.

        Returns:
            Percentage of services in healthy state (0.0-100.0)
        """
        if self.total_registrations == 0:
            return 100.0

        healthy_count = self.health_summary.get(EnumHealthStatus.HEALTHY, 0)
        return (healthy_count / self.total_registrations) * 100.0
