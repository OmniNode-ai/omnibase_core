"""
Core model for node metadata information.

Structured model for node metadata, replacing Dict[str, Any]
usage with proper typing. This is the core model that should be
used by all systems requiring node metadata.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelNodeMetadata(BaseModel):
    """
    Structured model for node metadata.

    Replaces Dict[str, Any] with proper typing for metadata.
    This is the core model used across all ONEX systems.
    """

    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")
    author: Optional[str] = Field(None, description="Node author")
    license: Optional[str] = Field(None, description="License information")
    repository: Optional[str] = Field(None, description="Source repository")
    documentation_url: Optional[str] = Field(None, description="Documentation URL")
    tags: List[str] = Field(default_factory=list, description="Node tags")
    version: Optional[str] = Field(None, description="Node version")
    description: Optional[str] = Field(None, description="Node description")
    category: Optional[str] = Field(None, description="Node category")
    dependencies: List[str] = Field(
        default_factory=list, description="Node dependencies"
    )
