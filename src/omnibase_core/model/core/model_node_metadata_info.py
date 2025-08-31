"""
NodeMetadataInfo model for node introspection.
"""

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_performance_profile_info import (
    ModelPerformanceProfileInfo,
)
from omnibase_core.model.core.model_version_status import ModelVersionStatus


class ModelNodeMetadataInfo(BaseModel):
    """Model for node metadata."""

    name: str = Field(..., description="Node name")
    version: str = Field(..., description="Node version")
    description: str = Field(..., description="Node description")
    author: str = Field(..., description="Node author")
    schema_version: str = Field(..., description="Node schema version")
    created_at: str | None = Field(None, description="Node creation timestamp")
    last_modified_at: str | None = Field(
        None,
        description="Last modification timestamp",
    )

    # Enhanced version information
    available_versions: list[str] | None = Field(
        None,
        description="All available versions of this node",
    )
    latest_version: str | None = Field(None, description="Latest available version")
    total_versions: int | None = Field(
        None,
        description="Total number of versions available",
    )
    version_status: ModelVersionStatus | None = Field(
        None,
        description="Status of each version (latest, supported, deprecated)",
    )

    # Ecosystem information
    category: str | None = Field(
        None,
        description="Node category (e.g., validation, generation, transformation)",
    )
    tags: list[str] | None = Field(
        None,
        description="Node tags for categorization and discovery",
    )
    maturity: str | None = Field(
        None,
        description="Node maturity level (experimental, beta, stable, deprecated)",
    )
    use_cases: list[str] | None = Field(
        None,
        description="Primary use cases for this node",
    )
    performance_profile: ModelPerformanceProfileInfo | None = Field(
        None,
        description="Performance characteristics and resource usage",
    )
