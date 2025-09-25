"""
Node Capabilities Information Model.

Capabilities and operational information for nodes.
Part of the ModelNodeInformation restructuring.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from .model_types_node_capabilities_summary import ModelNodeCapabilitiesSummaryType


class ModelNodeCapabilitiesInfo(BaseModel):
    """
    Node capabilities and operational information.

    Contains operational data:
    - Node capabilities
    - Supported operations
    - Dependencies
    """

    # Capabilities and operations (2 fields)
    capabilities: list[str] = Field(
        default_factory=list,
        description="Node capabilities",
    )
    supported_operations: list[str] = Field(
        default_factory=list,
        description="Supported operations",
    )

    # Dependencies (1 field)
    dependencies: list[UUID] = Field(
        default_factory=list,
        description="Node dependencies",
    )

    # Performance metrics (1 field, but structured)
    performance_metrics: dict[str, float] | None = Field(
        None,
        description="Performance metrics",
    )

    def has_capabilities(self) -> bool:
        """Check if node has capabilities."""
        return len(self.capabilities) > 0

    def has_operations(self) -> bool:
        """Check if node has supported operations."""
        return len(self.supported_operations) > 0

    def has_dependencies(self) -> bool:
        """Check if node has dependencies."""
        return len(self.dependencies) > 0

    def has_performance_metrics(self) -> bool:
        """Check if node has performance metrics."""
        return (
            self.performance_metrics is not None and len(self.performance_metrics) > 0
        )

    def add_capability(self, capability: str) -> None:
        """Add a capability if not already present."""
        if capability not in self.capabilities:
            self.capabilities.append(capability)

    def add_operation(self, operation: str) -> None:
        """Add a supported operation if not already present."""
        if operation not in self.supported_operations:
            self.supported_operations.append(operation)

    def add_dependency(self, dependency: UUID) -> None:
        """Add a dependency if not already present."""
        if dependency not in self.dependencies:
            self.dependencies.append(dependency)

    def set_performance_metric(self, metric_name: str, value: float) -> None:
        """Set a performance metric."""
        if self.performance_metrics is None:
            self.performance_metrics = {}
        self.performance_metrics[metric_name] = value

    def get_performance_metric(self, metric_name: str) -> float | None:
        """Get a performance metric value."""
        if self.performance_metrics is None:
            return None
        return self.performance_metrics.get(metric_name)

    def get_capabilities_summary(
        self,
    ) -> ModelNodeCapabilitiesSummaryType:
        """Get capabilities information summary."""
        return {
            "capabilities_count": len(self.capabilities),
            "operations_count": len(self.supported_operations),
            "dependencies_count": len(self.dependencies),
            "has_capabilities": self.has_capabilities(),
            "has_operations": self.has_operations(),
            "has_dependencies": self.has_dependencies(),
            "has_performance_metrics": self.has_performance_metrics(),
            "primary_capability": self.capabilities[0] if self.capabilities else None,
            "metrics_count": (
                len(self.performance_metrics) if self.performance_metrics else 0
            ),
        }

    @classmethod
    def create_with_capabilities(
        cls,
        capabilities: list[str],
        operations: list[str] | None = None,
    ) -> ModelNodeCapabilitiesInfo:
        """Create capabilities info with capabilities and operations."""
        return cls(
            capabilities=capabilities,
            supported_operations=operations or [],
            performance_metrics=None,
        )

    @classmethod
    def create_with_dependencies(
        cls,
        dependencies: list[UUID],
    ) -> ModelNodeCapabilitiesInfo:
        """Create capabilities info with dependencies."""
        return cls(
            dependencies=dependencies,
            performance_metrics=None,
        )


# Export for use
__all__ = ["ModelNodeCapabilitiesInfo"]
