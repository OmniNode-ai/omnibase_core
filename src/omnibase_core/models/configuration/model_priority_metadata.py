"""ONEX-compatible Priority Metadata Model.

Additional metadata for execution priorities with ONEX compliance and validation.
"""

from datetime import UTC, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.constants.constants_field_limits import MAX_IDENTIFIER_LENGTH
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.configuration.model_monitoring_thresholds import (
    ModelMonitoringThresholds,
)
from omnibase_core.models.configuration.model_notification_settings import (
    ModelNotificationSettings,
)
from omnibase_core.models.configuration.model_priority_metadata_summary import (
    ModelPriorityMetadataSummary,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError

__all__ = ["ModelPriorityMetadata", "ModelPriorityMetadataSummary"]


class ModelPriorityMetadata(BaseModel):
    """ONEX-compatible priority metadata with validation and business logic.

    Additional metadata for execution priorities including:
    - Ownership and approval management
    - SLA requirements and business justification
    - Cost tracking and usage monitoring
    - Notification and alerting thresholds
    """

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    owner: str | None = Field(
        default=None,
        description="Owner or team responsible for this priority level",
        max_length=MAX_IDENTIFIER_LENGTH,
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this priority was created",
    )

    last_modified: datetime | None = Field(
        default=None,
        description="When this priority was last modified",
    )

    tags: list[str] = Field(
        default_factory=list,
        description="Tags associated with this priority",
        max_length=50,
    )

    sla_requirements: str | None = Field(
        default=None,
        description="SLA requirements for this priority level",
        max_length=500,
    )

    business_justification: str | None = Field(
        default=None,
        description="Business justification for this priority level",
        max_length=1000,
    )

    usage_guidelines: str | None = Field(
        default=None,
        description="Guidelines for when to use this priority",
        max_length=1000,
    )

    cost_per_hour: float | None = Field(
        default=None,
        description="Cost per hour for this priority level",
        ge=0,
    )

    max_daily_usage: int | None = Field(
        default=None,
        description="Maximum daily usage allowed",
        ge=0,
    )

    notification_settings: ModelNotificationSettings = Field(
        default_factory=lambda: ModelNotificationSettings(
            email_enabled=False,
            email_on_failure=True,
            email_on_completion=False,
            webhook_enabled=False,
            webhook_url=None,
            webhook_retry_count=3,
            slack_enabled=False,
            slack_channel=None,
            slack_webhook_url=None,
            min_severity="error",
            rate_limit_per_hour=None,
            aggregate_notifications=True,
            aggregation_window_minutes=5,
        ),
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
        default_factory=lambda: ModelMonitoringThresholds(
            max_queue_time_ms=None,
            max_execution_time_ms=None,
            min_response_time_ms=None,
            max_memory_mb=None,
            max_cpu_percent=None,
            max_io_ops_per_second=None,
            max_daily_usage=None,
            max_consecutive_failures=None,
            max_error_rate_percent=None,
            cost_alert_threshold=None,
            alert_on_failure=True,
            alert_on_timeout=True,
            alert_on_degraded_performance=True,
            performance_baseline_factor=2.0,
            max_concurrent_executions=None,
        ),
        description="Monitoring and alerting thresholds",
    )

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Validate tags."""
        if len(v) > 20:
            raise ModelOnexError(
                message="Maximum 20 tags allowed",
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
            )

        for tag in v:
            if len(tag) > 50:
                raise ModelOnexError(
                    message=f"Tag '{tag}' exceeds maximum length of 50",
                    error_code=EnumCoreErrorCode.VALIDATION_FAILED,
                )

        return v

    @field_validator("approved_users")
    @classmethod
    def validate_approved_users(cls, v: list[str]) -> list[str]:
        """Validate approved users."""
        if len(v) > 1000:
            raise ModelOnexError(
                message="Maximum 1000 approved users allowed",
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
            )
        return v

    @field_validator("approved_groups")
    @classmethod
    def validate_approved_groups(cls, v: list[str]) -> list[str]:
        """Validate approved groups."""
        if len(v) > 100:
            raise ModelOnexError(
                message="Maximum 100 approved groups allowed",
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
            )
        return v

    # === User and Group Management ===

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

    def approve_user(self, user: str) -> None:
        """Approve a user for this priority."""
        if user not in self.approved_users:
            self.approved_users.append(user)
            self.update_last_modified()

    def revoke_user_approval(self, user: str) -> None:
        """Revoke user approval for this priority."""
        if user in self.approved_users:
            self.approved_users.remove(user)
            self.update_last_modified()

    def approve_group(self, group: str) -> None:
        """Approve a group for this priority."""
        if group not in self.approved_groups:
            self.approved_groups.append(group)
            self.update_last_modified()

    def revoke_group_approval(self, group: str) -> None:
        """Revoke group approval for this priority."""
        if group in self.approved_groups:
            self.approved_groups.remove(group)
            self.update_last_modified()

    # === Tag Management ===

    def add_tag(self, tag: str) -> None:
        """Add a tag to this priority."""
        if tag not in self.tags:
            if len(self.tags) >= 20:
                raise ModelOnexError(
                    message="Maximum 20 tags allowed",
                    error_code=EnumCoreErrorCode.VALIDATION_FAILED,
                )
            self.tags.append(tag)
            self.update_last_modified()

    def remove_tag(self, tag: str) -> None:
        """Remove a tag from this priority."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.update_last_modified()

    def has_tag(self, tag: str) -> bool:
        """Check if priority has a specific tag."""
        return tag in self.tags

    def get_tags_count(self) -> int:
        """Get count of tags."""
        return len(self.tags)

    # === Cost and Usage Management ===

    def calculate_daily_cost(self, usage_hours: float) -> float:
        """Calculate daily cost based on usage."""
        if self.cost_per_hour is None:
            return 0.0
        return self.cost_per_hour * usage_hours

    def is_usage_within_limit(self, current_usage: int) -> bool:
        """Check if current usage is within the daily limit."""
        if self.max_daily_usage is None:
            return True
        return current_usage <= self.max_daily_usage

    def get_remaining_usage(self, current_usage: int) -> int:
        """Get remaining usage for the day."""
        if self.max_daily_usage is None:
            return -1  # Unlimited
        remaining = self.max_daily_usage - current_usage
        return max(0, remaining)

    # === Timestamp Management ===

    def update_last_modified(self) -> None:
        """Update the last modified timestamp."""
        self.last_modified = datetime.now(UTC)

    def get_age_days(self) -> float:
        """Get age in days since creation."""
        now = datetime.now(UTC)
        age = now - self.created_at
        return age.total_seconds() / (24 * 3600)

    def get_days_since_modified(self) -> float | None:
        """Get days since last modification."""
        if self.last_modified is None:
            return None
        now = datetime.now(UTC)
        age = now - self.last_modified
        return age.total_seconds() / (24 * 3600)

    # === Validation Methods ===

    def validate_for_use(
        self, user: str | None = None, groups: list[str] | None = None
    ) -> bool:
        """Validate if this priority can be used."""
        if groups is None:
            groups = []

        # Check user approval if required
        if self.approval_required and user:
            if not (
                self.is_user_approved(user)
                or any(self.is_group_approved(group) for group in groups)
            ):
                return False

        return True

    def get_validation_errors(
        self, user: str | None = None, groups: list[str] | None = None
    ) -> list[str]:
        """Get validation errors for this priority."""
        errors = []

        if groups is None:
            groups = []

        if self.approval_required:
            if (
                user
                and not self.is_user_approved(user)
                and not any(self.is_group_approved(group) for group in groups)
            ):
                errors.append("User is not approved for this priority level")

        return errors

    # === Factory Methods ===

    @classmethod
    def create_default(cls, owner: str | None = None) -> Self:
        """Factory method for default metadata."""
        return cls(
            owner=owner,
            tags=["default"],
            usage_guidelines="Standard priority metadata",
            sla_requirements=None,
            business_justification=None,
            cost_per_hour=None,
            max_daily_usage=None,
            last_modified=None,
        )

    @classmethod
    def create_high_priority(cls, owner: str, sla: str) -> Self:
        """Factory method for high priority metadata."""
        return cls(
            owner=owner,
            tags=["high-priority", "sla-critical"],
            sla_requirements=sla,
            business_justification="Critical business operations requiring fast execution",
            usage_guidelines="Use for time-sensitive operations with SLA requirements",
            cost_per_hour=None,
            max_daily_usage=None,
            approval_required=True,
            last_modified=None,
            monitoring_thresholds=ModelMonitoringThresholds(
                max_queue_time_ms=10000,
                max_execution_time_ms=60000,
                min_response_time_ms=None,
                max_memory_mb=None,
                max_cpu_percent=None,
                max_io_ops_per_second=None,
                max_daily_usage=None,
                max_consecutive_failures=None,
                max_error_rate_percent=None,
                cost_alert_threshold=None,
                alert_on_failure=True,
                alert_on_timeout=True,
                alert_on_degraded_performance=True,
                performance_baseline_factor=2.0,
                max_concurrent_executions=None,
            ),
        )

    @classmethod
    def create_batch_metadata(cls, owner: str) -> Self:
        """Factory method for batch priority metadata."""
        return cls(
            owner=owner,
            tags=["batch", "background"],
            sla_requirements=None,
            business_justification="Background processing with no time constraints",
            usage_guidelines="Use for bulk operations, data processing, and cleanup tasks",
            cost_per_hour=0.10,  # Low cost for batch processing
            max_daily_usage=None,
            last_modified=None,
            monitoring_thresholds=ModelMonitoringThresholds(
                max_queue_time_ms=None,
                max_execution_time_ms=None,
                min_response_time_ms=None,
                max_memory_mb=None,
                max_cpu_percent=None,
                max_io_ops_per_second=None,
                max_daily_usage=1000,
                max_consecutive_failures=None,
                max_error_rate_percent=None,
                cost_alert_threshold=50.0,
                alert_on_failure=True,
                alert_on_timeout=True,
                alert_on_degraded_performance=True,
                performance_baseline_factor=2.0,
                max_concurrent_executions=None,
            ),
        )

    @classmethod
    def create_development_metadata(cls, owner: str) -> Self:
        """Factory method for development priority metadata."""
        return cls(
            owner=owner,
            tags=["development", "testing"],
            sla_requirements=None,
            business_justification="Development and testing environments",
            usage_guidelines="Use for development builds, testing, and debugging",
            cost_per_hour=0.05,
            max_daily_usage=None,
            approval_required=False,
            last_modified=None,
        )

    @classmethod
    def create_production_metadata(cls, owner: str, sla: str) -> Self:
        """Factory method for production priority metadata."""
        return cls(
            owner=owner,
            tags=["production", "mission-critical"],
            sla_requirements=sla,
            business_justification="Production workloads requiring high reliability",
            usage_guidelines="Use for production deployments and critical operations",
            cost_per_hour=None,
            max_daily_usage=None,
            approval_required=True,
            last_modified=None,
            monitoring_thresholds=ModelMonitoringThresholds(
                max_queue_time_ms=5000,
                max_execution_time_ms=30000,
                min_response_time_ms=None,
                max_memory_mb=None,
                max_cpu_percent=None,
                max_io_ops_per_second=None,
                max_daily_usage=None,
                max_consecutive_failures=None,
                max_error_rate_percent=None,
                cost_alert_threshold=None,
                alert_on_failure=True,
                alert_on_timeout=True,
                alert_on_degraded_performance=True,
                performance_baseline_factor=2.0,
                max_concurrent_executions=None,
            ),
        )

    # === Utility Methods ===

    def get_summary(self) -> "ModelPriorityMetadataSummary":
        """Get a summary of priority metadata."""
        return ModelPriorityMetadataSummary(
            owner=self.owner,
            approval_required=self.approval_required,
            approved_users_count=len(self.approved_users),
            approved_groups_count=len(self.approved_groups),
            tags_count=len(self.tags),
            has_sla=self.sla_requirements is not None,
            has_cost=self.cost_per_hour is not None,
            has_usage_limit=self.max_daily_usage is not None,
            age_days=self.get_age_days(),
        )

    def copy_with_modifications(
        self,
        owner: str | None = None,
        approval_required: bool | None = None,
        cost_per_hour: float | None = None,
        max_daily_usage: int | None = None,
    ) -> Self:
        """Create a copy with specified modifications."""
        data = self.model_dump(exclude={"created_at", "last_modified"})

        if owner is not None:
            data["owner"] = owner
        if approval_required is not None:
            data["approval_required"] = approval_required
        if cost_per_hour is not None:
            data["cost_per_hour"] = cost_per_hour
        if max_daily_usage is not None:
            data["max_daily_usage"] = max_daily_usage

        return self.__class__(**data)
