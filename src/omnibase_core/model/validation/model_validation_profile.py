"""Validation profile model for configuring tool validation strategies."""

from omnibase.enums.enum_validation_mode import EnumValidationMode
from pydantic import BaseModel, Field


class ModelValidationProfile(BaseModel):
    """Validation profile configuration for different tool types."""

    profile_name: str = Field(
        ...,
        description="Name of the validation profile",
        min_length=1,
    )
    max_failures_allowed: int = Field(
        default=0,
        description="Maximum number of test failures allowed",
        ge=0,
    )
    timeout_seconds: int = Field(
        default=600,
        description="Maximum validation time",
        gt=0,
        le=7200,
    )
    mode: EnumValidationMode = Field(
        default=EnumValidationMode.STRICT,
        description="Validation mode",
    )
    scenario_types: list[str] = Field(
        default_factory=lambda: ["smoke", "regression"],
        description="Types of scenarios to run",
    )
