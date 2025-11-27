from pydantic import Field

from omnibase_core.models.primitives.model_semver import ModelSemVer

"\nNode Instance Model\n\nNode instance with health and load information for advanced\ninstance management and service discovery.\n"
from datetime import UTC, datetime

from pydantic import BaseModel

from omnibase_core.enums.enum_node_status import EnumNodeStatus
from omnibase_core.models.configuration.model_load_metrics import ModelLoadMetrics
from omnibase_core.models.core.model_capability import ModelCapability
from omnibase_core.models.core.model_instance_metadata import ModelInstanceMetadata
from omnibase_core.models.core.model_node_reference import ModelNodeReference
from omnibase_core.models.health.model_health_metrics import ModelHealthMetrics
from omnibase_core.models.node_metadata.model_node_type import ModelNodeType


class ModelNodeInstance(BaseModel):
    """
    Node instance with health and load information.

    This model represents a running node instance with comprehensive
    health, load, and capability information for advanced management.
    """

    reference: ModelNodeReference = Field(default=..., description="Node reference")
    status: EnumNodeStatus = Field(default=..., description="Current node status")
    node_type: ModelNodeType = Field(
        default=..., description="Type of this node instance"
    )
    health_metrics: ModelHealthMetrics = Field(
        default_factory=lambda: ModelHealthMetrics(), description="Health metrics"
    )
    load_metrics: ModelLoadMetrics = Field(
        default_factory=lambda: ModelLoadMetrics(), description="Load metrics"
    )
    last_heartbeat: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last heartbeat timestamp",
    )
    registration_time: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Registration timestamp"
    )
    capabilities_verified: list[ModelCapability] = Field(
        default_factory=list, description="Verified capabilities"
    )
    instance_metadata: ModelInstanceMetadata | None = Field(
        default=None, description="Additional metadata"
    )
    connection_url: str | None = Field(
        default=None, description="Connection URL for remote instances"
    )
    protocol_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Protocol version supported",
    )

    def is_healthy(self) -> bool:
        """
        Check if instance is healthy.

        Returns:
            True if instance is healthy and responsive
        """
        heartbeat_age = (datetime.now(UTC) - self.last_heartbeat).total_seconds()
        if heartbeat_age > 30:
            return False
        return self.health_metrics.is_healthy()

    def is_available(self) -> bool:
        """
        Check if instance is available for new work.

        Returns:
            True if instance can accept new work
        """
        return (
            self.status == EnumNodeStatus.ACTIVE
            and self.is_healthy()
            and self.load_metrics.can_accept_load()
        )

    def get_overall_score(self) -> float:
        """
        Calculate overall instance score for load balancing.

        Returns:
            Score from 0.0 to 1.0 where 1.0 is best
        """
        if not self.is_healthy():
            return 0.0
        health_score = self.health_metrics.get_health_score()
        load_score = 1.0 - self.load_metrics.get_load_score()
        return (health_score + load_score) / 2.0

    def has_capability(self, capability: ModelCapability) -> bool:
        """
        Check if instance has a specific capability.

        Args:
            capability: Capability to check

        Returns:
            True if instance has the capability
        """
        for verified in self.capabilities_verified:
            if (
                verified.name == capability.name
                and verified.namespace == capability.namespace
            ):
                return True
        return False

    def update_heartbeat(self) -> None:
        """Update last heartbeat timestamp."""
        self.last_heartbeat = datetime.now(UTC)

    def update_metrics(
        self,
        health: ModelHealthMetrics | None = None,
        load: ModelLoadMetrics | None = None,
    ) -> None:
        """
        Update instance metrics.

        Args:
            health: New health metrics
            load: New load metrics
        """
        if health:
            self.health_metrics = health
        if load:
            self.load_metrics = load
            self.load_metrics.update_saturation()

    def matches_requirements(
        self,
        required_type: ModelNodeType | None = None,
        required_capabilities: list[ModelCapability] | None = None,
        required_labels: dict[str, str] | None = None,
    ) -> bool:
        """
        Check if instance matches requirements.

        Args:
            required_type: Required node type
            required_capabilities: Required capabilities
            required_labels: Required labels

        Returns:
            True if instance matches all requirements
        """
        if required_type and self.node_type.type_name != required_type.type_name:
            return False
        if required_capabilities:
            for cap in required_capabilities:
                if not self.has_capability(cap):
                    return False
        if required_labels and self.instance_metadata:
            if not self.instance_metadata.matches_selector(required_labels):
                return False
        return True
