"""
Workflow Coordination Subcontract Models for ONEX ORCHESTRATOR Nodes.

Provides Pydantic models for workflow orchestration, node coordination, and
execution management capabilities specifically for ORCHESTRATOR nodes.

Generated from workflow_coordination subcontract following ONEX patterns.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

# Import existing enums instead of duplicating
from omnibase_core.enums.enum_node_health_status import EnumNodeHealthStatus
from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.enums.enum_workflow_coordination import (
    EnumAssignmentStatus,
    EnumExecutionPattern,
    EnumFailureRecoveryStrategy,
    EnumWorkflowStatus,
)
from omnibase_core.models.metadata.model_semver import ModelSemVer


class ModelWorkflowInstance(BaseModel):
    """A workflow execution instance."""

    workflow_id: UUID = Field(
        default_factory=uuid4, description="Unique identifier for the workflow instance"
    )

    workflow_name: str = Field(..., description="Name of the workflow")

    workflow_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Version of the workflow definition",
    )

    created_timestamp: datetime = Field(
        ..., description="When the workflow instance was created"
    )

    status: EnumWorkflowStatus = Field(
        ..., description="Current status of the workflow"
    )

    input_parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Input parameters for the workflow"
    )

    execution_context: Dict[str, Any] = Field(
        default_factory=dict, description="Execution context for the workflow"
    )


class ModelNodeAssignment(BaseModel):
    """Node assignment for workflow execution."""

    node_id: UUID = Field(
        default_factory=uuid4, description="Unique identifier for the node"
    )

    node_type: EnumNodeType = Field(..., description="Type of the node")

    assignment_status: EnumAssignmentStatus = Field(
        ..., description="Current status of the assignment"
    )

    execution_time_ms: int = Field(
        default=0, description="Time spent executing on this node in milliseconds", ge=0
    )

    resource_usage: Dict[str, float] = Field(
        default_factory=dict, description="Resource usage metrics for this node"
    )


class ModelSynchronizationPoint(BaseModel):
    """A synchronization point in workflow execution."""

    point_name: str = Field(..., description="Name of the synchronization point")

    timestamp: datetime = Field(..., description="When the synchronization occurred")

    nodes_synchronized: int = Field(
        ..., description="Number of nodes synchronized at this point", ge=0
    )


class ModelCoordinationResult(BaseModel):
    """Result of node coordination operation."""

    coordination_id: UUID = Field(
        default_factory=uuid4, description="Unique identifier for this coordination"
    )

    workflow_id: UUID = Field(
        default_factory=uuid4, description="Workflow this coordination belongs to"
    )

    nodes_coordinated: List[ModelNodeAssignment] = Field(
        default_factory=list, description="List of nodes that were coordinated"
    )

    coordination_overhead_ms: int = Field(
        ..., description="Time spent on coordination overhead in milliseconds", ge=0
    )

    synchronization_points: List[ModelSynchronizationPoint] = Field(
        default_factory=list,
        description="Synchronization points reached during coordination",
    )


class ModelNodeProgress(BaseModel):
    """Progress information for a single node."""

    node_id: UUID = Field(
        default_factory=uuid4, description="Unique identifier for the node"
    )

    node_type: EnumNodeType = Field(..., description="Type of the node")

    progress_percent: float = Field(
        ..., description="Progress percentage for this node", ge=0.0, le=100.0
    )

    status: str = Field(..., description="Current status of the node")


class ModelProgressStatus(BaseModel):
    """Overall workflow progress status."""

    workflow_id: UUID = Field(default_factory=uuid4, description="Workflow identifier")

    overall_progress_percent: float = Field(
        ..., description="Overall workflow progress percentage", ge=0.0, le=100.0
    )

    current_stage: str = Field(..., description="Current stage of the workflow")

    stages_completed: int = Field(..., description="Number of stages completed", ge=0)

    stages_total: int = Field(
        ..., description="Total number of stages in the workflow", ge=1
    )

    estimated_completion: Optional[datetime] = Field(
        default=None, description="Estimated completion time"
    )

    node_progress: List[ModelNodeProgress] = Field(
        default_factory=list, description="Progress of individual nodes"
    )


class ModelWorkflowMetrics(BaseModel):
    """Performance metrics for workflow execution."""

    total_execution_time_ms: int = Field(
        ..., description="Total workflow execution time in milliseconds", ge=0
    )

    coordination_overhead_ms: int = Field(
        ..., description="Time spent on coordination overhead in milliseconds", ge=0
    )

    node_utilization_percent: float = Field(
        ..., description="Node utilization percentage", ge=0.0, le=100.0
    )

    parallelism_achieved: float = Field(
        ..., description="Achieved parallelism factor", ge=0.0
    )

    synchronization_delays_ms: int = Field(
        ..., description="Total time spent on synchronization delays", ge=0
    )

    resource_efficiency_score: float = Field(
        ..., description="Resource efficiency score", ge=0.0, le=1.0
    )


class ModelWorkflowNode(BaseModel):
    """A node definition in a workflow graph."""

    node_id: UUID = Field(
        default_factory=uuid4, description="Unique identifier for the node"
    )

    node_type: EnumNodeType = Field(..., description="Type of the node")

    node_requirements: Dict[str, Any] = Field(
        default_factory=dict, description="Requirements for this node"
    )

    dependencies: List[UUID] = Field(
        default_factory=list, description="List of node IDs this node depends on"
    )


class ModelExecutionGraph(BaseModel):
    """Execution graph for a workflow."""

    nodes: List[ModelWorkflowNode] = Field(
        default_factory=list, description="Nodes in the execution graph"
    )


class ModelCoordinationRules(BaseModel):
    """Rules for workflow coordination."""

    synchronization_points: List[str] = Field(
        default_factory=list, description="Named synchronization points in the workflow"
    )

    parallel_execution_allowed: bool = Field(
        default=True, description="Whether parallel execution is allowed"
    )

    failure_recovery_strategy: EnumFailureRecoveryStrategy = Field(
        default=EnumFailureRecoveryStrategy.RETRY,
        description="Strategy for handling failures",
    )


class ModelWorkflowMetadata(BaseModel):
    """Metadata for a workflow definition."""

    name: str = Field(..., description="Name of the workflow")

    version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Version of the workflow",
    )

    description: str = Field(..., description="Description of the workflow")

    timeout_ms: int = Field(
        default=600000, description="Workflow timeout in milliseconds", ge=1000
    )


class ModelWorkflowDefinition(BaseModel):
    """Complete workflow definition."""

    workflow_metadata: ModelWorkflowMetadata = Field(
        ..., description="Workflow metadata"
    )

    execution_graph: ModelExecutionGraph = Field(
        ..., description="Execution graph for the workflow"
    )

    coordination_rules: ModelCoordinationRules = Field(
        default_factory=ModelCoordinationRules,
        description="Rules for workflow coordination",
    )


class ModelExecutionResult(BaseModel):
    """Result of workflow execution."""

    workflow_id: UUID = Field(default_factory=uuid4, description="Workflow identifier")

    status: EnumWorkflowStatus = Field(..., description="Final status of the workflow")

    execution_time_ms: int = Field(
        ..., description="Total execution time in milliseconds", ge=0
    )

    result_data: Dict[str, Any] = Field(
        default_factory=dict, description="Result data from the workflow"
    )

    error_message: Optional[str] = Field(
        default=None, description="Error message if workflow failed"
    )

    coordination_metrics: ModelWorkflowMetrics = Field(
        ..., description="Performance metrics for the execution"
    )


# Main subcontract definition model
class ModelWorkflowCoordinationSubcontract(BaseModel):
    """
    Workflow Coordination Subcontract for ORCHESTRATOR nodes.

    Provides workflow orchestration, node coordination, and execution
    management capabilities specifically for ORCHESTRATOR nodes in the ONEX architecture.
    """

    subcontract_name: str = Field(
        default="workflow_coordination_subcontract",
        description="Name of the subcontract",
    )

    subcontract_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Version of the subcontract",
    )

    applicable_node_types: List[str] = Field(
        default=["ORCHESTRATOR"],
        description="Node types this subcontract applies to (ORCHESTRATOR only)",
    )

    # Configuration
    max_concurrent_workflows: int = Field(
        default=10, description="Maximum number of concurrent workflows", ge=1, le=100
    )

    default_workflow_timeout_ms: int = Field(
        default=600000,
        description="Default workflow timeout in milliseconds",
        ge=60000,
        le=3600000,
    )

    node_coordination_timeout_ms: int = Field(
        default=30000,
        description="Node coordination timeout in milliseconds",
        ge=5000,
        le=300000,
    )

    checkpoint_interval_ms: int = Field(
        default=60000,
        description="Checkpoint interval in milliseconds",
        ge=10000,
        le=600000,
    )

    auto_retry_enabled: bool = Field(
        default=True, description="Whether automatic retry is enabled"
    )

    parallel_execution_enabled: bool = Field(
        default=True, description="Whether parallel execution is enabled"
    )

    workflow_persistence_enabled: bool = Field(
        default=True, description="Whether workflow state persistence is enabled"
    )

    # Failure recovery configuration
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for failed operations",
        ge=0,
        le=10,
    )

    retry_delay_ms: int = Field(
        default=2000,
        description="Delay between retries in milliseconds",
        ge=1000,
        le=60000,
    )

    exponential_backoff: bool = Field(
        default=True, description="Whether to use exponential backoff for retries"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "subcontract_name": "workflow_coordination_subcontract",
                "subcontract_version": "1.0.0",
                "applicable_node_types": ["ORCHESTRATOR"],
                "max_concurrent_workflows": 10,
                "default_workflow_timeout_ms": 600000,
                "node_coordination_timeout_ms": 30000,
                "checkpoint_interval_ms": 60000,
                "auto_retry_enabled": True,
                "parallel_execution_enabled": True,
                "workflow_persistence_enabled": True,
                "max_retries": 3,
                "retry_delay_ms": 2000,
                "exponential_backoff": True,
            }
        }
    }
