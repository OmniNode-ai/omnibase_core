# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A view render receipt with a start and optional completion (OMN-21999).

The app sends the started record first. Once completion is available, its
timestamp must be at or after the start of the render attempt.
"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.dashboard.model_view_id_patterns import ViewId
from omnibase_core.models.dashboard.model_view_render_completed_record import (
    ModelViewRenderCompletedRecord,
)
from omnibase_core.models.dashboard.model_view_render_started_record import (
    ModelViewRenderStartedRecord,
)

__all__ = ["ModelViewRenderReceipt"]


class ModelViewRenderReceipt(BaseModel):
    """Render identity with the app's start and eventual completion records."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    render_id: ViewId = Field(
        ...,
        description="Identifier of the render attempt",
    )
    started: ModelViewRenderStartedRecord = Field(
        ..., description="Record sent when the app started rendering"
    )
    completed: ModelViewRenderCompletedRecord | None = Field(
        default=None, description="Completion record, absent while rendering is ongoing"
    )

    @model_validator(mode="after")
    def validate_completion_time(self) -> Self:
        """Refuse a completion timestamp before the start timestamp.

        Raises:
            ValueError: If completed_at is earlier than started_at.
        """
        if (
            self.completed is not None
            and self.completed.completed_at < self.started.started_at
        ):
            raise ValueError("completed_at must not be before started_at")
        return self
