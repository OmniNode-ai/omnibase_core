# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import StrEnum


class EnumEventBusAction(StrEnum):
    """Actions the overseer can request from an event bus provider.

    Used in protocol dispatch to messaging integrations (e.g. Kafka/Redpanda).
    """

    PUBLISH = "PUBLISH"
    """Publish a message to a topic."""

    SUBSCRIBE = "SUBSCRIBE"
    """Subscribe a consumer to a topic."""

    UNSUBSCRIBE = "UNSUBSCRIBE"
    """Remove a consumer subscription from a topic."""

    CREATE_TOPIC = "CREATE_TOPIC"
    """Create a new topic with given configuration."""

    DELETE_TOPIC = "DELETE_TOPIC"
    """Delete a topic and its retained messages."""

    LIST_TOPICS = "LIST_TOPICS"
    """List all available topics."""

    GET_OFFSET = "GET_OFFSET"
    """Retrieve the current consumer offset for a topic-partition."""

    SEEK_OFFSET = "SEEK_OFFSET"
    """Set the consumer offset to a specific position."""

    DRAIN = "DRAIN"
    """Consume and discard all pending messages on a topic."""


__all__: list[str] = ["EnumEventBusAction"]
