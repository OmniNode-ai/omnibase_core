# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit tests for omnibase_core.topics (canonical home post-OMN-9335).

Covers TopicBase enum values, build_topic() happy + invalid paths, and
build_agent_inbox_directed_topic. Mirrors the omniclaude/tests/hooks/test_topics.py
suite to ensure parity after the move from omniclaude.hooks.topics.
"""

from __future__ import annotations

import re

import pytest

from omnibase_core.models.errors import ModelOnexError
from omnibase_core.topics import (
    AGENT_INBOX_DIRECTED_BASE,
    TopicBase,
    build_agent_inbox_directed_topic,
    build_topic,
)

pytestmark = pytest.mark.unit


class TestTopicBase:
    def test_canonical_names(self) -> None:
        assert TopicBase.SESSION_STARTED == "onex.evt.omniclaude.session-started.v1"
        assert TopicBase.PROMPT_SUBMITTED == "onex.evt.omniclaude.prompt-submitted.v1"
        assert TopicBase.ROUTING_REQUESTED == "onex.cmd.omninode.routing-requested.v1"
        assert (
            TopicBase.CLAUDE_HOOK_EVENT
            == "onex.cmd.omniintelligence.claude-hook-event.v1"
        )

    def test_is_str_enum(self) -> None:
        for topic in TopicBase:
            assert isinstance(topic, str)
            assert isinstance(topic.value, str)

    def test_all_topics_match_onex_format(self) -> None:
        """Every TopicBase value matches onex.{kind}.{producer}.{event}.v{n}."""
        pattern = re.compile(
            r"^onex\.(cmd|evt|dlq|intent|snapshot)\.[a-z][a-z0-9-]*\.[a-z-]+\.v\d+$"
        )
        for topic in TopicBase:
            assert pattern.match(topic.value), (
                f"Topic {topic.name} does not follow ONEX canonical format: "
                f"{topic.value}"
            )


class TestBuildTopicValidInputs:
    def test_build_topic_returns_canonical_name(self) -> None:
        assert (
            build_topic(TopicBase.SESSION_STARTED)
            == "onex.evt.omniclaude.session-started.v1"
        )

    def test_build_topic_all_topic_bases_roundtrip(self) -> None:
        for base in TopicBase:
            assert build_topic(base) == base.value


class TestBuildTopicInvalidBase:
    def test_empty_base_raises(self) -> None:
        with pytest.raises(ModelOnexError, match="base must be a non-empty string"):
            build_topic("")

    def test_none_base_raises(self) -> None:
        with pytest.raises(ModelOnexError, match="base must not be None"):
            build_topic(None)  # type: ignore[arg-type]

    def test_whitespace_base_raises(self) -> None:
        with pytest.raises(ModelOnexError, match="base must be a non-empty string"):
            build_topic("   ")

    def test_int_base_raises(self) -> None:
        with pytest.raises(ModelOnexError, match="base must be a string, got int"):
            build_topic(123)  # type: ignore[arg-type]


class TestBuildTopicMalformed:
    def test_leading_dot_rejected(self) -> None:
        with pytest.raises(ModelOnexError, match="must not start with a dot"):
            build_topic(".omniclaude.test.v1")

    def test_trailing_dot_rejected(self) -> None:
        with pytest.raises(ModelOnexError, match="must not end with a dot"):
            build_topic("omniclaude.test.v1.")

    def test_consecutive_dots_rejected(self) -> None:
        with pytest.raises(ModelOnexError, match="consecutive dots"):
            build_topic("omniclaude..test.v1")

    def test_special_characters_rejected(self) -> None:
        with pytest.raises(ModelOnexError, match="invalid characters"):
            build_topic("omniclaude.test#v1")


class TestAgentInboxDirectedTopic:
    def test_base_prefix_is_stable(self) -> None:
        assert AGENT_INBOX_DIRECTED_BASE == "onex.evt.omniclaude.agent-inbox"

    def test_builds_per_agent_topic(self) -> None:
        assert (
            build_agent_inbox_directed_topic("agent-001")
            == "onex.evt.omniclaude.agent-inbox.agent-001.v1"
        )

    def test_rejects_empty_agent_id(self) -> None:
        with pytest.raises(ModelOnexError, match="agent_id must be a non-empty string"):
            build_agent_inbox_directed_topic("")

    def test_rejects_none_agent_id(self) -> None:
        with pytest.raises(ModelOnexError, match="agent_id must not be None"):
            build_agent_inbox_directed_topic(None)  # type: ignore[arg-type]

    def test_rejects_dotted_agent_id(self) -> None:
        with pytest.raises(ModelOnexError, match="single valid topic segment"):
            build_agent_inbox_directed_topic("agent.001")

    def test_rejects_agent_id_with_hash(self) -> None:
        with pytest.raises(ModelOnexError, match="single valid topic segment"):
            build_agent_inbox_directed_topic("agent#1")


class TestBuildTopicCanonicalEnforcement:
    def test_non_canonical_short_name_rejected(self) -> None:
        with pytest.raises(ModelOnexError, match="canonical ONEX format"):
            build_topic("abc")

    def test_non_canonical_two_segment_rejected(self) -> None:
        with pytest.raises(ModelOnexError, match="canonical ONEX format"):
            build_topic("foo.bar")

    def test_non_canonical_missing_version_rejected(self) -> None:
        with pytest.raises(ModelOnexError, match="canonical ONEX format"):
            build_topic("onex.evt.omniclaude.session-started")
