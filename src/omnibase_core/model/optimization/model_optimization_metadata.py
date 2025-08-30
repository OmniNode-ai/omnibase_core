"""
Model for optimization metadata.

Metadata for optimization result.
"""

from pydantic import BaseModel, Field


class ModelOptimizationMetadata(BaseModel):
    """Metadata for optimization result."""

    algorithm_used: str = Field(
        "dynamic_programming", description="Optimization algorithm"
    )
    duration_ms: int = Field(0, description="Optimization duration in milliseconds")
    iterations: int = Field(0, description="Number of iterations")
    convergence_achieved: bool = Field(
        False, description="Whether convergence was achieved"
    )
