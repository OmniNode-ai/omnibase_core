# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Core event model for Git hook events.

Published to ``onex.evt.platform.git-hook.v1`` by the Git hook integration layer.
This is the Core-layer view: a superset of ``ContractGitHookEvent``
from omnibase_spi.

Topic: ``onex.evt.platform.git-hook.v1``
Partition key: ``{repo}:{branch}``
"""

from __future__ import annotations

from pydantic import ConfigDict, Field

from omnibase_core.models.events.model_runtime_event_base import (
    ModelRuntimeEventBase,
)

__all__ = ["ModelGitHookEvent", "TOPIC_GIT_HOOK_EVENT"]

TOPIC_GIT_HOOK_EVENT = "onex.evt.platform.git-hook.v1"


class ModelGitHookEvent(ModelRuntimeEventBase):
    """Core event model for a Git hook event.

    Published to ``onex.evt.platform.git-hook.v1`` after a hook invocation completes.

    All fields from ``ContractGitHookEvent`` (omnibase_spi) must be present
    here (SPI contract fields ⊆ Core model fields invariant).

    Attributes:
        event_type: Fully-qualified event type identifier; equals the topic name.
        hook: Hook name (e.g. ``"pre-commit"``, ``"post-receive"``).
        repo: Repository identifier (e.g. ``"OmniNode-ai/omniclaude"``).
        branch: Branch name the hook fired on.
        author: Git committer/pusher username (NOT email).
        outcome: Hook outcome — ``"pass"`` or ``"fail"``.
        gates: List of gate names evaluated during the hook run.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=False,
        from_attributes=True,
    )

    event_type: str = Field(
        default=TOPIC_GIT_HOOK_EVENT,
        description="Fully-qualified event type identifier; equals the topic name.",
    )
    hook: str = Field(
        ...,
        description="Hook name (e.g. 'pre-commit', 'post-receive').",
    )
    repo: str = Field(
        ...,
        description="Repository identifier (e.g. 'OmniNode-ai/omniclaude').",
    )
    branch: str = Field(
        ...,
        description="Branch name the hook fired on.",
    )
    author: str = Field(
        ...,
        description="Git committer/pusher username (NOT email).",
    )
    outcome: str = Field(
        ...,
        description="Hook outcome: 'pass' or 'fail'.",
    )
    gates: list[str] = Field(
        default_factory=list,
        description="Gate names evaluated during the hook run.",
    )
