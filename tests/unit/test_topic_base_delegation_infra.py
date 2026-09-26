# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""TopicBase coverage for omnibase-infra delegation inference pipeline topics (OMN-12663).

Blocker 1 fix: TopicBase was missing the four omnibase-infra-namespace delegation
topics used by the live runtime (confirmed by D3 trace in OMN-12642).
"""

from __future__ import annotations

import pytest

from omnibase_core.runtime.runtime_fanout_resolver import derive_event_type_from_topic
from omnibase_core.topics import TopicBase, build_topic

pytestmark = pytest.mark.unit


def test_delegation_completed_infra_topic_value() -> None:
    assert (
        TopicBase.DELEGATION_COMPLETED_INFRA
        == "onex.evt.omnibase-infra.delegation-completed.v1"
    )


def test_delegation_failed_infra_topic_value() -> None:
    assert (
        TopicBase.DELEGATION_FAILED_INFRA
        == "onex.evt.omnibase-infra.delegation-failed.v1"
    )


def test_delegation_terminal_v2_infra_topic_values() -> None:
    assert (
        TopicBase.DELEGATION_COMPLETED_INFRA_V2
        == "onex.evt.omnibase-infra.delegation-completed.v2"
    )
    assert (
        TopicBase.DELEGATION_FAILED_ROUTED_INFRA_V2
        == "onex.evt.omnibase-infra.delegation-failed-routed.v2"
    )
    assert (
        TopicBase.DELEGATION_FAILED_UNROUTED_INFRA_V2
        == "onex.evt.omnibase-infra.delegation-failed-unrouted.v2"
    )


def test_all_delegation_terminal_topics_have_canonical_event_types() -> None:
    expected_event_types = {
        TopicBase.DELEGATION_COMPLETED_INFRA: "omnibase-infra.delegation-completed",
        TopicBase.DELEGATION_FAILED_INFRA: "omnibase-infra.delegation-failed",
        TopicBase.DELEGATION_COMPLETED_INFRA_V2: "omnibase-infra.delegation-completed",
        TopicBase.DELEGATION_FAILED_ROUTED_INFRA_V2: "omnibase-infra.delegation-failed-routed",
        TopicBase.DELEGATION_FAILED_UNROUTED_INFRA_V2: "omnibase-infra.delegation-failed-unrouted",
    }

    assert {
        topic: derive_event_type_from_topic(topic) for topic in expected_event_types
    } == expected_event_types


def test_delegation_inference_request_topic_value() -> None:
    assert (
        TopicBase.DELEGATION_INFERENCE_REQUEST
        == "onex.cmd.omnibase-infra.delegation-inference-request.v1"
    )


def test_delegation_inference_response_topic_value() -> None:
    assert (
        TopicBase.DELEGATION_INFERENCE_RESPONSE
        == "onex.evt.omnibase-infra.inference-response.v1"
    )


def test_delegation_infra_topics_pass_canonical_validation() -> None:
    """All four new topics must satisfy the canonical ONEX topic format check."""
    new_topics = [
        TopicBase.DELEGATION_COMPLETED_INFRA,
        TopicBase.DELEGATION_FAILED_INFRA,
        TopicBase.DELEGATION_COMPLETED_INFRA_V2,
        TopicBase.DELEGATION_FAILED_ROUTED_INFRA_V2,
        TopicBase.DELEGATION_FAILED_UNROUTED_INFRA_V2,
        TopicBase.DELEGATION_INFERENCE_REQUEST,
        TopicBase.DELEGATION_INFERENCE_RESPONSE,
    ]
    for topic in new_topics:
        result = build_topic(topic)
        assert result == topic, f"build_topic round-trip failed for {topic!r}"


def test_delegation_infra_topics_are_str_enum_members() -> None:
    """Each new topic must be a member of TopicBase (StrEnum)."""
    assert (
        "onex.evt.omnibase-infra.delegation-completed.v1"
        in TopicBase._value2member_map_
    )
    assert (
        "onex.evt.omnibase-infra.delegation-failed.v1" in TopicBase._value2member_map_
    )
    assert (
        "onex.evt.omnibase-infra.delegation-completed.v2"
        in TopicBase._value2member_map_
    )
    assert (
        "onex.evt.omnibase-infra.delegation-failed-routed.v2"
        in TopicBase._value2member_map_
    )
    assert (
        "onex.evt.omnibase-infra.delegation-failed-unrouted.v2"
        in TopicBase._value2member_map_
    )
    assert (
        "onex.cmd.omnibase-infra.delegation-inference-request.v1"
        in TopicBase._value2member_map_
    )
    assert (
        "onex.evt.omnibase-infra.inference-response.v1" in TopicBase._value2member_map_
    )
