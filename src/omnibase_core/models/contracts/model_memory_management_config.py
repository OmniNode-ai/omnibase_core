"""
Memory Management Configuration Model.

Memory management configuration for batch processing in NodeReducer implementations.
Defines memory allocation, garbage collection, and resource management for
efficient batch processing operations.

Part of the "one model per file" convention for clean architecture.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelMemoryManagementConfig(BaseModel):
    """
    Memory management for batch processing.

    Defines memory allocation, garbage collection,
    and resource management for efficient batch processing.
    """

    max_memory_mb: int = Field(
        default=1024,
        description="Maximum memory allocation in MB",
        ge=1,
    )

    gc_threshold: float = Field(
        default=0.8,
        description="Garbage collection trigger threshold (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    lazy_loading_enabled: bool = Field(
        default=True,
        description="Enable lazy loading for large datasets",
    )

    spill_to_disk_enabled: bool = Field(
        default=True,
        description="Enable spilling to disk when memory is full",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
