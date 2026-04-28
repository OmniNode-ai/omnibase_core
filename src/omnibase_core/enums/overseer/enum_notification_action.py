# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import StrEnum


class EnumNotificationAction(StrEnum):
    """Actions the overseer can request from a notification provider.

    Used in protocol dispatch to alerting/messaging integrations
    (e.g. Slack, PagerDuty, email).
    """

    SEND = "SEND"
    """Send a notification message to a target."""

    SEND_ALERT = "SEND_ALERT"
    """Send a high-priority alert requiring acknowledgement."""

    ACKNOWLEDGE = "ACKNOWLEDGE"
    """Acknowledge a pending alert."""

    RESOLVE = "RESOLVE"
    """Mark an alert or incident as resolved."""

    LIST_CHANNELS = "LIST_CHANNELS"
    """List available notification channels or targets."""

    GET_STATUS = "GET_STATUS"
    """Retrieve delivery status of a previously sent notification."""


__all__: list[str] = ["EnumNotificationAction"]
