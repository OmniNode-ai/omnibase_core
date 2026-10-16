# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""How a workflow lets the merge queue run a job pull request CI skips (OMN-19998)."""

from __future__ import annotations

from enum import StrEnum, unique

__all__ = ["EnumMergeQueueParityRule"]


@unique
class EnumMergeQueueParityRule(StrEnum):
    """The shapes that make a merge-queue-only failure possible.

    The values are written into each repository's merge-queue parity baseline
    file, so they are a stable external surface.
    """

    NO_PULL_REQUEST_TRIGGER = "no_pull_request_trigger"
    """The workflow triggers on ``merge_group`` and not on ``pull_request``."""

    PULL_REQUEST_PATH_FILTER = "pull_request_path_filter"
    """The ``pull_request`` trigger filters on paths; ``merge_group`` cannot."""

    MERGE_QUEUE_ONLY_IF = "merge_queue_only_if"
    """A job's ``if:`` can be true on ``merge_group`` while false on ``pull_request``."""

    EVENT_DEPENDENT_GATE = "event_dependent_gate"
    """A job is gated on a ``needs`` output that a job computes from the event name."""
