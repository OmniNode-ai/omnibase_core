"""
Dependency Node Model

Node in the dependency graph.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_document_freshness_actions import EnumDocumentType


class ModelDependencyNode(BaseModel):
    """Node in the dependency graph."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    id: str = Field(description="Unique identifier for the node")
    path: str = Field(description="File path")
    type: EnumDocumentType = Field(description="Type of file")
    freshness_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Freshness score for this node",
    )
