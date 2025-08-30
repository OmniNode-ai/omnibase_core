"""
AI Workflow State Models

Strongly-typed models for workflow orchestration with proper ONEX compliance.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class EnumWorkflowStatus(Enum):
    """Workflow execution status."""

    PENDING = "pending"
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EnumWorkflowType(Enum):
    """Supported workflow types."""

    DOCUMENT_REGENERATION = "document_regeneration"
    CODE_ANALYSIS = "code_analysis"
    MULTI_MODAL = "multi_modal"
    PR_CREATION = "pr_creation"


class EnumEventType(Enum):
    """Event types for workflow orchestration."""

    AI_WORKFLOW_REQUEST = "AI_WORKFLOW_REQUEST"
    LLM_INFERENCE_REQUEST = "LLM_INFERENCE_REQUEST"
    LLM_INFERENCE_COMPLETE = "LLM_INFERENCE_COMPLETE"
    WORKFLOW_STEP_COMPLETE = "WORKFLOW_STEP_COMPLETE"
    WORKFLOW_COMPLETE = "WORKFLOW_COMPLETE"
    NODE_ANNOUNCE = "NODE_ANNOUNCE"
    PR_CREATED = "PR_CREATED"


class ModelWorkflowStepData(BaseModel):
    """Data for completed workflow steps."""

    step_id: str = Field(description="Unique step identifier")
    status: str = Field(description="Step completion status")
    timestamp: Optional[float] = Field(
        default=None, description="Step completion timestamp"
    )
    output: Optional[str] = Field(default=None, description="Step output data")


class ModelWorkflowRequestData(BaseModel):
    """Data structure for workflow requests."""

    workflow_id: Optional[str] = Field(
        default=None, description="Unique workflow identifier"
    )
    workflow_type: EnumWorkflowType = Field(description="Type of workflow to execute")
    document: Optional[str] = Field(
        default=None, description="Document path for processing"
    )
    context: Optional[str] = Field(
        default=None, description="Additional context information"
    )
    file_path: Optional[str] = Field(
        default=None, description="File path for PR workflows"
    )
    improvement_context: Optional[str] = Field(
        default=None, description="Improvement context for PR workflows"
    )
    branch_name: Optional[str] = Field(
        default=None, description="Branch name for PR workflows"
    )
    code: Optional[str] = Field(
        default=None, description="Code content for analysis workflows"
    )


class ModelWorkflowState(BaseModel):
    """Complete workflow state tracking."""

    workflow_id: str = Field(description="Unique workflow identifier")
    workflow_type: EnumWorkflowType = Field(description="Type of workflow")
    status: EnumWorkflowStatus = Field(description="Current workflow status")
    steps_completed: List[ModelWorkflowStepData] = Field(
        default_factory=list, description="List of completed workflow steps"
    )
    request_data: ModelWorkflowRequestData = Field(description="Original request data")
    created_at: Optional[float] = Field(
        default=None, description="Workflow creation timestamp"
    )
    updated_at: Optional[float] = Field(
        default=None, description="Last update timestamp"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if failed"
    )


class ModelEventData(BaseModel):
    """Base event data structure."""

    event_type: EnumEventType = Field(description="Type of event")
    node_id: str = Field(description="Node that generated the event")
    timestamp: Optional[float] = Field(default=None, description="Event timestamp")


class ModelLLMInferenceRequestData(BaseModel):
    """Data for LLM inference requests."""

    request_id: str = Field(description="Unique request identifier")
    workflow_id: str = Field(description="Associated workflow ID")
    step_id: str = Field(description="Workflow step ID")
    prompt: str = Field(description="Prompt for LLM inference")
    model: Optional[str] = Field(default=None, description="Preferred model name")
    provider: Optional[str] = Field(default=None, description="Preferred provider")
    max_tokens: Optional[int] = Field(
        default=None, description="Maximum tokens to generate", gt=0
    )
    temperature: Optional[float] = Field(
        default=None, description="Temperature for generation", ge=0.0, le=2.0
    )


class ModelLLMInferenceResponseData(BaseModel):
    """Data for LLM inference responses."""

    request_id: str = Field(description="Request identifier")
    response: str = Field(description="Generated response text")
    model: str = Field(description="Model used for generation")
    provider: str = Field(description="Provider used for generation")
    duration: float = Field(description="Generation duration in seconds", ge=0.0)
    tokens_generated: Optional[int] = Field(
        default=None, description="Number of tokens generated", ge=0
    )
    success: bool = Field(description="Whether generation was successful")
    error_message: Optional[str] = Field(
        default=None, description="Error message if failed"
    )


class ModelPRCreatedData(BaseModel):
    """Data for PR creation events."""

    workflow_id: str = Field(description="Associated workflow ID")
    pr_url: str = Field(description="URL of created pull request")
    file_path: str = Field(description="Path of modified file")
    branch: str = Field(description="Branch name for PR")
    pr_number: Optional[int] = Field(
        default=None, description="PR number if available", gt=0
    )


class ModelNodeCapabilities(BaseModel):
    """Node capability announcement data."""

    node_id: str = Field(description="Node identifier")
    capabilities: List[str] = Field(description="List of supported capabilities")
    status: str = Field(description="Node status (ready, busy, error)")
    version: Optional[str] = Field(default=None, description="Node version")
    load: Optional[float] = Field(
        default=None, description="Current node load (0.0-1.0)", ge=0.0, le=1.0
    )
