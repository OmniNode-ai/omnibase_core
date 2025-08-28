"""
Model for node information in introspection metadata.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from omnibase.core.models.model_semver import ModelSemVer


class ModelIntrospectionNodeInfo(BaseModel):
    """Node information for introspection metadata."""

    node_name: str = Field(description="Name of the node")
    node_version: ModelSemVer = Field(description="Version of the node as ModelSemVer")
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
        elif isinstance(v, dict):
            # Convert dict to ModelSemVer
            return ModelSemVer(
                major=int(v.get("major", 1)),
                minor=int(v.get("minor", 0)),
                patch=int(v.get("patch", 0)),
                prerelease=v.get("prerelease"),
                build=v.get("build"),
            )
        elif isinstance(v, str):
            # Parse string version to ModelSemVer
            return ModelSemVer.parse(v)
        else:
            # Fallback to default version
            return ModelSemVer(major=1, minor=0, patch=0)

    class Config:
        json_schema_extra = {
            "example": {
                "node_name": "tool_example",
                "node_version": "1.0.0",
                "description": "Example tool",
                "author": "ONEX System",
                "tool_type": "generation",
                "created_at": "2024-01-01T00:00:00",
            }
        }
