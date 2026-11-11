# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The fields schema 1.1.0 adds to the ticket contract (OMN-23758)."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.ticket.model_ticket_business_brief import (
    ModelTicketBusinessBrief,
)

_MAX_STRING_LENGTH = 10000

# An external tracker ticket identifier such as ``OMN-1807``: not a UUID, and
# not versioned. The ``OMN-<digits>`` pattern is a 1.1.0 rule enforced by
# ``ModelTicketContract``, so 1.0.0 files keep loading.
TicketIdentifier = Annotated[str, Field(max_length=50)]


class ModelTicketStandardFormFields(BaseModel):
    """The standard-form fields of ``ModelTicketContract``.

    Optional here so 1.0.0 files keep loading; ``ModelTicketContract`` requires
    them when it declares schema 1.1.0 (``start_probe`` and ``diagnosis`` stay
    optional).
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    business_brief: ModelTicketBusinessBrief | None = Field(
        default=None,
        description="The five plain-language headings a non-technical reader can follow",
    )
    parent_ticket_id: TicketIdentifier | None = Field(
        default=None,
        description="The parent ticket this one serves (the Gate line)",
    )
    parent_ac_label: str | None = Field(
        default=None,
        description="The parent's acceptance-criterion label this ticket serves",
        max_length=50,
    )
    start_probe: str | None = Field(
        default=None,
        description="The probe that shows the work started (a ticket created In Progress)",
        max_length=_MAX_STRING_LENGTH,
    )
    diagnosis: str | None = Field(
        default=None,
        description="The diagnosis a defect-shaped ticket cites",
        max_length=_MAX_STRING_LENGTH,
    )
    repository: str | None = Field(
        default=None,
        description="The one repository this ticket's work belongs to",
        max_length=200,
    )


__all__ = ["ModelTicketStandardFormFields", "TicketIdentifier"]
