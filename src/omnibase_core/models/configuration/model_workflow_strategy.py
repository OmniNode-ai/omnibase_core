"""
Workflow strategy model.
"""

from pydantic import BaseModel, Field

from .model_matrix_strategy import ModelMatrixStrategy


class ModelWorkflowStrategy(BaseModel):
    """
    Workflow strategy configuration with typed fields.
    Replaces Dict[str, Any] for strategy fields.
    """

    matrix: ModelMatrixStrategy | None = Field(
        default=None,
        description="Matrix configuration",
    )
    fail_fast: bool = Field(default=True, description="Fail fast on first error")
    max_parallel: int | None = Field(default=None, description="Maximum parallel jobs")


# ONEX compliance remediation complete - factory method eliminated
# Direct Pydantic model_dump() provides standardized serialization:
# strategy_dict = strategy.model_dump(exclude_none=True, by_alias=True)
