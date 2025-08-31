#!/usr/bin/env python3
"""
RSD Calculation Context Model - ONEX Standards Compliant.

Context model for RSD priority calculations providing type-safe context
parameters for both base and orchestrator-enhanced calculations.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelCalculationContext(BaseModel):
    """
    Type-safe context for RSD priority calculations.

    Provides structured context parameters for base RSD calculations,
    replacing generic Dict usage with strongly typed model.
    """

    ticket_metadata: dict[str, str] | None = Field(
        default_factory=dict,
        description="Additional ticket metadata for calculation context",
    )

    calculation_options: dict[str, bool] | None = Field(
        default_factory=dict,
        description="Calculation options and feature flags",
    )

    performance_hints: dict[str, float] | None = Field(
        default_factory=dict,
        description="Performance hints and optimization parameters",
    )

    cache_settings: dict[str, int] | None = Field(
        default_factory=dict,
        description="Cache TTL and size settings for this calculation",
    )

    validation_rules: dict[str, str] | None = Field(
        default_factory=dict,
        description="Custom validation rules and constraints",
    )

    request_metadata: dict[str, str] | None = Field(
        default_factory=dict,
        description="Request-specific metadata (user ID, session, etc.)",
    )

    calculation_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when calculation context was created",
    )

    include_debug_info: bool = Field(
        default=False,
        description="Whether to include debug information in results",
    )

    force_recalculation: bool = Field(
        default=False,
        description="Whether to bypass cache and force recalculation",
    )

    class Config:
        """Pydantic model configuration."""

        extra = "forbid"  # Prevent additional fields
        validate_assignment = True
