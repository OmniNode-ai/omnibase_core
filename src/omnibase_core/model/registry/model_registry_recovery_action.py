"""
Registry Recovery Action Model

Type-safe recovery action for registry validation issues.
"""

from pydantic import BaseModel, Field


class ModelRegistryRecoveryAction(BaseModel):
    """
    Type-safe recovery action for registry validation issues.

    Provides structured recovery plan actions.
    """

    priority: int = Field(..., description="Action priority (1=highest)", ge=1, le=10)

    action_type: str = Field(
        ...,
        description="Type of recovery action",
        pattern="^(fix_critical_tool|fix_high_priority_tool|address_warnings|fix_configuration|optimize_performance|security_remediation)$",
    )

    description: str = Field(
        ...,
        description="Human-readable description of the action",
    )

    estimated_time: str = Field(..., description="Estimated time to complete action")

    tool_name: str | None = Field(
        None,
        description="Name of tool to fix (if applicable)",
    )

    recommendations: list[str] = Field(
        default_factory=list,
        description="Specific recommendations for this action",
    )

    warnings: list[str] | None = Field(
        None,
        description="Warnings to address (if applicable)",
    )

    # Action metadata
    action_id: str | None = Field(None, description="Unique identifier for tracking")

    assignee: str | None = Field(
        None,
        description="Person/team assigned to this action",
    )

    dependencies: list[str] = Field(
        default_factory=list,
        description="Other actions this depends on",
    )

    automation_possible: bool = Field(
        False,
        description="Whether this action can be automated",
    )

    rollback_plan: str | None = Field(
        None,
        description="Rollback plan if action fails",
    )

    success_criteria: list[str] = Field(
        default_factory=list,
        description="Criteria for successful completion",
    )
