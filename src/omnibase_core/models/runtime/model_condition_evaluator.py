# Model for condition evaluator
# DO NOT EDIT MANUALLY - regenerate using model generation tools


from pydantic import BaseModel, Field


class ModelConditionEvaluator(BaseModel):
    """Model for condition evaluator interface."""

    evaluator_id: str = Field(..., description="Unique evaluator identifier")
    version: str = Field(default="1.0.0", description="Evaluator version")
    is_active: bool = Field(default=True, description="Whether evaluator is active")
