"""
Workflow strategy model.
"""

from typing import Any

from pydantic import BaseModel, Field

from .model_matrix_strategy import ModelMatrixStrategy


class ModelWorkflowStrategy(BaseModel):
    """
    Workflow strategy configuration with typed fields.
    Replaces Dict[str, Any] for strategy fields.
    """

    matrix: ModelMatrixStrategy | None = Field(
        None,
        description="Matrix configuration",
    )
    fail_fast: bool = Field(True, description="Fail fast on first error")
    max_parallel: int | None = Field(None, description="Maximum parallel jobs")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        # Use model_dump() as base and apply field name transformations
        base_result = self.model_dump(exclude_none=True)

        # Apply custom field name transformations and conditional logic
        result = {"fail-fast": base_result["fail_fast"]}

        if self.matrix:
            result["matrix"] = self.matrix.model_dump(exclude_none=True)

        if self.max_parallel is not None:
            result["max-parallel"] = base_result["max_parallel"]

        return result
