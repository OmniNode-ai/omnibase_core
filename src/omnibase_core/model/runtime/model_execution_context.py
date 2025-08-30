"""Execution context model."""

from typing import List, Optional, Union

from pydantic import BaseModel, Field


class ModelExecutionContext(BaseModel):
    """Execution context for control flow operations."""

    execution_id: str = Field(..., description="Unique execution identifier")
    scenario_name: Optional[str] = Field(default=None, description="Scenario name")
    current_node: Optional[str] = Field(
        default=None, description="Current executing node"
    )
    start_time: Optional[str] = Field(default=None, description="Execution start time")
    variables: Optional[Union[str, int, float, bool, List[str]]] = Field(
        default=None, description="Context variables"
    )
    trace_id: Optional[str] = Field(default=None, description="Distributed trace ID")
