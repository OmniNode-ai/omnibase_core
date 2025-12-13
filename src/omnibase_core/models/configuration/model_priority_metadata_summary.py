"""ONEX-compatible Priority Metadata Summary Model.

Summary model for priority metadata with ONEX compliance.
"""

from pydantic import BaseModel, Field


class ModelPriorityMetadataSummary(BaseModel):
    """Summary of priority metadata."""

    owner: str | None = Field(default=None, description="Owner of the priority")
    approval_required: bool = Field(
        default=False, description="Whether approval is required"
    )
    approved_users_count: int = Field(default=0, description="Number of approved users")
    approved_groups_count: int = Field(
        default=0, description="Number of approved groups"
    )
    tags_count: int = Field(default=0, description="Number of tags")
    has_sla: bool = Field(default=False, description="Whether SLA is defined")
    has_cost: bool = Field(default=False, description="Whether cost is defined")
    has_usage_limit: bool = Field(
        default=False, description="Whether usage limit is defined"
    )
    age_days: float = Field(default=0.0, description="Age in days since creation")
