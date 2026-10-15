# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelContextCallerScope — the typed descriptors a caller supplies (OMN-18531 / TC.1).

A task-kind rule is a condition over these fields. The caller fills each one
from what it already has; a field the caller does not supply is absent, never
derived from prompt text, so every field is optional.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelContextCallerScope"]


class ModelContextCallerScope(BaseModel):
    """Caller-supplied descriptors a profile's scope rules are evaluated over."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    task_class: str | None = Field(
        default=None, description="Delegation task class, when the caller has one"
    )
    node_archetype: str | None = Field(
        default=None,
        description="Node archetype named by a contract path or a ticket's node kind",
    )
    request_paths: tuple[str, ...] = Field(
        default=(), description="Paths the request touches, matched by path glob"
    )
    repository: str | None = Field(default=None, description="Repository name")
    lane: str | None = Field(default=None, description="Lane name")
    lane_kind: str | None = Field(default=None, description="Lane kind")
    cited_ruling_stamps: tuple[str, ...] = Field(
        default=(), description="Ruling row stamps a lane brief explicitly cites"
    )
    cited_plan_paths: tuple[str, ...] = Field(
        default=(), description="Plan paths a lane brief explicitly cites"
    )
    ticket: str | None = Field(default=None, description="Linear ticket identifier")
