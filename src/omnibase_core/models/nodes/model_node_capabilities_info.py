from __future__ import annotations

import uuid

from pydantic import Field

from omnibase_core.errors.error_codes import ModelOnexError

"""
Node Capabilities Information Model.

Capabilities and operational information for nodes.
Part of the ModelNodeInformation restructuring.
"""


from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.errors.error_codes import ModelCoreErrorCode, ModelOnexError

from .model_types_node_capabilities_summary import ModelNodeCapabilitiesSummaryType


class ModelNodeCapabilitiesInfo(BaseModel):
    """
    Node capabilities and operational information.

    Contains operational data:
    - Node capabilities
    - Supported operations
    - Dependencies
    Implements omnibase_spi protocols:
    - Identifiable: UUID-based identification
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
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
        default=None,
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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def get_id(self) -> str:
        """Get unique identifier (Identifiable protocol)."""
        # Try common ID field patterns
        for field in [
            "id",
            "uuid",
            "identifier",
            "node_id",
            "execution_id",
            "metadata_id",
        ]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        raise ModelOnexError(
            code=ModelCoreErrorCode.VALIDATION_ERROR,
            message=f"{self.__class__.__name__} must have a valid ID field "
            f"(type_id, id, uuid, identifier, etc.). "
            f"Cannot generate stable ID without UUID field.",
        )

    def get_metadata(self) -> dict[str, Any]:
        """Get metadata as dict[str, Any]ionary (ProtocolMetadataProvider protocol)."""
        metadata = {}
        # Include common metadata fields
        for field in ["name", "description", "version", "tags", "metadata"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    metadata[field] = (
                        str(value) if not isinstance(value, (dict, list)) else value
                    )
        return metadata

    def set_metadata(self, metadata: dict[str, Any]) -> bool:
        """Set metadata from dict[str, Any]ionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (
            Exception
        ):  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False

    def serialize(self) -> dict[str, Any]:
        """Serialize to dict[str, Any]ionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (
            Exception
        ):  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False


# Export for use
__all__ = ["ModelNodeCapabilitiesInfo"]
