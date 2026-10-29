# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A Done write to judge: the ticket, its live description and the dod_verify verdict (OMN-20368)."""

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelDoneWriteReceiptRequest"]


class ModelDoneWriteReceiptRequest(BaseModel):
    """A Done write to judge: the ticket, its live description and the dod_verify verdict (OMN-20368)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    ticket_id: str
    description: str
    verdict: dict[str, object] | None = None
