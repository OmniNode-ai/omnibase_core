# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One ticket as the sprint roll sees it (OMN-20396).

Deliberately NOT a general Linear issue model. The roll needs five facts and must not
grow a dependency on everything an issue carries: its identifier, its workflow state,
its estimate (which may be absent -- that is the normal case, not an error), whether it
carries a release criterion, and who owns it. The criterion mapping is passed separately
on the request, because it is owned by omninode_infra's `tools/beta_board` carrier
lists and not by the ticket.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelSprintTicket"]


class ModelSprintTicket(BaseModel):
    """A ticket's placement-relevant facts, side-effect free."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    identifier: str
    state: str
    estimate: int | None = None
    is_carrier: bool = False
    owner: str | None = None
    title: str = ""
    #: Only read when no carrier list names the ticket, to find its own `Gate:` line.
    #: Empty is normal and simply means the text fallback is all that is available.
    description: str = ""
