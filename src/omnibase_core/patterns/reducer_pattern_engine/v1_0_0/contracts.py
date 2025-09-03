"""
Data contracts and interfaces for Reducer Pattern Engine v1.0.0.

Defines the core data models and interfaces for workflow routing,
processing, and subreducer interactions in Phase 1 implementation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class WorkflowType(Enum):
    """Supported workflow types for Phase 2 multi-workflow support."""

    DOCUMENT_REGENERATION = "document_regeneration"
    DATA_ANALYSIS = "data_analysis"
    REPORT_GENERATION = "report_generation"


class WorkflowStatus(Enum):
    """Workflow execution status."""

    PENDING = "pending"
    ROUTING = "routing"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowRequest(BaseModel):
    """
    Request model for workflow processing.

    Contains all necessary information for routing and processing
    a workflow through the Reducer Pattern Engine.
    """

    workflow_id: UUID = Field(default_factory=uuid4)
    workflow_type: WorkflowType
    instance_id: str = Field(
        ..., description="Unique instance identifier for isolation"
    )
    correlation_id: UUID = Field(default_factory=uuid4)
    payload: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str,
        }


class WorkflowResponse(BaseModel):
    """
    Response model for completed workflow processing.

    Contains processing results, status information, and metrics
    for observability and debugging.
    """

    workflow_id: UUID
    workflow_type: WorkflowType
    instance_id: str
    correlation_id: UUID
    status: WorkflowStatus
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    processing_time_ms: Optional[float] = None
    subreducer_name: Optional[str] = None
    completed_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str,
        }


class RoutingDecision(BaseModel):
    """
    Routing decision for workflow processing.

    Contains the routing logic result including subreducer selection
    and routing metadata for observability.
    """

    workflow_id: UUID
    workflow_type: WorkflowType
    instance_id: str
    subreducer_name: str
    routing_hash: str
    routing_metadata: Dict[str, Any] = Field(default_factory=dict)
    routed_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str,
        }


class SubreducerResult(BaseModel):
    """
    Result from subreducer processing.

    Contains the processing outcome from a specific subreducer
    including success/failure status and detailed results.
    """

    workflow_id: UUID
    subreducer_name: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    processing_time_ms: float
    processed_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str,
        }


class WorkflowMetrics(BaseModel):
    """
    Metrics for workflow processing performance.

    Tracks performance metrics for monitoring and optimization
    of the Reducer Pattern Engine.
    """

    total_workflows_processed: int = 0
    successful_workflows: int = 0
    failed_workflows: int = 0
    average_processing_time_ms: float = 0.0
    average_routing_time_ms: float = 0.0
    active_instances: int = 0
    subreducer_metrics: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    def calculate_success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_workflows_processed == 0:
            return 0.0
        return (self.successful_workflows / self.total_workflows_processed) * 100.0


# Interface for subreducers
class BaseSubreducer:
    """
    Abstract base interface for all subreducers.

    Defines the contract that all subreducers must implement
    for consistent integration with the Reducer Pattern Engine.
    """

    def __init__(self, name: str):
        """Initialize the subreducer with a name."""
        self.name = name

    async def process(self, request: WorkflowRequest) -> SubreducerResult:
        """
        Process a workflow request.

        Args:
            request: The workflow request to process

        Returns:
            SubreducerResult: The processing result

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement process method")

    def supports_workflow_type(self, workflow_type: WorkflowType) -> bool:
        """
        Check if this subreducer supports the given workflow type.

        Args:
            workflow_type: The workflow type to check

        Returns:
            bool: True if supported, False otherwise
        """
        raise NotImplementedError(
            "Subclasses must implement supports_workflow_type method"
        )
