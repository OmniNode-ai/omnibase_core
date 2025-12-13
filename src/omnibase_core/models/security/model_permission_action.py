"""
Permission action model for defining allowed actions in permission constraints.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class ModelPermissionAction(BaseModel):
    """
    Permission action definition.
    Defines specific actions that can be performed on resources.
    """

    action_id: UUID = Field(
        default=...,
        description="Unique action identifier",
        pattern="^[a-z][a-z0-9_-]*$",
    )

    action_name: str = Field(default=..., description="Human-readable action name")

    action_type: str = Field(
        default=...,
        description="Type of action (read, write, delete, execute, admin)",
        pattern="^(read|write|delete|execute|admin|custom)$",
    )

    resource_types: list[str] = Field(
        default_factory=list,
        description="Resource types this action applies to",
    )

    requires_approval: bool = Field(
        default=False,
        description="Whether this action requires approval",
    )

    risk_level: str = Field(
        default="medium",
        description="Risk level of this action",
        pattern="^(low|medium|high|critical)$",
    )

    description: str | None = Field(
        default=None,
        description="Detailed description of the action",
    )

    # Constraints
    max_frequency_per_hour: int | None = Field(
        default=None,
        description="Maximum times this action can be performed per hour",
        ge=0,
    )

    cooldown_minutes: int | None = Field(
        default=None,
        description="Cooldown period between actions in minutes",
        ge=0,
    )

    # Audit requirements
    audit_required: bool = Field(
        default=True,
        description="Whether this action must be audited",
    )

    audit_detail_level: str = Field(
        default="standard",
        description="Level of audit detail required",
        pattern="^(minimal|standard|detailed|comprehensive)$",
    )
