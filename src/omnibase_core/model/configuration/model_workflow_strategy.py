"""
Workflow strategy model.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from .model_matrix_strategy import ModelMatrixStrategy


class ModelWorkflowStrategy(BaseModel):
    """
    Workflow strategy configuration with typed fields.
    Replaces Dict[str, Any] for strategy fields.
    """

    matrix: Optional[ModelMatrixStrategy] = Field(
        None, description="Matrix configuration"
    )
    fail_fast: bool = Field(True, description="Fail fast on first error")
    max_parallel: Optional[int] = Field(None, description="Maximum parallel jobs")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        result = {"fail-fast": self.fail_fast}
        if self.matrix:
            result["matrix"] = self.matrix.dict(exclude_none=True)
        if self.max_parallel is not None:
            result["max-parallel"] = self.max_parallel
        return result
