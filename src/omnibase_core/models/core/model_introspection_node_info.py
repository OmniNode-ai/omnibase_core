"""
Model for node information in introspection metadata.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from omnibase_core.models.core.model_semver import ModelSemVer


class ModelIntrospectionNodeInfo(BaseModel):
    """Node information for introspection metadata."""

    node_name: str = Field(description="Name of the node")
    node_version: ModelSemVer = Field(description="Version of the node as ModelSemVer")
    description: str = Field(description="Description of the node")
    author: str = Field(default="ONEX System", description="Author of the node")
    node_type: str = Field(description="Type of node")
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
            # Convert dict to ModelSemVer
            return ModelSemVer(
                major=int(v.get("major", 1)),
                minor=int(v.get("minor", 0)),
                patch=int(v.get("patch", 0)),
            )
        if isinstance(v, str):
            # Parse string version to ModelSemVer
            parts = v.split(".")
            if len(parts) >= 3:
                return ModelSemVer(
                    major=int(parts[0]), minor=int(parts[1]), patch=int(parts[2])
                )
            elif len(parts) == 2:
                return ModelSemVer(major=int(parts[0]), minor=int(parts[1]), patch=0)
            elif len(parts) == 1:
                return ModelSemVer(major=int(parts[0]), minor=0, patch=0)
            else:
                return ModelSemVer(major=1, minor=0, patch=0)
        # Fallback to default version
        return ModelSemVer(major=1, minor=0, patch=0)

    class Config:
        json_schema_extra = {
            "example": {
                "node_name": "node_example",
                "node_version": "1.0.0",
                "description": "Example node",
                "author": "ONEX System",
                "node_type": "generation",
                "created_at": "2024-01-01T00:00:00",
            },
        }
