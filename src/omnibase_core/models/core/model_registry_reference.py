from uuid import UUID

from pydantic import Field

"""
Model for registry reference in ONEX NodeBase implementation.

This model supports the PATTERN-005 NodeBase functionality for
strongly-typed registry references.

Author: ONEX Framework Team
"""

from pydantic import BaseModel, ConfigDict


class ModelRegistryReference(BaseModel):
    """Model representing a registry reference with metadata."""

    model_config = ConfigDict(extra="ignore")

    node_id: UUID = Field(default=..., description="Node identifier for this registry")
    registry_class_name: str = Field(default=..., description="Registry class name")
    registry_type: str = Field(default=..., description="Registry type classification")
    is_initialized: bool = Field(
        default=True,
        description="Whether registry is initialized",
    )
