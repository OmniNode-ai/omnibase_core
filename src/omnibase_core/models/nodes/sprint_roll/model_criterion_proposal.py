# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A proposed release criterion for a ticket no carrier list names (OMN-20396).

`criterion` is None when nothing was strong enough, and that is an answer rather than a
failure: the board's reconciliation gate forbids an allowlist, so an unmappable ticket
gets a recorded ruling or has its label dropped -- never a guessed carrier. The near miss
is carried so a person settling it has somewhere to start.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelCriterionProposal"]


class ModelCriterionProposal(BaseModel):
    """One ticket's criterion proposal, with how it was reached."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    identifier: str
    criterion: str | None
    basis: str
    near_miss_criterion: str | None = None
    near_miss_score: int = 0
