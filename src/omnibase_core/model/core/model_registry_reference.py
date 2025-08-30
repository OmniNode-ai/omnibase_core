"""
Model for registry reference in ONEX NodeBase implementation.

This model supports the PATTERN-005 NodeBase functionality for
strongly-typed registry references.

Author: ONEX Framework Team
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelRegistryReference(BaseModel):
    """Model representing a registry reference with metadata."""

    model_config = ConfigDict(extra="ignore")

    node_id: str = Field(..., description="Node identifier for this registry")
    registry_class_name: str = Field(..., description="Registry class name")
    registry_type: str = Field(..., description="Registry type classification")
    is_initialized: bool = Field(
        default=True,
        description="Whether registry is initialized",
    )
