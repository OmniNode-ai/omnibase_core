#!/usr/bin/env python3
"""
Priority calculation models - ONEX Standards Compliant.

Models for RSD 5-factor priority calculation results and explanations.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ModelFactorScore(BaseModel):
    """
    Model for individual factor score in priority calculation.

    Represents one of the 5 factors in RSD priority algorithm.
    """

    factor_name: str = Field(
        description="Name of the factor (dependency_distance, failure_surface, etc)",
    )

    raw_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Raw calculated score before weighting (0.0-1.0)",
    )

    weight: float = Field(
        ge=0.0,
        le=1.0,
        description="Factor weight in final calculation",
    )

    weighted_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Score after applying weight (raw_score * weight)",
    )

    components: list["ModelScoreComponent"] = Field(
        default_factory=list,
        description="Breakdown of how this factor was calculated",
    )

    explanation: str = Field(
        description="Human-readable explanation of this factor's score",
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        default=1.0,
        description="Confidence in this factor's calculation",
    )

    class Config:
        """Pydantic model configuration."""

        validate_assignment = True


class ModelScoreComponent(BaseModel):
    """
    Model for component of a factor score.

    Provides detailed breakdown of factor calculations.
    """

    component_name: str = Field(description="Name of this component")

    value: float = Field(description="Calculated value")

    max_value: float = Field(description="Maximum possible value")

    normalized_value: float = Field(
        ge=0.0,
        le=1.0,
        description="Normalized value (0.0-1.0)",
    )

    description: str = Field(description="What this component measures")


class ModelPriorityCalculation(BaseModel):
    """
    Model for complete priority calculation result.

    Contains all factor scores and final priority with full explanation.
    """

    ticket_id: str = Field(description="Ticket being calculated")

    final_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Final calculated priority score (0.0-1.0)",
    )

    factors: list[ModelFactorScore] = Field(
        description="All factor scores in the calculation",
    )

    calculation_time: datetime = Field(
        default_factory=datetime.now,
        description="When this calculation was performed",
    )

    calculation_duration_ms: int = Field(
        ge=0,
        description="Time taken to calculate in milliseconds",
    )

    algorithm_version: str = Field(
        default="rsd-5-factor-v1",
        description="Algorithm version used",
    )

    override_applied: bool = Field(
        default=False,
        description="Whether a manual override affected the score",
    )

    override_details: Optional["ModelOverrideDetails"] = Field(
        default=None,
        description="Details of any override applied",
    )

    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        default=1.0,
        description="Overall confidence in the calculation",
    )

    warnings: list[str] = Field(
        default_factory=list,
        description="Any warnings during calculation",
    )

    class Config:
        """Pydantic model configuration."""

        validate_assignment = True

    def get_factor_by_name(self, name: str) -> ModelFactorScore | None:
        """Get a specific factor score by name."""
        for factor in self.factors:
            if factor.factor_name == name:
                return factor
        return None

    def get_summary(self) -> str:
        """Get a human-readable summary of the calculation."""
        lines = [
            f"Priority Calculation for {self.ticket_id}",
            f"Final Score: {self.final_score:.3f}",
            "",
            "Factor Breakdown:",
        ]

        for factor in self.factors:
            lines.append(
                f"  {factor.factor_name}: {factor.raw_score:.3f} "
                f"(weight: {factor.weight:.0%}) = {factor.weighted_score:.3f}",
            )

        if self.override_applied and self.override_details:
            lines.extend(
                [
                    "",
                    "Override Applied:",
                    f"  Original: {self.override_details.original_score:.3f}",
                    f"  Override: {self.override_details.override_score:.3f}",
                    f"  Reason: {self.override_details.reason}",
                ],
            )

        if self.warnings:
            lines.extend(["", "Warnings:"] + [f"  - {w}" for w in self.warnings])

        return "\n".join(lines)


class ModelOverrideDetails(BaseModel):
    """
    Model for manual override details.

    Tracks how manual overrides affected the calculation.
    """

    override_id: str = Field(description="ID of the override applied")

    original_score: float = Field(ge=0.0, le=1.0, description="Score before override")

    override_score: float = Field(ge=0.0, le=1.0, description="Score from override")

    blended_score: float = Field(ge=0.0, le=1.0, description="Final blended score")

    blend_strength: float = Field(
        ge=0.0,
        le=1.0,
        description="How much the override affected final score",
    )

    reason: str = Field(description="Reason for the override")

    authorized_by: str = Field(description="Who authorized the override")

    expires_at: datetime = Field(description="When the override expires")


class ModelBatchPriorityResult(BaseModel):
    """
    Model for batch priority calculation results.

    Used when calculating priorities for multiple tickets at once.
    """

    calculations: list[ModelPriorityCalculation] = Field(
        description="All individual calculations",
    )

    total_tickets: int = Field(ge=0, description="Total number of tickets calculated")

    successful_calculations: int = Field(
        ge=0,
        description="Number of successful calculations",
    )

    failed_calculations: int = Field(ge=0, description="Number of failed calculations")

    batch_duration_ms: int = Field(ge=0, description="Total time for batch calculation")

    average_duration_ms: float = Field(ge=0.0, description="Average time per ticket")

    cache_hits: int = Field(
        ge=0,
        default=0,
        description="Number of calculations served from cache",
    )

    errors: list["ModelCalculationError"] = Field(
        default_factory=list,
        description="Any errors during batch calculation",
    )

    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When batch calculation was performed",
    )

    def get_sorted_tickets(self) -> list[str]:
        """Get ticket IDs sorted by priority score (highest first)."""
        sorted_calcs = sorted(
            self.calculations,
            key=lambda c: c.final_score,
            reverse=True,
        )
        return [calc.ticket_id for calc in sorted_calcs]

    def get_calculation(self, ticket_id: str) -> ModelPriorityCalculation | None:
        """Get calculation for specific ticket."""
        for calc in self.calculations:
            if calc.ticket_id == ticket_id:
                return calc
        return None


class ModelCalculationError(BaseModel):
    """
    Model for calculation error details.

    Tracks errors that occur during priority calculation.
    """

    ticket_id: str = Field(description="Ticket that failed to calculate")

    error_type: str = Field(description="Type of error (validation, timeout, etc)")

    error_message: str = Field(description="Error message")

    error_details: str | None = Field(
        default=None,
        description="Additional error details or stack trace",
    )

    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When error occurred",
    )


# Update forward references
ModelFactorScore.update_forward_refs()
ModelPriorityCalculation.update_forward_refs()
