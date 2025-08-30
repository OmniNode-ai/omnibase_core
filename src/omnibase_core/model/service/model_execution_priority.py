"""
ModelExecutionPriority - Flexible execution priority configuration

This model provides business-specific priority management for execution contexts,
supporting priority values, preemption logic, resource allocation, and escalation policies.
"""

from typing import Optional

from pydantic import BaseModel, Field

from omnibase_core.model.configuration.model_priority_metadata import \
    ModelPriorityMetadata
from omnibase_core.model.configuration.model_resource_allocation import \
    ModelResourceAllocation


class ModelExecutionPriority(BaseModel):
    """
    Flexible execution priority model

    This model replaces hardcoded priority enums with extensible priority
    configuration supporting business-specific priority management, preemption
    logic, resource allocation, and queue escalation policies.
    """

    priority_value: int = Field(
        ..., description="Priority value (higher = more important)", ge=0, le=100
    )

    priority_class: str = Field(
        ..., description="Priority class name", pattern="^[a-z][a-z0-9_-]*$"
    )

    display_name: str = Field(..., description="Human-readable priority name")

    preemptible: bool = Field(
        default=True, description="Can be preempted by higher priority"
    )

    resource_allocation: ModelResourceAllocation = Field(
        ..., description="Resource allocation for this priority"
    )

    max_queue_time_ms: Optional[int] = Field(
        None, description="Maximum time in queue before escalation", ge=0
    )

    escalation_priority: Optional["ModelExecutionPriority"] = Field(
        None, description="Priority to escalate to after timeout"
    )

    metadata: Optional[ModelPriorityMetadata] = Field(
        None, description="Additional priority metadata"
    )

    def should_preempt(self, other: "ModelExecutionPriority") -> bool:
        """
        Check if this priority should preempt another

        Args:
            other: Other priority to compare against

        Returns:
            True if this priority should preempt the other
        """
        return self.priority_value > other.priority_value and other.preemptible

    def can_be_preempted_by(self, other: "ModelExecutionPriority") -> bool:
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

    @classmethod
    def create_realtime(cls) -> "ModelExecutionPriority":
        """Create realtime priority (highest priority, non-preemptible)"""
        from omnibase_core.model.configuration.model_priority_metadata import \
            ModelPriorityMetadata
        from omnibase_core.model.configuration.model_resource_allocation import \
            ModelResourceAllocation

        return cls(
            priority_value=100,
            priority_class="realtime",
            display_name="Realtime",
            preemptible=False,
            resource_allocation=ModelResourceAllocation.create_dedicated(),
            max_queue_time_ms=100,  # 100ms max queue time
            metadata=ModelPriorityMetadata.create_realtime(),
        )

    @classmethod
    def create_high(cls) -> "ModelExecutionPriority":
        """Create high priority"""
        from omnibase_core.model.configuration.model_priority_metadata import \
            ModelPriorityMetadata
        from omnibase_core.model.configuration.model_resource_allocation import \
            ModelResourceAllocation

        return cls(
            priority_value=80,
            priority_class="high",
            display_name="High Priority",
            preemptible=True,
            resource_allocation=ModelResourceAllocation.create_high(),
            max_queue_time_ms=1000,  # 1 second max queue time
            metadata=ModelPriorityMetadata.create_high(),
        )

    @classmethod
    def create_normal(cls) -> "ModelExecutionPriority":
        """Create normal priority"""
        from omnibase_core.model.configuration.model_priority_metadata import \
            ModelPriorityMetadata
        from omnibase_core.model.configuration.model_resource_allocation import \
            ModelResourceAllocation

        return cls(
            priority_value=50,
            priority_class="normal",
            display_name="Normal Priority",
            preemptible=True,
            resource_allocation=ModelResourceAllocation.create_normal(),
            max_queue_time_ms=5000,  # 5 seconds max queue time
            metadata=ModelPriorityMetadata.create_normal(),
        )

    @classmethod
    def create_low(cls) -> "ModelExecutionPriority":
        """Create low priority"""
        from omnibase_core.model.configuration.model_priority_metadata import \
            ModelPriorityMetadata
        from omnibase_core.model.configuration.model_resource_allocation import \
            ModelResourceAllocation

        return cls(
            priority_value=20,
            priority_class="low",
            display_name="Low Priority",
            preemptible=True,
            resource_allocation=ModelResourceAllocation.create_low(),
            max_queue_time_ms=30000,  # 30 seconds max queue time
            metadata=ModelPriorityMetadata.create_low(),
        )

    @classmethod
    def create_batch(cls) -> "ModelExecutionPriority":
        """Create batch priority (lowest priority, always preemptible)"""
        from omnibase_core.model.configuration.model_priority_metadata import \
            ModelPriorityMetadata
        from omnibase_core.model.configuration.model_resource_allocation import \
            ModelResourceAllocation

        return cls(
            priority_value=10,
            priority_class="batch",
            display_name="Batch Processing",
            preemptible=True,
            resource_allocation=ModelResourceAllocation.create_batch(),
            max_queue_time_ms=None,  # No queue time limit for batch
            metadata=ModelPriorityMetadata.create_batch(),
        )

    @classmethod
    def create_custom(
        cls, priority_value: int, priority_class: str, display_name: str
    ) -> "ModelExecutionPriority":
        """
        Create custom priority

        Args:
            priority_value: Custom priority value (0-100)
            priority_class: Custom priority class name
            display_name: Human-readable name

        Returns:
            Custom execution priority
        """
        from omnibase_core.model.configuration.model_priority_metadata import \
            ModelPriorityMetadata
        from omnibase_core.model.configuration.model_resource_allocation import \
            ModelResourceAllocation

        return cls(
            priority_value=priority_value,
            priority_class=priority_class,
            display_name=display_name,
            preemptible=True,
            resource_allocation=ModelResourceAllocation.create_custom(priority_value),
            max_queue_time_ms=max(
                1000, (100 - priority_value) * 100
            ),  # Scale with priority
            metadata=ModelPriorityMetadata.create_custom(priority_class),
        )
