"""
Service Cache Statistics Model.

Provides strongly typed models for service cache statistics and monitoring,
replacing Dict[str, Any] patterns with proper Pydantic models.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ModelServiceCacheEntry(BaseModel):
    """Individual cache entry information."""

    service_name: str = Field(..., description="Name of the cached service")
    protocol_type: str = Field(..., description="Protocol type of the service")
    cached_at: datetime = Field(..., description="When the service was cached")
    last_accessed: datetime = Field(..., description="Last access time")
    hit_count: int = Field(default=0, description="Number of cache hits", ge=0)
    is_fallback: bool = Field(
        default=False, description="Whether this is a fallback implementation"
    )


class ModelServiceCacheStats(BaseModel):
    """
    Service cache statistics model.
    
    Replaces: Dict[str, Any] in ProtocolServiceResolver.get_cache_stats()
    """

    total_services: int = Field(..., description="Total cached services", ge=0)
    primary_services: int = Field(..., description="Primary implementations", ge=0)
    fallback_services: int = Field(..., description="Fallback implementations", ge=0)
    cache_entries: list[ModelServiceCacheEntry] = Field(
        default_factory=list, description="Individual cache entries"
    )
    cache_hit_rate: float = Field(
        default=0.0, description="Cache hit rate percentage", ge=0.0, le=100.0
    )
    total_hits: int = Field(default=0, description="Total cache hits", ge=0)
    total_misses: int = Field(default=0, description="Total cache misses", ge=0)
    last_reset: Optional[datetime] = Field(
        None, description="Last cache reset timestamp"
    )