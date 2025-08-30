"""
Statistics model for window transitions.

Provides strongly typed statistics structure for transitions.
"""

from pydantic import BaseModel, Field


class ModelTransitionStatistics(BaseModel):
    """Statistics for window transitions."""

    transition_duration_seconds: float = Field(
        default=0.0, description="Time taken for transition"
    )
    agents_migrated: int = Field(default=0, description="Number of agents migrated")
    tasks_interrupted: int = Field(default=0, description="Number of tasks interrupted")
    quota_transferred: int = Field(default=0, description="Amount of quota transferred")
    transition_type: str = Field(
        default="scheduled",
        description="Type of transition (scheduled, manual, emergency)",
    )
    smooth_transition: bool = Field(
        default=True, description="Whether transition was smooth"
    )
    warnings_generated: int = Field(
        default=0, description="Number of warnings during transition"
    )
