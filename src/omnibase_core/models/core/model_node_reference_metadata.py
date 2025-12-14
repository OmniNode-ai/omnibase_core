"""
Node Reference Metadata Model.

Metadata specific to node references with capabilities,
performance hints, and routing preferences.
"""

from pydantic import Field

from omnibase_core.models.configuration.model_performance_hints import (
    ModelPerformanceHints,
)
from omnibase_core.models.core.model_capability import ModelCapability
from omnibase_core.models.services.model_routing_preferences import (
    ModelRoutingPreferences,
)

from .model_metadata_base import ModelMetadataBase


class ModelNodeReferenceMetadata(ModelMetadataBase):
    """
    Metadata specific to node references.

    Extends base metadata with node-specific information like
    capabilities, performance characteristics, and routing preferences.
    """

    capabilities_required: list[ModelCapability] = Field(
        default_factory=list,
        description="Required capabilities for this node",
    )
    capabilities_provided: list[ModelCapability] = Field(
        default_factory=list,
        description="Capabilities provided by this node",
    )
    performance_hints: ModelPerformanceHints | None = Field(
        default=None,
        description="Performance optimization hints",
    )
    routing_preferences: ModelRoutingPreferences | None = Field(
        default=None,
        description="Routing preferences for load balancing",
    )
    description: str | None = Field(
        default=None, description="Human-readable description"
    )
    maintainer: str | None = Field(default=None, description="Node maintainer")

    def has_capability(self, capability: ModelCapability) -> bool:
        """Check if node provides a specific capability."""
        return any(cap.matches(capability) for cap in self.capabilities_provided)

    def requires_capability(self, capability: ModelCapability) -> bool:
        """Check if node requires a specific capability."""
        return any(cap.matches(capability) for cap in self.capabilities_required)

    def is_compatible_with(self, other_capabilities: list[ModelCapability]) -> bool:
        """Check if node's requirements are satisfied by available capabilities."""
        for required in self.capabilities_required:
            found = False
            for provided in other_capabilities:
                if provided.matches(required):
                    found = True
                    break
            if not found:
                return False
        return True
