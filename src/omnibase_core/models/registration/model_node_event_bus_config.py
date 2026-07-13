# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Node Event Bus Configuration Model.

The model for a node's resolved event bus configuration,
containing lists of topics the node subscribes to and publishes to.

Key Design Decisions:
    1. Topics stored as realm-agnostic strings (e.g., "onex.evt.intent-classified.v1")  # onex-topic-allow: pending contract auto-wiring
    2. Metadata fields are tooling-only; routing uses ONLY topic strings
    3. Property methods extract topic strings only for routing lookups
    4. Model is frozen (immutable) with extra="forbid" for safety

Example:
    >>> from omnibase_core.models.registration import (
    ...     ModelEventBusTopicEntry,
    ...     ModelNodeEventBusConfig,
    ... )
    >>> entry = ModelEventBusTopicEntry(
    ...     topic="onex.evt.intent-classified.v1",  # onex-topic-allow: pending contract auto-wiring
    ...     event_type="ModelIntentClassified",
    ... )
    >>> config = ModelNodeEventBusConfig(subscribe_topics=[entry])
    >>> config.subscribe_topic_strings
    ['onex.evt.intent-classified.v1']  # onex-topic-allow: pending contract auto-wiring
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.registration.model_event_bus_topic_entry import (
    ModelEventBusTopicEntry,
)


class ModelNodeEventBusConfig(BaseModel):
    """Resolved event bus configuration for registry storage.

    This model holds the resolved, realm-agnostic topic strings
    that a node subscribes to and publishes to. It is designed for
    storage in the registry to enable dynamic topic-based routing.

    The property methods (subscribe_topic_strings, publish_topic_strings)
    extract only the topic strings for routing lookups, ignoring all
    metadata fields.

    Attributes:
        subscribe_topics: List of topics the node subscribes to.
        publish_topics: List of topics the node publishes to.

    Example:
        >>> config = ModelNodeEventBusConfig(
        ...     subscribe_topics=[
        ...         ModelEventBusTopicEntry(topic="onex.evt.input.v1"),  # onex-topic-allow: pending contract auto-wiring
        ...     ],
        ...     publish_topics=[
        ...         ModelEventBusTopicEntry(topic="onex.evt.output.v1"),  # onex-topic-allow: pending contract auto-wiring
        ...     ],
        ... )
        >>> config.subscribe_topic_strings
        ['onex.evt.input.v1']  # onex-topic-allow: pending contract auto-wiring
        >>> config.publish_topic_strings
        ['onex.evt.output.v1']  # onex-topic-allow: pending contract auto-wiring
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    subscribe_topics: list[ModelEventBusTopicEntry] = Field(
        default_factory=list,
        description="List of topics the node subscribes to.",
    )
    publish_topics: list[ModelEventBusTopicEntry] = Field(
        default_factory=list,
        description="List of topics the node publishes to.",
    )

    @property
    def subscribe_topic_strings(self) -> list[str]:
        """Extract topic strings only, for routing lookups.

        Returns:
            List of realm-agnostic topic strings from subscribe_topics.
            Metadata fields are ignored.
        """
        return [entry.topic for entry in self.subscribe_topics]

    @property
    def publish_topic_strings(self) -> list[str]:
        """Extract topic strings only, for routing lookups.

        Returns:
            List of realm-agnostic topic strings from publish_topics.
            Metadata fields are ignored.
        """
        return [entry.topic for entry in self.publish_topics]


__all__ = ["ModelEventBusTopicEntry", "ModelNodeEventBusConfig"]
