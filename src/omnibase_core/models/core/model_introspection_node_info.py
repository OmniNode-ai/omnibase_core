from pydantic import Field, field_validator

from omnibase_core.models.primitives.model_semver import ModelSemVer

"""
Model for node information in introspection metadata.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from omnibase_core.models.primitives.model_semver import parse_semver_from_string


class ModelIntrospectionNodeInfo(BaseModel):
    """Node information for introspection metadata."""

    node_name: str = Field(description="Name of the node")
    node_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Version of the node as ModelSemVer",
    )
    description: str = Field(description="Description of the node")
    author: str = Field(default="ONEX System", description="Author of the node")
    tool_type: str = Field(description="Type of tool")
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Creation timestamp",
    )

    @field_validator("node_version", mode="before")
    @classmethod
    def validate_node_version(cls, v: Any) -> ModelSemVer:
        """Convert various version formats to ModelSemVer."""
        if isinstance(v, ModelSemVer):
            return v
        if isinstance(v, dict):
            # Convert dict[str, Any]to ModelSemVer
            return ModelSemVer(
                major=int(v.get("major", 1)),
                minor=int(v.get("minor", 0)),
                patch=int(v.get("patch", 0)),
            )
        if isinstance(v, str):
            # Parse string version to ModelSemVer
            return parse_semver_from_string(v)
        # Fallback to default version
        return ModelSemVer(major=1, minor=0, patch=0)
