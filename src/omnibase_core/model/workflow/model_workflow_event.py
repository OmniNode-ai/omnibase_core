"""Workflow event model with proper typing and validation."""

from typing import List

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_workflow_condition import EnumWorkflowCondition


class ModelWorkflowEvent(BaseModel):
    """Workflow event definition with proper typing and validation."""

    trigger: str = Field(..., description="Event trigger identifier", min_length=1)
    target: str = Field(..., description="Target node to execute", min_length=1)
    condition: EnumWorkflowCondition = Field(
        default=EnumWorkflowCondition.SUCCESS, description="Execution condition"
    )
    retry_count: int = Field(
        default=0, description="Number of retries allowed", ge=0, le=10
    )
    timeout_seconds: int = Field(
        default=300, description="Execution timeout", gt=0, le=3600
    )
    dependencies: List[str] = Field(
        default_factory=list, description="Node dependencies"
    )
