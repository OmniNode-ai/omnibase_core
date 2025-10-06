from typing import Any, Dict

from pydantic import Field

"""
Core model for node metadata information.

Structured model for node metadata, replacing Dict[str, Any]
usage with proper typing. This is the core model that should be
used by all systems requiring node metadata.
"""

from pydantic import BaseModel, Field


class ModelNodeMetadata(BaseModel):
    """
    Structured model for node metadata.

    Replaces Dict[str, Any] with proper typing for metadata.
    This is the core model used across all ONEX systems.
    """

    created_at: str | None = Field(None, description="Creation timestamp")
    updated_at: str | None = Field(None, description="Last update timestamp")
    author: str | None = Field(None, description="Node author")
    license: str | None = Field(None, description="License information")
    repository: str | None = Field(None, description="Source repository")
    documentation_url: str | None = Field(None, description="Documentation URL")
    tags: list[str] = Field(default_factory=list, description="Node tags")
    version: str | None = Field(None, description="Node version")
    description: str | None = Field(None, description="Node description")
    category: str | None = Field(None, description="Node category")
    dependencies: list[str] = Field(
        default_factory=list,
        description="Node dependencies",
    )
