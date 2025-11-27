from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelDiscoveryMetadata(BaseModel):
    """Additional metadata for node discovery operations."""

    discovery_duration_ms: int | None = Field(
        default=None,
        description="Time taken for discovery operation",
        ge=0,
    )
    discovery_errors: list[str] = Field(
        default_factory=list,
        description="Any errors encountered during discovery",
    )
    cached_results: bool = Field(
        default=False,
        description="Whether results were served from cache",
    )
    filter_criteria: dict[str, str] = Field(
        default_factory=dict,
        description="Criteria used to filter discovery results",
    )
    discovery_scope: str | None = Field(
        default=None,
        description="Scope of discovery (local, cluster, global)",
    )
    last_refresh: datetime | None = Field(
        default=None,
        description="When discovery data was last refreshed",
    )
    next_refresh: datetime | None = Field(
        default=None,
        description="When discovery data should be refreshed next",
    )
    discovery_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Version of discovery protocol used",
    )
