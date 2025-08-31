#!/usr/bin/env python3
"""
Orchestrator Cache Model - ONEX Standards Compliant.

Cache model for orchestrator calculations providing type-safe caching
structures for performance optimization.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelOrchestratorCacheEntry(BaseModel):
    """
    Single cache entry for orchestrator calculations.

    Contains cached calculation results with TTL and metadata
    for performance optimization in orchestrator operations.
    """

    ticket_id: str = Field(
        description="Unique ticket identifier for this cache entry",
        min_length=1,
    )

    cached_factors: dict[str, float] = Field(
        description="Cached orchestrator factor calculations",
    )

    base_score: float = Field(
        description="Cached base RSD score for this ticket",
        ge=0.0,
        le=100.0,
    )

    orchestrator_adjusted_score: float = Field(
        description="Cached orchestrator-adjusted score",
        ge=0.0,
        le=150.0,
    )

    calculation_timestamp: datetime = Field(
        description="When this cache entry was created",
    )

    context_hash: str = Field(
        description="Hash of the context used for this calculation",
        min_length=1,
    )

    hit_count: int = Field(
        default=1,
        description="Number of times this cache entry has been accessed",
        ge=1,
    )

    last_accessed: datetime = Field(
        default_factory=datetime.now,
        description="Last time this cache entry was accessed",
    )

    class Config:
        """Pydantic model configuration."""

        extra = "forbid"
        validate_assignment = True


class ModelOrchestratorCache(BaseModel):
    """
    Complete orchestrator cache structure.

    Type-safe replacement for Dict cache usage in orchestrator
    priority engine with TTL management and performance tracking.
    """

    entries: dict[str, ModelOrchestratorCacheEntry] = Field(
        default_factory=dict,
        description="Cache entries keyed by ticket ID",
    )

    cache_stats: dict[str, int] = Field(
        default_factory=lambda: {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_requests": 0,
        },
        description="Cache performance statistics",
    )

    max_entries: int = Field(
        default=10000,
        description="Maximum number of cache entries",
        ge=100,
    )

    ttl_seconds: int = Field(
        default=300,
        description="TTL for cache entries in seconds",
        ge=60,  # 5 minutes
    )

    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Cache creation timestamp",
    )

    class Config:
        """Pydantic model configuration."""

        extra = "forbid"
        validate_assignment = True
