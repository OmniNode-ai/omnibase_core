"""
Dependency Edge Model

Edge in the dependency graph.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_document_freshness_actions import \
    EnumDependencyRelationship


class ModelDependencyEdge(BaseModel):
    """Edge in the dependency graph."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    from_node: str = Field(alias="from", description="Source node ID")
    to_node: str = Field(alias="to", description="Target node ID")
    relationship: EnumDependencyRelationship = Field(
        description="Type of dependency relationship"
    )
    strength: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Strength of the dependency"
    )
