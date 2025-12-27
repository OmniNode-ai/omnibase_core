"""
ModelExecutionPriority - Flexible execution priority configuration

This model provides business-specific priority management for execution contexts,
supporting priority values, preemption logic, resource allocation, and escalation policies.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from omnibase_core.models.configuration.model_priority_metadata import (
    ModelPriorityMetadata,
)
from omnibase_core.models.configuration.model_resource_allocation import (
    ModelResourceAllocation,
)


class ModelExecutionPriority(BaseModel):
    """
    Flexible execution priority model

    This model replaces hardcoded priority enums with extensible priority
    configuration supporting business-specific priority management, preemption
    logic, resource allocation, and queue escalation policies.
    """

    priority_value: int = Field(
        default=...,
        description="Priority value (higher = more important)",
        ge=0,
        le=100,
    )

    priority_class: str = Field(
        default=...,
        description="Priority class name",
        pattern="^[a-z][a-z0-9_-]*$",
    )

    display_name: str = Field(default=..., description="Human-readable priority name")

    preemptible: bool = Field(
        default=True,
        description="Can be preempted by higher priority",
    )

    resource_allocation: ModelResourceAllocation = Field(
        default=...,
        description="Resource allocation for this priority",
    )

    max_queue_time_ms: int | None = Field(
        default=None,
        description="Maximum time in queue before escalation",
        ge=0,
    )

    escalation_priority: ModelExecutionPriority | None = Field(
        default=None,
        description="Priority to escalate to after timeout",
    )

    metadata: ModelPriorityMetadata | None = Field(
        default=None,
        description="Additional priority metadata",
    )

    def should_preempt(self, other: ModelExecutionPriority) -> bool:
        """
        Check if this priority should preempt another

        Args:
            other: Other priority to compare against

        Returns:
            True if this priority should preempt the other
        """
        return self.priority_value > other.priority_value and other.preemptible

    def can_be_preempted_by(self, other: ModelExecutionPriority) -> bool:
        """
        Check if this priority can be preempted by another

        Args:
            other: Other priority to compare against

        Returns:
            True if this priority can be preempted by the other
        """
        return self.preemptible and other.priority_value > self.priority_value

    def get_effective_priority(self) -> int:
        """
        Get the effective priority value considering escalation

        Returns:
            Effective priority value
        """
        if self.escalation_priority:
            return max(self.priority_value, self.escalation_priority.priority_value)
        return self.priority_value
