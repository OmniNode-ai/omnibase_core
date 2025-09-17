"""
Node Type Model.

Extensible node type definition that replaces restrictive enums
with flexible, plugin-extensible node type configuration.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.configuration.model_performance_constraints import (
    ModelPerformanceConstraints,
)
from omnibase_core.models.core.model_capability import ModelCapability


class ModelNodeType(BaseModel):
    """
    Extensible node type definition.

    Replaces hardcoded NodeType enum with flexible model that
    allows plugins to define custom node types.
    """

    type_name: str = Field(
        ...,
        description="Node type identifier",
        pattern="^[a-z][a-z0-9_]*$",
    )
    category: str = Field(
        ...,
        description="Node category",
        pattern="^(core|extension|plugin|custom)$",
    )
    display_name: str = Field(..., description="Human-readable type name")
    description: str = Field(..., description="Description of what this node type does")
    capabilities_provided: list[ModelCapability] = Field(
        default_factory=list,
        description="Capabilities this type provides",
    )
    capabilities_required: list[ModelCapability] = Field(
        default_factory=list,
        description="Capabilities this type requires",
    )
    resource_requirements: ModelPerformanceConstraints = Field(
        default_factory=ModelPerformanceConstraints,
        description="Resource requirements",
    )
    is_singleton: bool = Field(default=False, description="Only one instance allowed")
    supports_clustering: bool = Field(
        default=True,
        description="Supports multiple instances",
    )
    version_compatibility: str | None = Field(
        None,
        description="Version compatibility pattern",
    )

    def is_compatible_with(self, available_capabilities: list[ModelCapability]) -> bool:
        """Check if type requirements are satisfied."""
        for required in self.capabilities_required:
            found = False
            for provided in available_capabilities:
                if provided.matches(required):
                    found = True
                    break
            if not found:
                return False
        return True

    def provides_capability(self, capability: ModelCapability) -> bool:
        """Check if type provides a capability."""
        return any(cap.matches(capability) for cap in self.capabilities_provided)

    @classmethod
    def create_core_type(
        cls,
        type_name: str,
        display_name: str,
        description: str,
    ) -> "ModelNodeType":
        """Factory method for core node types."""
        return cls(
            type_name=type_name,
            category="core",
            display_name=display_name,
            description=description,
        )
