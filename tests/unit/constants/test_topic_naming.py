# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for topic naming convention enforcement (OMN-2813).

Validates that all TOPIC_* constants in constants_event_types.py follow the
canonical 5-segment format: onex.{kind}.{producer}.{event}.v{n}
"""

import re

import pytest

from omnibase_core.constants import constants_event_types

# Canonical topic pattern: onex.{kind}.{producer}.{event-name}.v{n}
# - kind: cmd | evt | dlq | intent | snapshot
# - producer: lowercase alphanumeric with hyphens (e.g., "platform", "omniclaude")
# - event-name: lowercase alphanumeric with hyphens
# - version: v followed by one or more digits
_TOPIC_PATTERN = re.compile(
    r"^onex\.(cmd|evt|dlq|intent|snapshot)\.[a-z][a-z0-9-]*\.[a-z][a-z0-9-]*\.v\d+$"
)


def _collect_topic_constants() -> list[tuple[str, str]]:
    """Collect all TOPIC_* constants from constants_event_types that look like topic strings.

    Returns a list of (constant_name, value) tuples for constants whose values
    start with 'onex.' (i.e., full topic names, not short event type identifiers).
    """
    results = []
    for name in dir(constants_event_types):
        if not name.startswith("TOPIC_"):
            continue
        value = getattr(constants_event_types, name)
        if not isinstance(value, str):
            continue
        # Only check full topic names (start with "onex.")
        if not value.startswith("onex."):
            continue
        results.append((name, value))
    return results


@pytest.mark.unit
class TestTopicNamingConvention:
    """Validate all topic constants follow the 5-segment naming convention."""

    def test_at_least_three_topic_constants_exist(self) -> None:
        """Ensure we have at least the 3 workflow automation topic constants."""
        topics = _collect_topic_constants()
        assert len(topics) >= 3, (
            f"Expected at least 3 TOPIC_* constants with onex. prefix, found {len(topics)}"
        )

    @pytest.mark.parametrize(
        ("name", "value"),
        _collect_topic_constants(),
        ids=[name for name, _ in _collect_topic_constants()],
    )
    def test_topic_follows_five_segment_format(self, name: str, value: str) -> None:
        """Each TOPIC_* constant must match onex.{kind}.{producer}.{event}.v{n}."""
        segments = value.split(".")
        assert len(segments) == 5, (
            f"{name} = '{value}' has {len(segments)} segments, expected 5 "
            f"(onex.{{kind}}.{{producer}}.{{event}}.v{{n}})"
        )
        assert _TOPIC_PATTERN.match(value), (
            f"{name} = '{value}' does not match the canonical topic pattern "
            f"onex.{{kind}}.{{producer}}.{{event}}.v{{n}}"
        )

    def test_git_hook_topic_normalized(self) -> None:
        """TOPIC_GIT_HOOK_EVENT uses 'platform' as producer segment."""
        assert (
            constants_event_types.TOPIC_GIT_HOOK_EVENT
            == "onex.evt.platform.git-hook.v1"
        )

    def test_github_pr_status_topic_normalized(self) -> None:
        """TOPIC_GITHUB_PR_STATUS_EVENT uses 'platform' as producer segment."""
        assert (
            constants_event_types.TOPIC_GITHUB_PR_STATUS_EVENT
            == "onex.evt.platform.github-pr-status.v1"
        )

    def test_linear_snapshot_topic_normalized(self) -> None:
        """TOPIC_LINEAR_SNAPSHOT_EVENT uses 'platform' as producer segment."""
        assert (
            constants_event_types.TOPIC_LINEAR_SNAPSHOT_EVENT
            == "onex.evt.platform.linear-snapshot.v1"
        )

    def test_model_topic_matches_constant(self) -> None:
        """Model-level TOPIC_* constants must match the central registry."""
        from omnibase_core.models.events.model_git_hook_event import (
            TOPIC_GIT_HOOK_EVENT as MODEL_GIT_HOOK,
        )
        from omnibase_core.models.events.model_github_pr_status_event import (
            TOPIC_GITHUB_PR_STATUS_EVENT as MODEL_PR_STATUS,
        )
        from omnibase_core.models.events.model_linear_snapshot_event import (
            TOPIC_LINEAR_SNAPSHOT_EVENT as MODEL_LINEAR,
        )

        assert MODEL_GIT_HOOK == constants_event_types.TOPIC_GIT_HOOK_EVENT
        assert MODEL_PR_STATUS == constants_event_types.TOPIC_GITHUB_PR_STATUS_EVENT
        assert MODEL_LINEAR == constants_event_types.TOPIC_LINEAR_SNAPSHOT_EVENT

    def test_no_old_topic_names_remain(self) -> None:
        """Ensure the old 4-segment topic names are no longer present."""
        old_topics = {
            "onex.evt.git.hook.v1",
            "onex.evt.github.pr-status.v1",
            "onex.evt.linear.snapshot.v1",
        }
        for name, value in _collect_topic_constants():
            assert value not in old_topics, (
                f"{name} = '{value}' still uses the old 4-segment topic name"
            )
