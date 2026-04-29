# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""TopicBase coverage for cost projection snapshots."""

from __future__ import annotations

import pytest

from omnibase_core.topics import TopicBase, build_topic

pytestmark = pytest.mark.unit


def test_cost_projection_snapshot_topic_values() -> None:
    assert (
        TopicBase.PROJECTION_COST_SUMMARY == "onex.snapshot.projection.cost.summary.v1"
    )
    assert (
        TopicBase.PROJECTION_COST_BY_REPO == "onex.snapshot.projection.cost.by_repo.v1"
    )
    assert (
        TopicBase.PROJECTION_COST_TOKEN_USAGE
        == "onex.snapshot.projection.cost.token_usage.v1"
    )


def test_cost_projection_snapshot_topics_build() -> None:
    assert build_topic(TopicBase.PROJECTION_COST_SUMMARY) == (
        "onex.snapshot.projection.cost.summary.v1"
    )
    assert build_topic(TopicBase.PROJECTION_COST_BY_REPO) == (
        "onex.snapshot.projection.cost.by_repo.v1"
    )
    assert build_topic(TopicBase.PROJECTION_COST_TOKEN_USAGE) == (
        "onex.snapshot.projection.cost.token_usage.v1"
    )
