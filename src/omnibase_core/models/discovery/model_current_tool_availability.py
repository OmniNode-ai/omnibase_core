"""
Current Tool Availability Model

Model for current availability status of tools within a node.
"""

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_node_current_status import EnumNodeCurrentStatus


class ModelCurrentToolAvailability(BaseModel):
    """Current availability status of tools within the node"""

    tool_name: str = Field(default=..., description="Name of the tool")
    status: EnumNodeCurrentStatus = Field(
        default=..., description="Current tool status"
    )
    last_execution: str | None = Field(
        default=None,
        description="ISO timestamp of last execution",
    )
    execution_count: int | None = Field(
        default=None,
        description="Total number of executions",
        ge=0,
    )
    average_execution_time_ms: float | None = Field(
        default=None,
        description="Average execution time in milliseconds",
        ge=0.0,
    )
