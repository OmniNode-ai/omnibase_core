"""Evaluation details model for conditional execution."""

from typing import List, Optional, Union

from pydantic import BaseModel, Field


class ModelEvaluationDetails(BaseModel):
    """Details of condition evaluation."""

    condition_text: Optional[str] = Field(
        default=None, description="Original condition text"
    )
    evaluation_result: bool = Field(..., description="Result of evaluation")
    source_value: Optional[Union[str, int, float, bool]] = Field(
        default=None, description="Source value used in evaluation"
    )
    target_value: Optional[Union[str, int, float, bool]] = Field(
        default=None, description="Target value for comparison"
    )
    operator_used: Optional[str] = Field(
        default=None, description="Operator used in evaluation"
    )
    evaluation_steps: Optional[List[str]] = Field(
        default=None, description="Step-by-step evaluation process"
    )
