"""
Priority Metadata Model.

Additional metadata for execution priorities.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.models.configuration.model_monitoring_thresholds import (
    ModelMonitoringThresholds,
)
from omnibase_core.models.configuration.model_notification_settings import (
    ModelNotificationSettings,
)


class ModelPriorityMetadata(BaseModel):
    """Additional metadata for execution priorities."""

    owner: str | None = Field(
        None,
        description="Owner or team responsible for this priority level",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this priority was created",
    )
    last_modified: datetime | None = Field(
        None,
        description="When this priority was last modified",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags associated with this priority",
    )
    sla_requirements: str | None = Field(
        None,
        description="SLA requirements for this priority level",
    )
    business_justification: str | None = Field(
        None,
        description="Business justification for this priority level",
    )
    usage_guidelines: str | None = Field(
        None,
        description="Guidelines for when to use this priority",
    )
    cost_per_hour: float | None = Field(
        None,
        description="Cost per hour for this priority level",
        ge=0,
    )
    max_daily_usage: int | None = Field(
        None,
        description="Maximum daily usage allowed",
        ge=0,
    )
    notification_settings: ModelNotificationSettings = Field(
        default_factory=lambda: ModelNotificationSettings(),
        description="Notification settings for this priority",
    )
    approval_required: bool = Field(
        default=False,
        description="Whether approval is required to use this priority",
    )
    approved_users: list[str] = Field(
        default_factory=list,
        description="Users approved to use this priority level",
    )
    approved_groups: list[str] = Field(
        default_factory=list,
        description="Groups approved to use this priority level",
    )
    monitoring_thresholds: ModelMonitoringThresholds = Field(
        default_factory=lambda: ModelMonitoringThresholds(),
        description="Monitoring and alerting thresholds",
    )

    def is_user_approved(self, user: str) -> bool:
        """Check if user is approved to use this priority."""
        if not self.approval_required:
            return True
        return user in self.approved_users

    def is_group_approved(self, group: str) -> bool:
        """Check if group is approved to use this priority."""
        if not self.approval_required:
            return True
        return group in self.approved_groups

    def add_tag(self, tag: str) -> None:
        """Add a tag to this priority."""
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag from this priority."""
        if tag in self.tags:
            self.tags.remove(tag)

    def has_tag(self, tag: str) -> bool:
        """Check if priority has a specific tag."""
        return tag in self.tags

    def update_last_modified(self) -> None:
        """Update the last modified timestamp."""
        self.last_modified = datetime.utcnow()

    @classmethod
    def create_default(cls, owner: str | None = None) -> "ModelPriorityMetadata":
        """Factory method for default metadata."""
        return cls(
            owner=owner,
            tags=["default"],
            usage_guidelines="Standard priority metadata",
        )

    @classmethod
    def create_high_priority(cls, owner: str, sla: str) -> "ModelPriorityMetadata":
        """Factory method for high priority metadata."""
        return cls(
            owner=owner,
            tags=["high-priority", "sla-critical"],
            sla_requirements=sla,
            business_justification="Critical business operations requiring fast execution",
            usage_guidelines="Use for time-sensitive operations with SLA requirements",
            approval_required=True,
            monitoring_thresholds=ModelMonitoringThresholds(
                max_queue_time_ms=10000,
                max_execution_time_ms=60000,
                alert_on_failure=True,
            ),
        )

    @classmethod
    def create_batch_metadata(cls, owner: str) -> "ModelPriorityMetadata":
        """Factory method for batch priority metadata."""
        return cls(
            owner=owner,
            tags=["batch", "background"],
            business_justification="Background processing with no time constraints",
            usage_guidelines="Use for bulk operations, data processing, and cleanup tasks",
            cost_per_hour=0.10,  # Low cost for batch processing
            monitoring_thresholds=ModelMonitoringThresholds(
                max_daily_usage=1000,
                cost_alert_threshold=50.0,
            ),
        )
