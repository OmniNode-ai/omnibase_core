# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit tests for node generation Kafka topics in TopicBase (OMN-11088)."""

from __future__ import annotations

import re

from omnibase_core.topics import TopicBase


def test_node_generation_topics_exist() -> None:
    assert hasattr(TopicBase, "NODE_GENERATION_REQUESTED")
    assert hasattr(TopicBase, "NODE_GENERATION_COMPLETED")
    assert hasattr(TopicBase, "NODE_GENERATION_FAILED")


def test_topic_values_correct() -> None:
    assert (
        TopicBase.NODE_GENERATION_REQUESTED.value
        == "onex.cmd.omnimarket.node-generation-requested.v1"
    )
    assert (
        TopicBase.NODE_GENERATION_COMPLETED.value
        == "onex.evt.omnimarket.node-generation-completed.v1"
    )
    assert (
        TopicBase.NODE_GENERATION_FAILED.value
        == "onex.evt.omnimarket.node-generation-failed.v1"
    )


def test_topic_naming_convention() -> None:
    """Topics must follow onex.{cmd|evt}.{service}.{event-name}.v{N} format."""
    pattern = r"^onex\.(cmd|evt)\.\w+\.[a-z0-9-]+\.v\d+$"
    assert re.match(pattern, TopicBase.NODE_GENERATION_REQUESTED.value)
    assert re.match(pattern, TopicBase.NODE_GENERATION_COMPLETED.value)
    assert re.match(pattern, TopicBase.NODE_GENERATION_FAILED.value)


def test_requested_is_command_topic() -> None:
    assert ".cmd." in TopicBase.NODE_GENERATION_REQUESTED.value


def test_completed_and_failed_are_event_topics() -> None:
    assert ".evt." in TopicBase.NODE_GENERATION_COMPLETED.value
    assert ".evt." in TopicBase.NODE_GENERATION_FAILED.value
