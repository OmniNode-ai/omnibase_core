"""Execution result model for Workflow node execution tracking."""

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_execution_status import EnumExecutionStatus


class ModelExecutionResult(BaseModel):
    """Model for execution results replacing Dict[str, Any] returns."""

    node_id: str = Field(..., description="ID of the executed node", min_length=1)
    status: EnumExecutionStatus = Field(..., description="Execution status")
    output: str = Field(..., description="Primary output message")
    details: str = Field(default="", description="Additional execution details")
    execution_time_seconds: float | None = Field(
        None,
        description="Execution duration",
        ge=0,
    )
    discovered_tools: int | None = Field(
        None,
        description="Number of tools discovered",
        ge=0,
    )
    models_generated: int | None = Field(
        None,
        description="Number of models generated",
        ge=0,
    )
    failed_tools: list[str] = Field(
        default_factory=list,
        description="List of failed tools",
    )
    tool_directories: list[str] = Field(
        default_factory=list,
        description="Processed directories",
    )
    success_rate: float | None = Field(
        None,
        description="Success rate percentage",
        ge=0.0,
        le=100.0,
    )
    scenarios_passed: int | None = Field(
        None,
        description="Number of scenarios passed",
        ge=0,
    )
    scenarios_total: int | None = Field(
        None,
        description="Total number of scenarios",
        ge=0,
    )
