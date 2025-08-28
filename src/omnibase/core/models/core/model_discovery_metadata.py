from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ModelDiscoveryMetadata(BaseModel):
    """Additional metadata for node discovery operations."""

    discovery_duration_ms: Optional[int] = Field(
        None, description="Time taken for discovery operation", ge=0
    )
    discovery_errors: List[str] = Field(
        default_factory=list, description="Any errors encountered during discovery"
    )
    cached_results: bool = Field(
        default=False, description="Whether results were served from cache"
    )
    filter_criteria: Dict[str, str] = Field(
        default_factory=dict, description="Criteria used to filter discovery results"
    )
    discovery_scope: Optional[str] = Field(
        None, description="Scope of discovery (local, cluster, global)"
    )
    last_refresh: Optional[datetime] = Field(
        None, description="When discovery data was last refreshed"
    )
    next_refresh: Optional[datetime] = Field(
        None, description="When discovery data should be refreshed next"
    )
    discovery_version: str = Field(
        default="1.0.0", description="Version of discovery protocol used"
    )
