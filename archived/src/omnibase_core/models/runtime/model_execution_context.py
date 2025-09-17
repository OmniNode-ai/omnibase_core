"""Execution context model."""

from pydantic import BaseModel, Field


class ModelExecutionContext(BaseModel):
    """Execution context for control flow operations."""

    execution_id: str = Field(..., description="Unique execution identifier")
    scenario_name: str | None = Field(default=None, description="Scenario name")
    current_node: str | None = Field(
        default=None,
        description="Current executing node",
    )
    start_time: str | None = Field(default=None, description="Execution start time")
    variables: str | int | float | bool | list[str] | None = Field(
        default=None,
        description="Context variables",
    )
    trace_id: str | None = Field(default=None, description="Distributed trace ID")
