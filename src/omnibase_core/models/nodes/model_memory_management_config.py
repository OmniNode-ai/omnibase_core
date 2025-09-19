"""
Memory management configuration model for REDUCER nodes.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.nodes import EnumMemoryCleanupStrategy


class ModelMemoryManagementConfig(BaseModel):
    """Memory management configuration for REDUCER nodes."""

    model_config = ConfigDict(extra="forbid")

    max_memory_mb: int = Field(
        default=512,
        description="Maximum memory usage in megabytes",
        ge=1,
    )
    gc_threshold: float = Field(
        default=0.8,
        description="Garbage collection threshold (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )
    cleanup_strategy: EnumMemoryCleanupStrategy = Field(
        default=EnumMemoryCleanupStrategy.LRU,
        description="Memory cleanup strategy",
    )
