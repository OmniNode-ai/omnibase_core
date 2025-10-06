from __future__ import annotations

from pydantic import BaseModel, Field


class ModelWorkflowInputParameters(BaseModel):
    """Structured workflow input parameters."""

    execution_mode: str = Field(
        default="synchronous",
        description="Workflow execution mode",
    )
    retry_policy: str = Field(default="default", description="Retry policy name")
    timeout_seconds: int = Field(default=300, description="Workflow timeout in seconds")
    priority: str = Field(default="normal", description="Execution priority")
    debug_mode: bool = Field(default=False, description="Whether debug mode is enabled")
    validation_level: str = Field(
        default="strict",
        description="Input validation level",
    )
    custom_parameters: dict[str, str] = Field(
        default_factory=dict,
        description="Additional custom parameters",
    )
