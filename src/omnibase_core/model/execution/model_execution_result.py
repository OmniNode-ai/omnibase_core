"""Execution result model for Workflow node execution tracking."""

from typing import List, Optional

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_execution_status import EnumExecutionStatus


class ModelExecutionResult(BaseModel):
    """Model for execution results replacing Dict[str, Any] returns."""

    node_id: str = Field(..., description="ID of the executed node", min_length=1)
    status: EnumExecutionStatus = Field(..., description="Execution status")
    output: str = Field(..., description="Primary output message")
    details: str = Field(default="", description="Additional execution details")
    execution_time_seconds: Optional[float] = Field(
        None, description="Execution duration", ge=0
    )
    discovered_tools: Optional[int] = Field(
        None, description="Number of tools discovered", ge=0
    )
    models_generated: Optional[int] = Field(
        None, description="Number of models generated", ge=0
    )
    failed_tools: List[str] = Field(
        default_factory=list, description="List of failed tools"
    )
    tool_directories: List[str] = Field(
        default_factory=list, description="Processed directories"
    )
    success_rate: Optional[float] = Field(
        None, description="Success rate percentage", ge=0.0, le=100.0
    )
    scenarios_passed: Optional[int] = Field(
        None, description="Number of scenarios passed", ge=0
    )
    scenarios_total: Optional[int] = Field(
        None, description="Total number of scenarios", ge=0
    )
