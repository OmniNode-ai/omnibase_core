# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import Field, field_validator

from omnibase_core.models.primitives.model_semver import ModelSemVer

"""
Model for node information in introspection metadata.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.primitives.model_semver import parse_semver_from_string


class ModelIntrospectionNodeInfo(BaseModel):
    """Node information for introspection metadata."""

    model_config = ConfigDict(extra="forbid")

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
    def validate_node_version(cls, value: object) -> ModelSemVer:
        """Validate the required version without inventing missing authority."""
        if isinstance(value, ModelSemVer):
            return value
        if isinstance(value, dict):
            return ModelSemVer.model_validate(value)
        if isinstance(value, str):
            # Parse string version to ModelSemVer
            return parse_semver_from_string(value)
        raise ValueError(
            "node_version must be a ModelSemVer, complete mapping, or SemVer string; "
            f"got {type(value).__name__}"
        )
