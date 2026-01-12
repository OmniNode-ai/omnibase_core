"""
Strongly-typed computation operation parameters model.

Represents structured parameters for computation operations.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelComputationOperationParameters(BaseModel):
    """
    Strongly-typed computation operation parameters.

    Provides structured parameters for configuring computation operations
    including algorithm selection, optimization, and error handling.
    """

    algorithm_name: str = Field(
        default="",
        description="Algorithm identifier",
    )
    optimization_level: str = Field(
        default="standard",
        description="Optimization level",
    )
    parallel_execution: bool = Field(
        default=False,
        description="Enable parallel execution",
    )
    validation_mode: str = Field(
        default="strict",
        description="Input validation mode",
    )
    error_handling: str = Field(
        default="fail_fast",
        description="Error handling strategy",
    )
    custom_parameters: dict[str, str] = Field(
        default_factory=dict,
        description="Additional custom parameters",
    )

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=False,
        validate_assignment=True,
    )


# Export for use
__all__ = ["ModelComputationOperationParameters"]
