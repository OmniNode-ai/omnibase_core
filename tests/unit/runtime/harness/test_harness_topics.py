# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Canonical topic bindings for the local runtime harness (OMN-17524)."""

from __future__ import annotations

import pytest

from omnibase_core.runtime.harness.harness_topics import (
    DELEGATION_COMMAND_TOPIC,
    DELEGATION_COMPLETED_TOPIC,
    DELEGATION_INFER_TOPIC,
    SEA_COMMAND_TOPIC,
    SEA_COMPLETED_TOPIC,
    SEA_INFER_TOPIC,
    command_topic,
    completed_topic,
    infer_topic,
)
from omnibase_core.topics import TopicBase

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("workflow", "command", "infer", "completed"),
    [
        (
            "delegation",
            TopicBase.HARNESS_DELEGATION_REQUESTED.value,
            TopicBase.HARNESS_DELEGATION_INFERRED.value,
            TopicBase.HARNESS_DELEGATION_COMPLETED.value,
        ),
        (
            "sea",
            TopicBase.HARNESS_SEA_REQUESTED.value,
            TopicBase.HARNESS_SEA_INFERRED.value,
            TopicBase.HARNESS_SEA_COMPLETED.value,
        ),
    ],
)
def test_harness_topic_wrappers_preserve_canonical_wire_values(
    workflow: str, command: str, infer: str, completed: str
) -> None:
    """Harness wrappers return the canonical registry value for every hop."""
    assert command_topic(workflow) == command
    assert infer_topic(workflow) == infer
    assert completed_topic(workflow) == completed


def test_harness_topic_constants_match_their_wrappers() -> None:
    """Named wrapper constants remain aliases for the canonical registry."""
    assert command_topic("delegation") == DELEGATION_COMMAND_TOPIC
    assert infer_topic("delegation") == DELEGATION_INFER_TOPIC
    assert completed_topic("delegation") == DELEGATION_COMPLETED_TOPIC
    assert command_topic("sea") == SEA_COMMAND_TOPIC
    assert infer_topic("sea") == SEA_INFER_TOPIC
    assert completed_topic("sea") == SEA_COMPLETED_TOPIC
