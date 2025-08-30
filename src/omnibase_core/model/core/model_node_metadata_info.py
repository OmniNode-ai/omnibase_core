"""
NodeMetadataInfo model for node introspection.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_performance_profile_info import \
    ModelPerformanceProfileInfo
from omnibase_core.model.core.model_version_status import ModelVersionStatus


class ModelNodeMetadataInfo(BaseModel):
    """Model for node metadata."""

    name: str = Field(..., description="Node name")
    version: str = Field(..., description="Node version")
    description: str = Field(..., description="Node description")
    author: str = Field(..., description="Node author")
    schema_version: str = Field(..., description="Node schema version")
    created_at: Optional[str] = Field(None, description="Node creation timestamp")
    last_modified_at: Optional[str] = Field(
        None, description="Last modification timestamp"
    )

    # Enhanced version information
    available_versions: Optional[List[str]] = Field(
        None, description="All available versions of this node"
    )
    latest_version: Optional[str] = Field(None, description="Latest available version")
    total_versions: Optional[int] = Field(
        None, description="Total number of versions available"
    )
    version_status: Optional[ModelVersionStatus] = Field(
        None, description="Status of each version (latest, supported, deprecated)"
    )

    # Ecosystem information
    category: Optional[str] = Field(
        None, description="Node category (e.g., validation, generation, transformation)"
    )
    tags: Optional[List[str]] = Field(
        None, description="Node tags for categorization and discovery"
    )
    maturity: Optional[str] = Field(
        None, description="Node maturity level (experimental, beta, stable, deprecated)"
    )
    use_cases: Optional[List[str]] = Field(
        None, description="Primary use cases for this node"
    )
    performance_profile: Optional[ModelPerformanceProfileInfo] = Field(
        None, description="Performance characteristics and resource usage"
    )
