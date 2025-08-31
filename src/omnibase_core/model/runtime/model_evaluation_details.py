"""Evaluation details model for conditional execution."""

from pydantic import BaseModel, Field


class ModelEvaluationDetails(BaseModel):
    """Details of condition evaluation."""

    condition_text: str | None = Field(
        default=None,
        description="Original condition text",
    )
    evaluation_result: bool = Field(..., description="Result of evaluation")
    source_value: str | int | float | bool | None = Field(
        default=None,
        description="Source value used in evaluation",
    )
    target_value: str | int | float | bool | None = Field(
        default=None,
        description="Target value for comparison",
    )
    operator_used: str | None = Field(
        default=None,
        description="Operator used in evaluation",
    )
    evaluation_steps: list[str] | None = Field(
        default=None,
        description="Step-by-step evaluation process",
    )
