from __future__ import annotations

from pydantic import BaseModel, Field


class ModelLoopWorkflowContext(BaseModel):
    """Structured context for loop workflow iterations."""

    iteration_counter: int = Field(default=0, description="Current iteration counter")
    loop_variable: str = Field(default="", description="Primary loop variable name")
    accumulator_variables: dict[str, str] = Field(
        default_factory=dict,
        description="Variables accumulated across iterations",
    )
    break_conditions: list[str] = Field(
        default_factory=list,
        description="Additional break conditions",
    )
    performance_tracking: bool = Field(
        default=True,
        description="Track performance metrics per iteration",
    )
