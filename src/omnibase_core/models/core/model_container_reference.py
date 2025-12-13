"""
Model for container reference in ONEX NodeBase implementation.

This model supports the PATTERN-005 NodeBase functionality for
strongly-typed container references.

"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelContainerReference(BaseModel):
    """Model representing a container reference with metadata."""

    model_config = ConfigDict(extra="ignore")

    node_id: UUID = Field(default=..., description="Node identifier for this container")
    container_class_name: str = Field(default=..., description="Container class name")
    container_type: str = Field(
        default=..., description="Container type classification"
    )
    is_initialized: bool = Field(
        default=True,
        description="Whether container is initialized",
    )
