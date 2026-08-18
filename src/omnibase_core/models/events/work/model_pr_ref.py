# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Structured PR citation (OMN-16177).

Replaces the free-prose PR mentions the markdown work ledger carries today.
A citation that cannot be resolved back to a repo, a number, and — when merged
— a merge commit is not evidence.
"""

from __future__ import annotations

from pydantic import Field, model_validator

from omnibase_core.enums.governance.enum_pr_state import EnumPRState
from omnibase_core.models.events.model_event_payload_base import ModelEventPayloadBase

__all__ = ["ModelPrRef"]


class ModelPrRef(ModelEventPayloadBase):
    """A pull request cited by a work event."""

    repo: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Repository name without the org, e.g. 'omnibase_core'.",
    )
    number: int = Field(..., ge=1, description="Pull request number.")
    state: EnumPRState = Field(..., description="PR state at the observed moment.")
    merge_sha: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{40}$",
        description="Merge commit SHA. Required when state is merged, else absent.",
    )

    @model_validator(mode="after")
    def _merge_sha_matches_state(self) -> ModelPrRef:
        """A merged citation carries its merge commit; an unmerged one cannot."""
        if self.state is EnumPRState.MERGED and self.merge_sha is None:
            raise ValueError(
                "merge_sha is required when state is 'merged' — a merged PR "
                "citation without its merge commit is unverifiable"
            )
        if self.state is not EnumPRState.MERGED and self.merge_sha is not None:
            raise ValueError(
                f"merge_sha must be absent when state is {self.state.value!r}"
            )
        return self
