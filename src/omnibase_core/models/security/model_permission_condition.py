from pydantic import Field

"""
Permission condition model for defining conditional access rules.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.security.model_condition_value import ModelConditionValue
from omnibase_core.models.security.model_required_attributes import (
    ModelRequiredAttributes,
)


class ModelPermissionCondition(BaseModel):
    """
    Permission condition definition.
    Defines conditions that must be met for permission to be granted.
    """

    condition_id: str = Field(
        ...,
        description="Unique condition identifier",
        pattern="^[a-z][a-z0-9_-]*$",
    )

    condition_type: str = Field(
        ...,
        description="Type of condition",
        pattern="^(time|location|attribute|resource|user|custom)$",
    )

    operator: str = Field(
        ...,
        description="Comparison operator",
        pattern="^(eq|neq|gt|gte|lt|lte|in|not_in|contains|matches)$",
    )

    field_name: str = Field(..., description="Field to evaluate")

    expected_value: ModelConditionValue = Field(
        ...,
        description="Expected value for comparison",
    )

    # Time-based conditions
    time_window_start: str | None = Field(
        None,
        description="Start time for time-based conditions (HH:MM format)",
    )

    time_window_end: str | None = Field(
        None,
        description="End time for time-based conditions (HH:MM format)",
    )

    days_of_week: list[str] | None = Field(
        None,
        description="Days when condition applies (mon, tue, wed, thu, fri, sat, sun)",
    )

    # Location-based conditions
    allowed_locations: list[str] | None = Field(
        None,
        description="Allowed geographic locations",
    )

    ip_ranges: list[str] | None = Field(
        None,
        description="Allowed IP ranges (CIDR notation)",
    )

    # Attribute conditions
    required_attributes: ModelRequiredAttributes | None = Field(
        None,
        description="Required user/resource attributes",
    )

    # Logical operators
    combine_with: str | None = Field(
        None,
        description="How to combine with other conditions",
        pattern="^(and|or)$",
    )

    negate: bool = Field(default=False, description="Whether to negate this condition")

    # Metadata
    description: str | None = Field(
        None,
        description="Human-readable description of the condition",
    )

    error_message: str | None = Field(
        None,
        description="Custom error message when condition fails",
    )
