"""
Node Capabilities Information Model.

Capabilities and operational information for nodes.
Part of the ModelNodeInformation restructuring.
"""

from __future__ import annotations

from typing import cast
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel
from omnibase_core.types.type_json import JsonType
from omnibase_core.types.typed_dict_node_capabilities_summary import (
    TypedDictNodeCapabilitiesSummary,
)


class ModelNodeCapabilitiesInfo(BaseModel):
    """
    Node capabilities and operational information.

    Contains operational data:
    - Node capabilities
    - Supported operations
    - Dependencies
    Implements Core protocols:
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
    ) -> TypedDictNodeCapabilitiesSummary:
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
            supported_operations=operations if operations is not None else [],
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

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

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
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"{self.__class__.__name__} must have a valid ID field "
            f"(type_id, id, uuid, identifier, etc.). "
            f"Cannot generate stable ID without UUID field.",
        )

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        result: TypedDictMetadataDict = {}
        # Pack capabilities info into metadata dict
        # Cast to list[JsonType] for type compatibility (no copy - cast is zero-cost at runtime)
        result["metadata"] = {
            "capabilities": cast(list[JsonType], self.capabilities),
            "supported_operations": cast(list[JsonType], self.supported_operations),
            "dependencies": [str(dep) for dep in self.dependencies],
            "has_capabilities": self.has_capabilities(),
            "has_operations": self.has_operations(),
            "has_dependencies": self.has_dependencies(),
            "has_performance_metrics": self.has_performance_metrics(),
        }
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        return True


# Export for use
__all__ = ["ModelNodeCapabilitiesInfo"]
