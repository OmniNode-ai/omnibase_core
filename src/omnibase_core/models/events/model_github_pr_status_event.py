# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Core event model for GitHub PR status events.

Published to ``onex.evt.github.pr-status.v1`` by the GitHub PR poller effect.
This is the Core-layer view: a superset of ``ContractGitHubPRStatusEvent``
from omnibase_spi.

Topic: ``onex.evt.github.pr-status.v1``
Partition key: ``{repo}:{pr_number}``
"""

from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict, Field

from omnibase_core.models.events.model_runtime_event_base import (
    ModelRuntimeEventBase,
)

__all__ = ["ModelGitHubPRStatusEvent", "TOPIC_GITHUB_PR_STATUS_EVENT"]

TOPIC_GITHUB_PR_STATUS_EVENT = "onex.evt.github.pr-status.v1"

TriageState = Literal[
    "draft",
    "stale",
    "ci_failing",
    "changes_requested",
    "ready_to_merge",
    "approved_pending_ci",
    "needs_review",
    "blocked",
]


class ModelGitHubPRStatusEvent(ModelRuntimeEventBase):
    """Core event model for a GitHub PR status event.

    Produced by the GitHub PR poller effect and published to
    ``onex.evt.github.pr-status.v1``.

    All fields from ``ContractGitHubPRStatusEvent`` (omnibase_spi) must
    be present here (SPI contract fields ⊆ Core model fields invariant).

    Attributes:
        event_type: Fully-qualified event type identifier; equals the topic name.
        repo: Repository identifier in ``{owner}/{name}`` format.
        pr_number: Pull request number (positive integer).
        triage_state: Current triage classification of the pull request.
        title: Pull request title.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=False,
        from_attributes=True,
    )

    event_type: str = Field(
        default=TOPIC_GITHUB_PR_STATUS_EVENT,
        description="Fully-qualified event type identifier; equals the topic name.",
    )
    repo: str = Field(
        ...,
        description=(
            "Repository in '{owner}/{name}' format (e.g. 'OmniNode-ai/omniclaude')."
        ),
    )
    pr_number: int = Field(
        ...,
        ge=1,
        description="Pull request number.",
    )
    triage_state: TriageState = Field(
        ...,
        description="Current triage classification of the pull request.",
    )
    title: str = Field(
        default="",
        description="Pull request title.",
    )
