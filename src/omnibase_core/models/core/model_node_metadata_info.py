from pydantic import Field

"""
NodeMetadataInfo model for node introspection.
"""

from pydantic import BaseModel

from omnibase_core.models.core.model_performance_profile_info import (
    ModelPerformanceProfileInfo,
)
from omnibase_core.models.core.model_version_status import ModelVersionStatus
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelNodeMetadataInfo(BaseModel):
    """Model for node metadata."""

    name: str = Field(default=..., description="Node name")
    version: ModelSemVer = Field(default=..., description="Node version")
    description: str = Field(default=..., description="Node description")
    author: str = Field(default=..., description="Node author")
    schema_version: ModelSemVer = Field(default=..., description="Node schema version")
    created_at: str | None = Field(default=None, description="Node creation timestamp")
    last_modified_at: str | None = Field(
        default=None,
        description="Last modification timestamp",
    )

    # Enhanced version information
    available_versions: list[ModelSemVer] | None = Field(
        default=None,
        description="All available versions of this node",
    )
    latest_version: ModelSemVer | None = Field(
        default=None, description="Latest available version"
    )
    total_versions: int | None = Field(
        default=None,
        description="Total number of versions available",
    )
    version_status: ModelVersionStatus | None = Field(
        default=None,
        description="Status of each version (latest, supported, deprecated)",
    )

    # Ecosystem information
    category: str | None = Field(
        default=None,
        description="Node category (e.g., validation, generation, transformation)",
    )
    tags: list[str] | None = Field(
        default=None,
        description="Node tags for categorization and discovery",
    )
    maturity: str | None = Field(
        default=None,
        description="Node maturity level (experimental, beta, stable, deprecated)",
    )
    use_cases: list[str] | None = Field(
        default=None,
        description="Primary use cases for this node",
    )
    performance_profile: ModelPerformanceProfileInfo | None = Field(
        default=None,
        description="Performance characteristics and resource usage",
    )
