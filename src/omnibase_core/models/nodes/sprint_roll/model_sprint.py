# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One sprint window and its tickets (OMN-20396).

`elapsed` and `span` are days, and both are needed rather than derivable: throughput is
measured as what closed over the days actually elapsed, then extrapolated to the span, so
a sprint read mid-week does not understate a week's capacity.
"""

from __future__ import annotations

import datetime as dt
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.sprint_roll.model_sprint_ticket import ModelSprintTicket

__all__ = ["ModelSprint"]


class ModelSprint(BaseModel):
    """A sprint project: its window, and every ticket in it."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    sprint_id: UUID
    name: str
    start: dt.date
    end: dt.date
    tickets: tuple[ModelSprintTicket, ...] = Field(default_factory=tuple)
    elapsed_days: int = 7
    span_days: int = 7
