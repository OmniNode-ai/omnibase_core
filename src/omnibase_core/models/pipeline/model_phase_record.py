# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Phase Record model for pipeline phase history.

Represents a completed pipeline phase with timestamp and optional artifacts.
Used as entries in ``ModelPipelineState.phase_history``.

.. versionadded:: 0.7.0
    Added as part of OMN-3870 to formalize the ticket-pipeline state model.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_pipeline_phase import EnumPipelinePhase

__all__ = ["ModelPhaseRecord"]


class ModelPhaseRecord(BaseModel):
    """Record of a completed pipeline phase.

    Immutable once created -- phase history is append-only.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    phase: EnumPipelinePhase
    """The pipeline phase that was completed."""

    completed_at: datetime
    """UTC timestamp when this phase completed."""

    artifacts: dict[str, str | int | float | bool | None] = (
        Field(  # @allow_dict_any: phase artifacts have heterogeneous but primitive values
            default_factory=dict
        )
    )
    """Optional artifacts produced by the phase (e.g., PR URL, commit SHA).

    Values are restricted to JSON-primitive types. Complex structured
    artifacts should be modeled as dedicated fields on the phase record
    or as separate models.
    """

    @field_validator("completed_at", mode="before")
    @classmethod
    def _enforce_utc(cls, v: Any) -> datetime:
        """Ensure completed_at has UTC timezone info."""
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v
