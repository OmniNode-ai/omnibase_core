"""
Permission Custom Constraints Model

Type-safe custom constraints for permissions.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.services.model_custom_fields import ModelCustomFields


class ModelPermissionCustomConstraints(BaseModel):
    """
    Type-safe custom constraints for permissions.

    Provides structured custom constraint definitions.
    """

    # Time-based constraints
    time_of_day_start: str | None = Field(
        default=None,
        description="Start time for daily access window (HH:MM)",
        pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$",
    )

    time_of_day_end: str | None = Field(
        default=None,
        description="End time for daily access window (HH:MM)",
        pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$",
    )

    allowed_days_of_week: list[int] = Field(
        default_factory=list,
        description="Allowed days (0=Sunday, 6=Saturday)",
    )

    blackout_dates: list[str] = Field(
        default_factory=list,
        description="Dates when access is blocked (ISO format)",
    )

    # Resource constraints
    max_resource_count: int | None = Field(
        default=None,
        description="Maximum number of resources that can be accessed",
        ge=1,
    )

    resource_name_pattern: str | None = Field(
        default=None,
        description="Regex pattern for allowed resource names",
    )

    excluded_resources: list[str] = Field(
        default_factory=list,
        description="Specific resources that are excluded",
    )

    # Action constraints
    allowed_actions: list[str] = Field(
        default_factory=list,
        description="Specific actions allowed with this permission",
    )

    prohibited_actions: list[str] = Field(
        default_factory=list,
        description="Actions explicitly prohibited",
    )

    action_rate_limits: dict[str, int] = Field(
        default_factory=dict,
        description="Rate limits per action (action -> max per hour)",
    )

    # Context constraints
    required_context_keys: list[str] = Field(
        default_factory=list,
        description="Context keys that must be present",
    )

    required_context_values: dict[str, str] = Field(
        default_factory=dict,
        description="Required context key-value pairs",
    )

    # Delegation constraints
    max_delegation_duration_hours: int | None = Field(
        default=None,
        description="Maximum duration for delegated permissions",
        ge=1,
    )

    delegation_scope_reduction: list[str] = Field(
        default_factory=list,
        description="Scopes that must be removed when delegating",
    )

    # Custom fields for extensibility
    custom_fields: ModelCustomFields | None = Field(
        default=None,
        description="Additional custom constraints",
    )
