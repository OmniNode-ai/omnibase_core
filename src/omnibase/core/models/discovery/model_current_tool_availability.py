"""
Current Tool Availability Model

Model for current availability status of tools within a node.
"""

from typing import Optional

from pydantic import BaseModel, Field

from .enum_node_current_status import NodeCurrentStatusEnum


class ModelCurrentToolAvailability(BaseModel):
    """Current availability status of tools within the node"""

    tool_name: str = Field(..., description="Name of the tool")
    status: NodeCurrentStatusEnum = Field(..., description="Current tool status")
    last_execution: Optional[str] = Field(
        None, description="ISO timestamp of last execution"
    )
    execution_count: Optional[int] = Field(
        None, description="Total number of executions", ge=0
    )
    average_execution_time_ms: Optional[float] = Field(
        None, description="Average execution time in milliseconds", ge=0.0
    )
