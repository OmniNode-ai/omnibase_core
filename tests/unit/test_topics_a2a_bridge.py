# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""TopicBase coverage for the A2A delegation bridge topics."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import omnibase_core.topics as topics_mod
from omnibase_core.topics import TopicBase

pytestmark = pytest.mark.unit

_ONEX_TOPIC = re.compile(r"^onex\.(cmd|evt)\.omnibase-infra\.[a-z0-9-]+\.v[1-9]\d*$")


def test_new_members_present() -> None:
    assert TopicBase.INVOCATION_COMMAND.value == (
        "onex.cmd.omnibase-infra.invocation.v1"
    )
    assert TopicBase.REMOTE_AGENT_INVOKE.value == (
        "onex.cmd.omnibase-infra.remote-agent-invoke.v1"
    )
    assert TopicBase.AGENT_TASK_LIFECYCLE.value == (
        "onex.evt.omnibase-infra.agent-task-lifecycle.v1"
    )


def test_new_members_match_onex_topic_regex() -> None:
    for member in (
        TopicBase.INVOCATION_COMMAND,
        TopicBase.REMOTE_AGENT_INVOKE,
        TopicBase.AGENT_TASK_LIFECYCLE,
    ):
        assert _ONEX_TOPIC.match(member.value), member.value


def test_each_topic_string_declared_exactly_once_in_source() -> None:
    src = Path(topics_mod.__file__).read_text()
    for member in (
        "INVOCATION_COMMAND",
        "REMOTE_AGENT_INVOKE",
        "AGENT_TASK_LIFECYCLE",
    ):
        assert src.count(member) == 1, f"{member} declared {src.count(member)} times"
