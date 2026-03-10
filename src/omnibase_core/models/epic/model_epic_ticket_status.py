# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelEpicTicketStatus — status of a single ticket within an epic execution.

Migration-phase capture model. Status fields use ``str`` instead of enums
to avoid breaking existing state files during initial adoption. A follow-up
task should introduce ``EnumEpicStatus`` once the actual status vocabulary
stabilizes from production usage.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelEpicTicketStatus"]


class ModelEpicTicketStatus(BaseModel):
    """Status of a single ticket within an epic execution.

    The ``status`` field uses ``str`` instead of an enum to accommodate the
    35+ distinct ticket status strings observed in production state files.
    See the corpus comment in model_epic_state.py for the full vocabulary.
    A follow-up task should introduce ``EnumTicketStatus`` once the vocabulary
    stabilizes from production usage.
    """

    model_config = ConfigDict(extra="allow", from_attributes=True)

    # string-id-ok: ticket_id is a Linear ticket ID (e.g., "OMN-1234"), not a UUID
    ticket_id: str = Field(..., min_length=1)
    status: str = Field(..., min_length=1)
    pr_url: str | None = Field(default=None)
    pr_number: int | None = Field(default=None)
    branch: str | None = Field(default=None)
    error: str | None = Field(default=None)
    failure_type: str | None = Field(default=None)
