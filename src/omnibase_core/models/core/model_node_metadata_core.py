"""
Core model for node metadata information.

Structured model for node metadata, replacing Dict[str, Any]
usage with proper typing. This is the core model that should be
used by all systems requiring node metadata.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelNodeMetadata(BaseModel):
    """
    Structured model for node metadata.

    Replaces Dict[str, Any] with proper typing for metadata.
    This is the core model used across all ONEX systems.
    """

    created_at: str | None = Field(default=None, description="Creation timestamp")
    updated_at: str | None = Field(default=None, description="Last update timestamp")
    author: str | None = Field(default=None, description="Node author")
    license: str | None = Field(default=None, description="License information")
    repository: str | None = Field(default=None, description="Source repository")
    documentation_url: str | None = Field(default=None, description="Documentation URL")
    tags: list[str] = Field(default_factory=list, description="Node tags")
    version: ModelSemVer | None = Field(default=None, description="Node version")
    description: str | None = Field(default=None, description="Node description")
    category: str | None = Field(default=None, description="Node category")
    dependencies: list[str] = Field(
        default_factory=list,
        description="Node dependencies",
    )
