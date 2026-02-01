"""
OmniMemory Contract Schema Model.

YAML contract schema for OmniMemory configuration that allows declarative
configuration of memory behavior, retention policies, and cost thresholds.
"""

from __future__ import annotations

from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelOmniMemoryContract(BaseModel):
    """YAML contract schema for OmniMemory configuration.

    Defines memory behavior including retention policies and cost controls
    for decision, failure, and cost tracking in the OmniMemory system.

    Attributes:
        contract_id: Unique identifier for this contract.
        name: Human-readable contract name.
        version: Contract version following SemVer 2.0.0.
        retention_policy: Policy for data retention (forever, ttl, count_limit).
        retention_value: TTL in days or max count depending on retention_policy.
        default_budget: Default cost budget for operations.
        warning_threshold: Threshold (0.0-1.0) at which to emit budget warnings.
        hard_ceiling: Absolute maximum budget multiplier.
        track_decisions: Whether to track decision events.
        track_failures: Whether to track failure events.
        track_costs: Whether to track cost metrics.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # Identity
    contract_id: UUID
    name: str | None = Field(default=None, description="Human-readable contract name")
    version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Contract version following SemVer 2.0.0",
    )

    # Behavior
    retention_policy: Literal["forever", "ttl", "count_limit"] = Field(
        description="Data retention policy"
    )
    retention_value: int | None = Field(
        default=None,
        ge=1,
        description="TTL in days (for 'ttl') or max count (for 'count_limit'). Must be >= 1.",
    )

    # Cost controls
    default_budget: float = Field(description="Default cost budget for operations")
    warning_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Budget warning threshold (0.0-1.0)",
    )
    hard_ceiling: float = Field(
        default=1.0,
        ge=0.0,
        description="Absolute maximum budget multiplier",
    )

    # Decision tracking
    track_decisions: bool = Field(
        default=True, description="Whether to track decision events"
    )
    track_failures: bool = Field(
        default=True, description="Whether to track failure events"
    )
    track_costs: bool = Field(default=True, description="Whether to track cost metrics")

    @model_validator(mode="after")
    def validate_retention(self) -> Self:
        """Ensure retention_value is provided when policy requires it."""
        if self.retention_policy != "forever" and self.retention_value is None:
            raise ValueError(
                "retention_value is required when retention_policy is 'ttl' or 'count_limit'"
            )
        return self

    @model_validator(mode="after")
    def validate_threshold_ceiling(self) -> Self:
        """Ensure warning_threshold does not exceed hard_ceiling."""
        if self.warning_threshold > self.hard_ceiling:
            raise ValueError(
                f"warning_threshold ({self.warning_threshold}) cannot exceed "
                f"hard_ceiling ({self.hard_ceiling})"
            )
        return self
