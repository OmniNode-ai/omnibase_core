#!/usr/bin/env python3
"""
Orchestrator Context Model - ONEX Standards Compliant.

Orchestrator-specific context model for enhanced RSD priority calculations
with workflow coordination factors.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelWorkflowGraphNode(BaseModel):
    """
    Workflow graph node representation for critical path analysis.

    Contains ticket metadata and execution context for graph traversal
    and critical path calculation in workflow coordination scenarios.
    """

    ticket_id: str = Field(description="Unique ticket identifier", min_length=1)

    estimated_effort_hours: float = Field(
        description="Estimated effort hours for completion",
        ge=0.0,
    )

    dependencies: list[str] = Field(
        default_factory=list,
        description="List of dependent ticket IDs",
    )

    parallel_eligibility: bool = Field(
        default=False,
        description="Whether this node can execute in parallel with others",
    )

    execution_lane: str | None = Field(
        default=None,
        description="Assigned execution lane (L1-L6)",
    )


class ModelCriticalPathAnalysis(BaseModel):
    """
    Critical path analysis results for workflow prioritization.

    Contains critical path identification, bottleneck analysis,
    and workflow optimization recommendations.
    """

    is_on_critical_path: bool = Field(
        description="Whether ticket is on the critical path",
    )

    critical_path_position: int = Field(
        description="Position in critical path (0-based)",
        ge=0,
    )

    critical_path_length: int = Field(description="Total length of critical path", ge=1)

    slack_time_hours: float = Field(description="Available slack time in hours", ge=0.0)

    bottleneck_risk_score: float = Field(
        description="Risk of becoming a bottleneck (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    parallel_opportunities: int = Field(
        description="Number of parallel execution opportunities",
        ge=0,
    )


class ModelLaneContention(BaseModel):
    """
    Execution lane contention analysis for resource optimization.

    Tracks lane utilization, congestion levels, and contention
    penalties for workflow resource allocation.
    """

    lane_id: str = Field(
        description="Execution lane identifier (L1-L6)",
        pattern=r"^L[1-6]$",
    )

    current_utilization: float = Field(
        description="Current lane utilization percentage (0.0-100.0)",
        ge=0.0,
        le=100.0,
    )

    queue_depth: int = Field(description="Number of tickets queued for this lane", ge=0)

    average_wait_time_minutes: float = Field(
        description="Average wait time in minutes",
        ge=0.0,
    )

    congestion_level: float = Field(
        description="Congestion severity (0.0-1.0, >0.8 is critical)",
        ge=0.0,
        le=1.0,
    )

    predicted_availability_hours: float = Field(
        description="Predicted hours until lane becomes available",
        ge=0.0,
    )


class ModelWorkLease(BaseModel):
    """
    Work lease information for TTL pressure calculations.

    Contains lease metadata, expiration tracking, and renewal
    policies for time-sensitive workflow coordination.
    """

    lease_id: str = Field(description="Unique lease identifier", min_length=1)

    granted_at: datetime = Field(description="When the lease was granted")

    expires_at: datetime = Field(description="When the lease expires")

    lease_duration_minutes: int = Field(
        description="Original lease duration in minutes",
        ge=1,
    )

    renewal_count: int = Field(
        description="Number of times lease has been renewed",
        ge=0,
    )

    max_renewals: int = Field(description="Maximum allowed renewals", ge=0)

    auto_renewal_enabled: bool = Field(
        default=True,
        description="Whether automatic renewal is enabled",
    )

    scope: str = Field(
        description="Lease scope (ticket, workflow, resource)",
        pattern=r"^(ticket|workflow|resource)$",
    )


class ModelCoordinationOverhead(BaseModel):
    """
    Coordination overhead metrics for multi-node operations.

    Tracks communication overhead, synchronization costs, and
    coordination complexity for distributed workflow execution.
    """

    node_count: int = Field(
        description="Number of nodes involved in coordination",
        ge=1,
    )

    communication_overhead_factor: float = Field(
        description="Communication overhead multiplier (1.0 = no overhead)",
        ge=1.0,
    )

    synchronization_points: int = Field(
        description="Number of synchronization points required",
        ge=0,
    )

    consensus_required: bool = Field(
        default=False,
        description="Whether consensus is required for coordination",
    )

    coordination_complexity: float = Field(
        description="Overall coordination complexity (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    estimated_overhead_minutes: float = Field(
        description="Estimated coordination overhead in minutes",
        ge=0.0,
    )


class ModelEventDependency(BaseModel):
    """
    Event dependency tracking for event-driven workflows.

    Contains event subscription metadata, dependency chains,
    and event-driven workflow trigger analysis.
    """

    event_name: str = Field(
        description="Event name this ticket depends on",
        min_length=1,
    )

    event_type: str = Field(description="Type of event dependency", min_length=1)

    dependency_depth: int = Field(description="Depth in event dependency chain", ge=1)

    is_blocking: bool = Field(description="Whether this event dependency is blocking")

    timeout_minutes: int | None = Field(
        default=None,
        description="Timeout for event dependency in minutes",
        ge=1,
    )

    retry_enabled: bool = Field(
        default=True,
        description="Whether retry is enabled for this dependency",
    )

    fallback_available: bool = Field(
        default=False,
        description="Whether fallback execution path is available",
    )


class ModelOrchestratorContext(BaseModel):
    """
    Complete orchestrator context for enhanced RSD calculations.

    Aggregates all orchestrator-specific factors including critical path
    analysis, lane contention, lease pressure, coordination overhead,
    and event dependencies for sophisticated workflow prioritization.
    """

    ticket_id: str = Field(description="Target ticket ID for context", min_length=1)

    # Critical path analysis
    workflow_graph: list[ModelWorkflowGraphNode] = Field(
        default_factory=list,
        description="Complete workflow graph for critical path analysis",
    )

    critical_path_analysis: ModelCriticalPathAnalysis | None = Field(
        default=None,
        description="Critical path analysis results",
    )

    # Lane contention analysis
    target_lane: str | None = Field(
        default=None,
        description="Target execution lane for this ticket",
        pattern=r"^L[1-6]$",
    )

    lane_contention: ModelLaneContention | None = Field(
        default=None,
        description="Current lane contention analysis",
    )

    alternative_lanes: list[str] = Field(
        default_factory=list,
        description="Alternative execution lanes available",
    )

    # Lease TTL pressure
    active_leases: list[ModelWorkLease] = Field(
        default_factory=list,
        description="Active work leases for this ticket",
    )

    # Coordination overhead
    coordination_overhead: ModelCoordinationOverhead | None = Field(
        default=None,
        description="Multi-node coordination overhead analysis",
    )

    # Event dependencies
    event_dependencies: list[ModelEventDependency] = Field(
        default_factory=list,
        description="Event-driven workflow dependencies",
    )

    # Orchestrator mode settings
    orchestrator_mode_enabled: bool = Field(
        default=False,
        description="Whether orchestrator-specific factors are enabled",
    )

    algorithm_version: str = Field(
        default="2.1.0",
        description="RSD algorithm version with orchestrator extensions",
    )

    calculation_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When context was captured",
    )

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        validate_assignment = True
        json_encoders = {datetime: lambda v: v.isoformat()}
