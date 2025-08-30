#!/usr/bin/env python3
"""
Orchestrator Prioritization Result Model - ONEX Standards Compliant.

Extended prioritization result model for orchestrator-enhanced RSD calculations
with base score preservation and orchestrator factor tracking.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.model.rsd.model_rsd_prioritization_result import (
    ModelRSDPrioritizationResult,
)


class ModelOrchestratorPrioritizationResult(BaseModel):
    """
    Complete prioritization result with orchestrator enhancements.

    Extends the standard RSD result with orchestrator-specific factors,
    maintaining backward compatibility while adding workflow coordination
    intelligence for sophisticated priority calculations.
    """

    # Base RSD calculation (maintains backward compatibility)
    base_result: ModelRSDPrioritizationResult = Field(
        description="Original 5-factor RSD prioritization result",
    )

    # Orchestrator-enhanced scoring
    orchestrator_adjusted_score: float = Field(
        description="Final score after orchestrator adjustments (0.0-150.0)",
        ge=0.0,
        le=150.0,
    )

    # Individual orchestrator factor contributions
    critical_path_boost_applied: float = Field(
        description="Critical path boost multiplier applied (1.0-1.5)",
        ge=1.0,
        le=1.5,
    )

    lane_contention_penalty_applied: float = Field(
        description="Lane contention penalty multiplier applied (0.7-1.0)",
        ge=0.7,
        le=1.0,
    )

    lease_ttl_pressure_applied: float = Field(
        description="Lease TTL pressure multiplier applied (1.0-2.0)",
        ge=1.0,
        le=2.0,
    )

    coordination_overhead_penalty_applied: float = Field(
        description="Coordination overhead penalty multiplier applied (0.8-1.0)",
        ge=0.8,
        le=1.0,
    )

    event_dependency_factor_applied: float = Field(
        description="Event dependency factor multiplier applied (0.9-1.2)",
        ge=0.9,
        le=1.2,
    )

    # Orchestrator mode metadata
    orchestrator_mode_enabled: bool = Field(
        description="Whether orchestrator mode was enabled for this calculation",
    )

    orchestrator_factors_detected: int = Field(
        description="Number of orchestrator factors that applied to this ticket",
        ge=0,
    )

    workflow_graph_size: int = Field(
        description="Size of workflow graph analyzed",
        ge=0,
    )

    target_execution_lane: str = Field(
        default="unassigned",
        description="Target execution lane (L1-L6 or unassigned)",
    )

    is_on_critical_path: bool = Field(
        description="Whether ticket was identified on critical path",
    )

    has_active_leases: bool = Field(description="Whether ticket has active work leases")

    requires_coordination: bool = Field(
        description="Whether ticket requires multi-node coordination",
    )

    # Impact analysis
    score_delta: float = Field(
        description="Difference between base and orchestrator-adjusted scores",
        ge=-50.0,
        le=50.0,
    )

    priority_ranking_impact: str = Field(
        description="Impact on priority ranking (elevated, maintained, reduced)",
        pattern=r"^(elevated|maintained|reduced)$",
    )

    orchestrator_recommendation: str = Field(
        description="Orchestrator-specific execution recommendation",
        min_length=1,
    )

    # Extended metadata
    algorithm_version: str = Field(
        default="2.1.0-orchestrator",
        description="Algorithm version with orchestrator extensions",
    )

    orchestrator_processing_time_ms: float = Field(
        description="Additional processing time for orchestrator factors in milliseconds",
        gt=0.0,
    )

    total_processing_time_ms: float = Field(
        description="Total processing time including orchestrator extensions",
        gt=0.0,
    )

    calculated_at: datetime = Field(
        description="When the orchestrator-enhanced priority was calculated",
        default_factory=datetime.now,
    )

    # Backward compatibility helpers
    @property
    def ticket_id(self) -> str:
        """Get ticket ID from base result for backward compatibility."""
        return self.base_result.ticket_id

    @property
    def overall_score(self) -> float:
        """
        Get effective overall score.

        Returns orchestrator-adjusted score when orchestrator mode is enabled,
        otherwise returns base score for backward compatibility.
        """
        return (
            self.orchestrator_adjusted_score
            if self.orchestrator_mode_enabled
            else self.base_result.overall_score
        )

    @property
    def dependency_distance_score(self) -> float:
        """Get dependency distance score from base result."""
        return self.base_result.dependency_distance_score

    @property
    def failure_surface_score(self) -> float:
        """Get failure surface score from base result."""
        return self.base_result.failure_surface_score

    @property
    def time_decay_score(self) -> float:
        """Get time decay score from base result."""
        return self.base_result.time_decay_score

    @property
    def agent_utility_score(self) -> float:
        """Get agent utility score from base result."""
        return self.base_result.agent_utility_score

    @property
    def user_weighting_score(self) -> float:
        """Get user weighting score from base result."""
        return self.base_result.user_weighting_score

    @property
    def processing_time_ms(self) -> float:
        """Get effective processing time including orchestrator extensions."""
        return self.total_processing_time_ms

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        validate_assignment = True
        json_encoders = {datetime: lambda v: v.isoformat()}
