"""
Approval Requirements Model

Type-safe approval requirements configuration.
"""

from pydantic import BaseModel, Field


class ModelApprovalRequirements(BaseModel):
    """
    Type-safe approval requirements configuration.

    Defines approval workflow requirements for permissions.
    """

    required: bool = Field(False, description="Whether approval is required")

    types: list[str] = Field(
        default_factory=list,
        description="Types of approval required (e.g., 'manager', 'security', 'admin')",
    )

    min_approvals: int = Field(
        1,
        description="Minimum number of approvals required",
        ge=0,
        le=10,
    )

    timeout_hours: int | None = Field(
        None,
        description="Hours after which approval request expires",
        ge=1,
        le=168,  # Max 1 week
    )

    auto_approve_conditions: list[str] = Field(
        default_factory=list,
        description="Conditions under which approval is automatic",
    )

    escalation_enabled: bool = Field(
        False,
        description="Whether escalation is enabled after timeout",
    )

    escalation_chain: list[str] = Field(
        default_factory=list,
        description="Escalation chain if primary approvers don't respond",
    )

    approval_message_template: str | None = Field(
        None,
        description="Template for approval request messages",
    )
