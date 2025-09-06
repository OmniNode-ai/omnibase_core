"""
Strongly-typed Pydantic models for workflow and reducer patterns.

Replaces Union and Dict[str, Any] patterns in workflow processing
with proper type safety and validation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class WorkflowPriority(str, Enum):
    """Workflow execution priority."""
    
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class ModelWorkflowMetadata(BaseModel):
    """Metadata for workflow execution."""
    
    workflow_id: str = Field(..., description="Unique workflow identifier")
    workflow_type: str = Field(..., description="Type of workflow")
    instance_id: str = Field(..., description="Workflow instance identifier")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")
    parent_workflow_id: Optional[str] = Field(None, description="Parent workflow ID for nested workflows")
    priority: WorkflowPriority = Field(WorkflowPriority.NORMAL, description="Workflow priority")
    retry_count: int = Field(0, description="Number of retry attempts")
    max_retries: int = Field(3, description="Maximum retry attempts")
    timeout_seconds: Optional[int] = Field(None, description="Workflow timeout in seconds")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Execution start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    tags: list[str] = Field(default_factory=list, description="Workflow tags")
    labels: dict[str, str] = Field(default_factory=dict, description="Workflow labels")


class ModelWorkflowInput(BaseModel):
    """Strongly-typed input for workflow execution."""
    
    metadata: ModelWorkflowMetadata = Field(..., description="Workflow metadata")
    payload: dict[str, Any] = Field(..., description="Workflow input payload")
    context: dict[str, Any] = Field(default_factory=dict, description="Execution context")
    configuration: dict[str, Any] = Field(default_factory=dict, description="Workflow configuration")
    
    @field_validator('payload')
    @classmethod
    def validate_payload(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate workflow payload is not empty."""
        if not v:
            raise ValueError("Workflow payload cannot be empty")
        return v


class ModelWorkflowOutput(BaseModel):
    """Strongly-typed output from workflow execution."""
    
    metadata: ModelWorkflowMetadata = Field(..., description="Workflow metadata")
    status: WorkflowStatus = Field(..., description="Execution status")
    result: Optional[dict[str, Any]] = Field(None, description="Workflow result data")
    error: Optional[str] = Field(None, description="Error message if failed")
    error_details: Optional[dict[str, Any]] = Field(None, description="Detailed error information")
    execution_time_ms: float = Field(0, description="Execution time in milliseconds")
    metrics: dict[str, float] = Field(default_factory=dict, description="Execution metrics")
    artifacts: list[str] = Field(default_factory=list, description="Generated artifact references")
    
    def is_successful(self) -> bool:
        """Check if workflow execution was successful."""
        return self.status == WorkflowStatus.COMPLETED
    
    def is_retriable(self) -> bool:
        """Check if workflow can be retried."""
        return (
            self.status == WorkflowStatus.FAILED and
            self.metadata.retry_count < self.metadata.max_retries
        )


class ModelReducerInput(BaseModel):
    """Strongly-typed input for reducer operations."""
    
    reducer_id: str = Field(..., description="Reducer identifier")
    input_data: dict[str, Any] = Field(..., description="Input data for reduction")
    reduction_strategy: str = Field("default", description="Reduction strategy to use")
    options: dict[str, Any] = Field(default_factory=dict, description="Reducer options")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ModelReducerOutput(BaseModel):
    """Strongly-typed output from reducer operations."""
    
    reducer_id: str = Field(..., description="Reducer identifier")
    reduced_data: dict[str, Any] = Field(..., description="Reduced output data")
    reduction_strategy: str = Field(..., description="Strategy used for reduction")
    statistics: dict[str, float] = Field(default_factory=dict, description="Reduction statistics")
    execution_time_ms: float = Field(0, description="Execution time in milliseconds")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ModelWorkflowStep(BaseModel):
    """Model for individual workflow step."""
    
    step_id: str = Field(..., description="Unique step identifier")
    step_name: str = Field(..., description="Step name")
    step_type: str = Field(..., description="Type of step (compute, effect, reduce, orchestrate)")
    input_data: dict[str, Any] = Field(..., description="Step input data")
    output_data: Optional[dict[str, Any]] = Field(None, description="Step output data")
    status: WorkflowStatus = Field(WorkflowStatus.PENDING, description="Step execution status")
    started_at: Optional[datetime] = Field(None, description="Step start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Step completion timestamp")
    execution_time_ms: float = Field(0, description="Step execution time")
    error: Optional[str] = Field(None, description="Error message if step failed")
    retry_count: int = Field(0, description="Number of retries for this step")
    dependencies: list[str] = Field(default_factory=list, description="Step dependencies")
    
    def is_ready(self, completed_steps: set[str]) -> bool:
        """Check if step is ready to execute based on dependencies."""
        return all(dep in completed_steps for dep in self.dependencies)


class ModelWorkflowPlan(BaseModel):
    """Model for workflow execution plan."""
    
    plan_id: str = Field(..., description="Unique plan identifier")
    workflow_metadata: ModelWorkflowMetadata = Field(..., description="Workflow metadata")
    steps: list[ModelWorkflowStep] = Field(..., description="Workflow steps")
    execution_order: list[str] = Field(default_factory=list, description="Step execution order")
    parallel_groups: list[list[str]] = Field(default_factory=list, description="Groups of parallel steps")
    estimated_duration_ms: float = Field(0, description="Estimated total duration")
    resource_requirements: dict[str, Any] = Field(default_factory=dict, description="Resource requirements")
    
    def validate_dependencies(self) -> bool:
        """Validate that all step dependencies are valid."""
        step_ids = {step.step_id for step in self.steps}
        for step in self.steps:
            for dep in step.dependencies:
                if dep not in step_ids:
                    return False
        return True