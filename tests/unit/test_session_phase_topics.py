# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit tests for session phase Kafka topics in TopicBase (OMN-11228)."""

from __future__ import annotations

import re

import pytest

from omnibase_core.topics import TopicBase

pytestmark = pytest.mark.unit


def test_session_phase_topics_exist() -> None:
    assert hasattr(TopicBase, "SESSION_PHASE_EVALUATED")
    assert hasattr(TopicBase, "SESSION_PHASE_TRANSITION")
    assert hasattr(TopicBase, "SESSION_PHASE_STATE")
    assert hasattr(TopicBase, "SESSION_PHASE_BUDGET_WARNING")
    assert hasattr(TopicBase, "SESSION_HALT_REQUIRED")


def test_session_phase_topics_values() -> None:
    assert (
        TopicBase.SESSION_PHASE_EVALUATED.value
        == "onex.evt.omnimarket.session-phase-evaluated.v1"
    )
    assert (
        TopicBase.SESSION_PHASE_TRANSITION.value
        == "onex.cmd.omnimarket.session-phase-transition.v1"
    )
    assert (
        TopicBase.SESSION_PHASE_STATE.value
        == "onex.evt.omnimarket.session-phase-state.v1"
    )
    assert (
        TopicBase.SESSION_PHASE_BUDGET_WARNING.value
        == "onex.evt.omnimarket.session-phase-budget-warning.v1"
    )
    assert (
        TopicBase.SESSION_HALT_REQUIRED.value
        == "onex.cmd.omnimarket.session-halt-required.v1"
    )


def test_session_phase_topic_naming_convention() -> None:
    pattern = r"^onex\.(cmd|evt)\.omnimarket\.[a-z0-9-]+\.v\d+$"
    for topic in (
        TopicBase.SESSION_PHASE_EVALUATED,
        TopicBase.SESSION_PHASE_TRANSITION,
        TopicBase.SESSION_PHASE_STATE,
        TopicBase.SESSION_PHASE_BUDGET_WARNING,
        TopicBase.SESSION_HALT_REQUIRED,
    ):
        assert re.match(pattern, topic.value), (
            f"Topic {topic.name} does not follow expected format: {topic.value}"
        )


def test_session_phase_transition_and_halt_are_commands() -> None:
    assert ".cmd." in TopicBase.SESSION_PHASE_TRANSITION.value
    assert ".cmd." in TopicBase.SESSION_HALT_REQUIRED.value


def test_session_phase_evaluated_state_warning_are_events() -> None:
    assert ".evt." in TopicBase.SESSION_PHASE_EVALUATED.value
    assert ".evt." in TopicBase.SESSION_PHASE_STATE.value
    assert ".evt." in TopicBase.SESSION_PHASE_BUDGET_WARNING.value
