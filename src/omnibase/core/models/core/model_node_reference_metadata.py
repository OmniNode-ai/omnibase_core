"""
Node Reference Metadata Model.

Metadata specific to node references with capabilities,
performance hints, and routing preferences.
"""

from typing import List, Optional

from pydantic import Field

from omnibase.model.configuration.model_performance_hints import ModelPerformanceHints
from omnibase.model.core.model_capability import ModelCapability
from omnibase.model.service.model_routing_preferences import ModelRoutingPreferences

from .model_metadata_base import ModelMetadataBase


class ModelNodeReferenceMetadata(ModelMetadataBase):
    """
    Metadata specific to node references.

    Extends base metadata with node-specific information like
    capabilities, performance characteristics, and routing preferences.
    """

    capabilities_required: List[ModelCapability] = Field(
        default_factory=list, description="Required capabilities for this node"
    )
    capabilities_provided: List[ModelCapability] = Field(
        default_factory=list, description="Capabilities provided by this node"
    )
    performance_hints: Optional[ModelPerformanceHints] = Field(
        None, description="Performance optimization hints"
    )
    routing_preferences: Optional[ModelRoutingPreferences] = Field(
        None, description="Routing preferences for load balancing"
    )
    description: Optional[str] = Field(None, description="Human-readable description")
    maintainer: Optional[str] = Field(None, description="Node maintainer")

    def has_capability(self, capability: ModelCapability) -> bool:
        """Check if node provides a specific capability."""
        for cap in self.capabilities_provided:
            if cap.matches(capability):
                return True
        return False

    def requires_capability(self, capability: ModelCapability) -> bool:
        """Check if node requires a specific capability."""
        for cap in self.capabilities_required:
            if cap.matches(capability):
                return True
        return False

    def is_compatible_with(self, other_capabilities: List[ModelCapability]) -> bool:
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
