# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The verdict of the shared Done-write receipt gate (OMN-20368)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.ticket.model_ac_binding_row import ModelAcBindingRow


class ModelDoneWriteDecision(BaseModel):
    """Whether a ticket may be written Done, and why not when it may not.

    ``allowed`` is True only when a verified dod_verify verdict binds every
    acceptance criterion in the ticket's description through ``binds_ac``.
    ``reason`` is empty on an allow and names the cause on a refusal.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    allowed: bool = Field(
        ..., description="True only when the bound-receipt bar is met."
    )
    reason: str = Field(
        default="",
        description="Why the Done write is refused; empty when it is allowed.",
    )
    unbound: tuple[str, ...] = Field(
        default=(),
        description="Acceptance criteria no verified check binds, verbatim.",
    )
    rows: tuple[ModelAcBindingRow, ...] = Field(
        default=(),
        description="The criterion-to-check binding table the decision read.",
    )


__all__ = ["ModelDoneWriteDecision"]
