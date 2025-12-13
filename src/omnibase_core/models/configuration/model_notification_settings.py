"""
Notification Settings Model.

Notification settings for priority levels.
"""

from pydantic import BaseModel, Field


class ModelNotificationSettings(BaseModel):
    """Notification settings for priority levels."""

    # Email notifications
    email_enabled: bool = Field(default=False, description="Enable email notifications")
    email_recipients: list[str] = Field(
        default_factory=list,
        description="Email recipients",
    )
    email_on_failure: bool = Field(
        default=True, description="Send email on execution failure"
    )
    email_on_completion: bool = Field(
        default=False,
        description="Send email on execution completion",
    )

    # Webhook notifications
    webhook_enabled: bool = Field(
        default=False, description="Enable webhook notifications"
    )
    webhook_url: str | None = Field(
        default=None,
        description="Webhook URL for notifications",
    )
    webhook_headers: dict[str, str] = Field(
        default_factory=dict,
        description="Custom headers for webhook",
    )
    webhook_retry_count: int = Field(
        default=3,
        description="Number of webhook retry attempts",
        ge=0,
        le=5,
    )

    # Slack notifications
    slack_enabled: bool = Field(default=False, description="Enable Slack notifications")
    slack_channel: str | None = Field(
        default=None,
        description="Slack channel for notifications",
    )
    slack_webhook_url: str | None = Field(default=None, description="Slack webhook URL")

    # Notification rules
    min_severity: str = Field(
        default="error",
        description="Minimum severity to trigger notifications",
        pattern="^(debug|info|warning|error|critical)$",
    )
    rate_limit_per_hour: int | None = Field(
        default=None,
        description="Maximum notifications per hour",
        ge=1,
    )
    aggregate_notifications: bool = Field(
        default=True,
        description="Aggregate multiple notifications",
    )
    aggregation_window_minutes: int = Field(
        default=5,
        description="Window for notification aggregation",
        ge=1,
        le=60,
    )
