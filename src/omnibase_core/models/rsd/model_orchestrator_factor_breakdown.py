#!/usr/bin/env python3
"""
Orchestrator Factor Breakdown Model - ONEX Standards Compliant.

Extended factor breakdown model for orchestrator-specific RSD calculations
with multiplicative boost/penalty system.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.rsd.model_factor_detail import ModelFactorDetail


class ModelOrchestratorFactorDetail(BaseModel):
    """
    Orchestrator-specific factor detail with boost/penalty information.

    Extends basic factor detail with multiplicative factors,
    boost/penalty explanations, and orchestrator-specific metadata.
    """

    base_factor: ModelFactorDetail = Field(
        description="Base 5-factor RSD calculation detail",
    )

    orchestrator_multiplier: float = Field(
        description="Orchestrator-specific multiplier (0.5-2.0)",
        ge=0.5,
        le=2.0,
    )

    boost_penalty_type: str = Field(
        description="Type of boost or penalty applied",
        pattern=r"^(boost|penalty|neutral)$",
    )

    orchestrator_contribution: float = Field(
        description="Additional contribution from orchestrator factors",
        ge=0.0,
    )

    final_contribution: float = Field(
        description="Final contribution after orchestrator adjustments",
        ge=0.0,
    )

    orchestrator_explanation: str = Field(
        description="Explanation of orchestrator-specific adjustments",
        min_length=1,
    )


class ModelOrchestratorPriorityFactorBreakdown(BaseModel):
    """
    Complete factor breakdown for orchestrator-enhanced RSD calculations.

    Extends the standard 5-factor breakdown with orchestrator-specific
    boost/penalty factors and detailed explanation of adjustments.
    """

    ticket_id: str = Field(
        description="Ticket ID this breakdown applies to",
        min_length=1,
    )

    # Enhanced 5-factor breakdown with orchestrator adjustments
    dependency_distance: ModelOrchestratorFactorDetail = Field(
        description="Enhanced dependency distance factor with orchestrator adjustments",
    )

    failure_surface: ModelOrchestratorFactorDetail = Field(
        description="Enhanced failure surface factor with orchestrator adjustments",
    )

    time_decay: ModelOrchestratorFactorDetail = Field(
        description="Enhanced time decay factor with orchestrator adjustments",
    )

    agent_utility: ModelOrchestratorFactorDetail = Field(
        description="Enhanced agent utility factor with orchestrator adjustments",
    )

    user_weighting: ModelOrchestratorFactorDetail = Field(
        description="Enhanced user weighting factor with orchestrator adjustments",
    )

    # Orchestrator-specific factor contributions
    critical_path_boost: float = Field(
        description="Critical path priority boost multiplier (1.0-1.5)",
        ge=1.0,
        le=1.5,
    )

    lane_contention_penalty: float = Field(
        description="Lane contention priority penalty multiplier (0.7-1.0)",
        ge=0.7,
        le=1.0,
    )

    lease_ttl_pressure: float = Field(
        description="Lease TTL pressure multiplier (1.0-2.0)",
        ge=1.0,
        le=2.0,
    )

    coordination_overhead_penalty: float = Field(
        description="Coordination overhead penalty multiplier (0.8-1.0)",
        ge=0.8,
        le=1.0,
    )

    event_dependency_factor: float = Field(
        description="Event dependency factor multiplier (0.9-1.2)",
        ge=0.9,
        le=1.2,
    )

    # Summary metrics
    base_score: float = Field(
        description="Original 5-factor RSD score (0.0-100.0)",
        ge=0.0,
        le=100.0,
    )

    orchestrator_adjusted_score: float = Field(
        description="Final score after orchestrator adjustments (0.0-150.0)",
        ge=0.0,
        le=150.0,
    )

    total_orchestrator_impact: float = Field(
        description="Total impact of orchestrator factors (-50.0 to +50.0)",
        ge=-50.0,
        le=50.0,
    )

    orchestrator_mode_enabled: bool = Field(
        description="Whether orchestrator mode was enabled for this calculation",
    )

    algorithm_version: str = Field(
        default="2.1.0-orchestrator",
        description="Algorithm version with orchestrator extensions",
    )

    calculation_explanation: str = Field(
        description="Human-readable explanation of the orchestrator adjustments",
        min_length=1,
    )

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        validate_assignment = True
