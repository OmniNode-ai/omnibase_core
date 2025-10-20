from __future__ import annotations

from pydantic import BaseModel, Field


class ModelConditionalWorkflowContext(BaseModel):
    """Structured context for conditional workflow evaluation."""

    variable_scope: str = Field(
        default="local",
        description="Variable scope for condition",
    )
    evaluation_mode: str = Field(
        default="strict",
        description="Condition evaluation mode",
    )
    context_variables: dict[str, str] = Field(
        default_factory=dict,
        description="Context variables for evaluation",
    )
    external_dependencies: list[str] = Field(
        default_factory=list,
        description="External dependencies for condition",
    )
    cache_results: bool = Field(
        default=True,
        description="Whether to cache evaluation results",
    )
