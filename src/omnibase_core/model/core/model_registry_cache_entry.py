"""
Model for registry cache entry in ONEX NodeBase implementation.

This model supports the PATTERN-005 RegistryFactory functionality for
strongly-typed registry caching.

Author: ONEX Framework Team
"""

from pydantic import BaseModel, Field


class ModelRegistryCacheEntry(BaseModel):
    """Model representing a cached registry entry."""

    node_id: str = Field(..., description="Node identifier for this registry")
    registry_class_name: str = Field(..., description="Registry class name")
    creation_timestamp: float = Field(..., description="Registry creation timestamp")
    is_active: bool = Field(default=True, description="Whether registry is active")
