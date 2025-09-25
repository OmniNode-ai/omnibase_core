#!/usr/bin/env python3
"""
Parallel Configuration Model - ONEX Standards Compliant.

Parallel processing configuration defining thread pools, async settings,
and concurrency parameters for performance optimization.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel, Field


class ModelParallelConfig(BaseModel):
    """
    Parallel processing configuration.

    Defines thread pools, async settings, and concurrency
    parameters for performance optimization.
    """

    enabled: bool = Field(default=True, description="Enable parallel processing")

    max_workers: int = Field(
        default=4,
        description="Maximum number of worker threads",
        ge=1,
        le=32,
    )

    batch_size: int = Field(
        default=100,
        description="Batch size for parallel operations",
        ge=1,
    )

    async_enabled: bool = Field(
        default=False,
        description="Enable asynchronous processing",
    )

    thread_pool_type: str = Field(
        default="ThreadPoolExecutor",
        description="Thread pool implementation type",
    )

    queue_size: int = Field(
        default=1000,
        description="Maximum queue size for pending operations",
        ge=1,
    )
