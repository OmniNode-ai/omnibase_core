"""
Strongly-typed computation metadata context model.

Represents metadata context for computation operations.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ModelComputationMetadataContext(BaseModel):
    """
    Strongly-typed computation metadata context.

    Provides structured metadata for computation operations including
    execution tracking, performance hints, and quality requirements.
    """

    execution_id: UUID = Field(
        default_factory=uuid4,
        description="Unique execution identifier",
    )
    computation_session: str = Field(
        default="",
        description="Computation session identifier",
    )
    performance_hints: dict[str, str] = Field(
        default_factory=dict,
        description="Performance optimization hints",
    )
    quality_requirements: dict[str, str] = Field(
        default_factory=dict,
        description="Quality and precision requirements",
    )
    resource_constraints: dict[str, str] = Field(
        default_factory=dict,
        description="Resource constraint specifications",
    )
    debug_mode: bool = Field(
        default=False,
        description="Whether debug mode is enabled",
    )
    trace_enabled: bool = Field(
        default=False,
        description="Whether execution tracing is enabled",
    )

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=False,
        validate_assignment=True,
    )


# Export for use
__all__ = ["ModelComputationMetadataContext"]
