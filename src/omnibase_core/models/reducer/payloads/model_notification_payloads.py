"""
Notification intent payloads for alerts and messaging.

This module provides typed payloads for notification-related intents:
- ModelPayloadNotify: General notification/alert emission

Design Pattern:
    Reducers emit these payloads when notification side effects are needed.
    The Effect node receives the intent, pattern-matches on the `intent_type`
    discriminator, and sends the notification through the configured channel.

    This separation ensures Reducer purity - the Reducer declares the desired
    outcome without performing the actual side effect.

Notification Integration:
    - ModelPayloadNotify supports multiple channels (email, SMS, Slack, webhook)
    - Supports priority levels for alerting systems
    - Includes recipient targeting and content templating

Thread Safety:
    All payloads are immutable (frozen=True) after creation, making them
    thread-safe for concurrent read access.

Example:
    >>> from omnibase_core.models.reducer.payloads import ModelPayloadNotify
    >>>
    >>> # Notification payload
    >>> notify_payload = ModelPayloadNotify(
    ...     channel="slack",
    ...     recipients=["#engineering-alerts"],
    ...     subject="Build Failed",
    ...     body="Build #1234 failed in production pipeline",
    ...     priority="high",
    ... )

See Also:
    omnibase_core.models.reducer.payloads.ModelIntentPayloadBase: Base class
    omnibase_core.models.reducer.payloads.model_protocol_intent_payload: Protocol for intent payloads
"""

from typing import Literal
from uuid import UUID

from pydantic import Field

from omnibase_core.models.reducer.payloads.model_intent_payload_base import (
    ModelIntentPayloadBase,
)

# Public API - listed immediately after imports per Python convention
__all__ = ["ModelPayloadNotify"]


class ModelPayloadNotify(ModelIntentPayloadBase):
    """Payload for notification/alert intents.

    Emitted by Reducers when a notification should be sent to users or systems.
    The Effect node executes this intent by sending the notification through
    the configured channel (email, SMS, Slack, PagerDuty, etc.).

    Supports multiple channels, priority levels, and rich content formatting.

    Attributes:
        intent_type: Discriminator literal for intent routing. Always "notify".
            Placed first for optimal union type resolution performance.
        channel: Notification channel (email, sms, slack, pagerduty, webhook).
        recipients: List of recipients (email addresses, phone numbers, channel IDs).
        subject: Notification subject/title. Used as email subject or alert title.
        body: Notification body content. Supports plain text or markdown.
        priority: Priority level for the notification.
        template_id: Optional template ID for templated notifications.
        template_vars: Variables to substitute in the template.
        metadata: Additional metadata for the notification.

    Example:
        >>> payload = ModelPayloadNotify(
        ...     channel="email",
        ...     recipients=["admin@example.com", "oncall@example.com"],
        ...     subject="Critical: Database Connection Pool Exhausted",
        ...     body="Connection pool at 98% capacity. Consider scaling up.",
        ...     priority="critical",
        ...     metadata={"service": "api-gateway", "env": "production"},
        ... )
    """

    # NOTE: Discriminator field is placed FIRST for optimal union type resolution.
    intent_type: Literal["notify"] = Field(
        default="notify",
        description=(
            "Discriminator literal for intent routing. Used by Pydantic's "
            "discriminated union to dispatch to the correct Effect handler."
        ),
    )

    channel: Literal["email", "sms", "slack", "pagerduty", "webhook", "teams"] = Field(
        ...,
        description=(
            "Notification channel to use. Each channel has its own delivery "
            "mechanism and recipient format."
        ),
    )

    recipients: list[str] = Field(
        ...,
        description=(
            "List of recipients. Format depends on channel: email addresses for "
            "email, phone numbers for SMS, channel IDs for Slack, etc."
        ),
        min_length=1,
    )

    subject: str = Field(
        ...,
        description=(
            "Notification subject or title. Used as email subject line, "
            "alert title, or message header."
        ),
        min_length=1,
        max_length=256,
    )

    body: str = Field(
        ...,
        description=(
            "Notification body content. Supports plain text. Some channels "
            "(Slack, email) may support markdown or HTML formatting."
        ),
        min_length=1,
        max_length=16384,
    )

    priority: Literal["low", "normal", "high", "critical"] = Field(
        default="normal",
        description=(
            "Priority level for the notification. Critical triggers immediate "
            "escalation in alerting systems. High is urgent but not page-worthy."
        ),
    )

    template_id: UUID | None = Field(
        default=None,
        description=(
            "Optional template ID for templated notifications. If provided, "
            "the body may be ignored in favor of the template."
        ),
    )

    template_vars: dict[str, object] = Field(
        default_factory=dict,
        description=(
            "Variables to substitute in the template. Keys are variable names, "
            "values are the substitution values."
        ),
    )

    metadata: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Additional metadata for the notification. Common keys: 'service', "
            "'env', 'correlation_id', 'alert_id'."
        ),
    )
