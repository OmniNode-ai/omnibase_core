#!/usr/bin/env python3
"""
Orchestrator Internal Types - ONEX Standards Compliant.

Internal data structures for orchestrator services providing type-safe
replacements for generic Dict usage in caches and calculations.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


class ModelLaneState(BaseModel):
    """
    Type-safe lane state representation.

    Replaces generic Dict usage in lane contention analysis
    with strongly typed data structure.
    """

    capacity: int = Field(description="Maximum concurrent tasks for this lane", ge=1)

    active_tasks: int = Field(description="Currently executing tasks", ge=0)

    queue_depth: int = Field(description="Tasks waiting in queue", ge=0)

    average_task_duration_minutes: float = Field(
        description="Average task completion time in minutes", ge=0.0
    )

    last_updated: datetime = Field(description="Last update timestamp for this state")

    class Config:
        """Pydantic model configuration."""

        extra = "forbid"
        validate_assignment = True


class ModelUtilizationMetrics(BaseModel):
    """
    Type-safe utilization metrics.

    Calculated metrics for lane utilization analysis.
    """

    utilization: float = Field(
        description="Utilization percentage (0-100)", ge=0.0, le=100.0
    )

    active_tasks: int = Field(description="Currently active tasks", ge=0)

    queue_depth: int = Field(description="Queued tasks waiting for execution", ge=0)

    capacity: int = Field(description="Lane capacity", ge=1)

    class Config:
        """Pydantic model configuration."""

        extra = "forbid"
        validate_assignment = True


class ModelWaitTimeMetrics(BaseModel):
    """
    Type-safe wait time metrics.

    Calculated wait time analysis for lane contention.
    """

    average_wait_minutes: float = Field(
        description="Average wait time in minutes", ge=0.0
    )

    max_estimated_wait_minutes: float = Field(
        description="Maximum estimated wait time", ge=0.0
    )

    queue_processing_rate: int = Field(
        description="Rate at which queue is processed", ge=1
    )

    class Config:
        """Pydantic model configuration."""

        extra = "forbid"
        validate_assignment = True


class ModelTicketRequirements(BaseModel):
    """
    Type-safe ticket execution requirements.

    Requirements for ticket execution in lane assignment.
    """

    preferred_capacity: Optional[int] = Field(
        default=None, description="Preferred lane capacity for execution", ge=1
    )

    priority_level: Optional[str] = Field(
        default=None, description="Priority level (high, medium, low)"
    )

    estimated_duration_minutes: Optional[float] = Field(
        default=None, description="Estimated execution duration", ge=0.0
    )

    resource_requirements: Dict[str, str] = Field(
        default_factory=dict, description="Resource requirements mapping"
    )

    execution_constraints: Dict[str, bool] = Field(
        default_factory=dict, description="Execution constraints and flags"
    )

    class Config:
        """Pydantic model configuration."""

        extra = "forbid"
        validate_assignment = True


class ModelCriticalPathData(BaseModel):
    """
    Type-safe critical path calculation data.

    Internal data structure for critical path analysis.
    """

    path: List[str] = Field(description="Critical path as list of ticket IDs")

    total_effort_hours: float = Field(
        description="Total effort hours for critical path", ge=0.0
    )

    calculated_at: datetime = Field(description="When this path was calculated")

    slack_analysis: Dict[str, float] = Field(
        default_factory=dict, description="Slack time analysis for each node"
    )

    bottleneck_scores: Dict[str, float] = Field(
        default_factory=dict, description="Bottleneck risk scores for each node"
    )

    class Config:
        """Pydantic model configuration."""

        extra = "forbid"
        validate_assignment = True


class ModelLeaseAnalysisCache(BaseModel):
    """
    Type-safe lease analysis cache entry.

    Cached lease TTL analysis results for performance.
    """

    ticket_id: str = Field(description="Ticket ID for this analysis", min_length=1)

    pressure_score: float = Field(
        description="Calculated TTL pressure score", ge=1.0, le=2.0
    )

    expires_at: datetime = Field(description="When this cache entry expires")

    lease_count: int = Field(description="Number of leases analyzed", ge=0)

    urgency_level: str = Field(
        description="Urgency level (low, medium, high, critical)"
    )

    class Config:
        """Pydantic model configuration."""

        extra = "forbid"
        validate_assignment = True
