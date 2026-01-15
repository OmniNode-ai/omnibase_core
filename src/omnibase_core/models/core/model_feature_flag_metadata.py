"""
Feature Flag Metadata Model.

Metadata for a feature flag including description, ownership, and rollout percentage.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ModelFeatureFlagMetadata(BaseModel):
    """Metadata for a feature flag."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    description: str = Field(default="", description="Description of the feature flag")
    created_at: datetime | None = Field(
        default=None, description="When the flag was created"
    )
    updated_at: datetime | None = Field(
        default=None, description="When the flag was last updated"
    )
    owner: str | None = Field(default=None, description="Owner of the feature flag")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    rollout_percentage: int = Field(
        default=100,
        ge=0,
        le=100,
        description="Percentage rollout (0-100)",
    )
