# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Current DoD projection row annotation, not replay truth."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelExecutionGraphStoredVerdictAnnotation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ticket_id: str = Field(min_length=1)
    correlation_id: UUID
    completed_at: datetime
    status: str = Field(min_length=1)
    outcome: str = Field(min_length=1)
    projection_cursor: int = Field(ge=0)
