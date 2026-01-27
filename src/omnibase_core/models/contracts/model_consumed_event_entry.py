"""Consumed event entry model for YAML contracts.

ONEX infra extension - used for contract-level event subscription declarations.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelConsumedEventEntry(BaseModel):
    """Simple consumed event entry for YAML contracts.

    ONEX infra extension - used for contract-level event subscription declarations.
    Normalized from simple strings or full subscription objects.

    Example YAML (string form - normalized to this model):
        consumed_events:
          - "jobs.events.created.v1"
          - "jobs.events.completed.v1"

    Example YAML (object form):
        consumed_events:
          - event_type: "jobs.events.created.v1"
            handler_function: "handle_job_created"
          - event_type: "jobs.events.completed.v1"
            handler_function: "handle_job_completed"
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    event_type: str = Field(..., description="Event type name or pattern")
    handler_function: str | None = Field(
        default=None,
        description="Handler function for this event (optional for simple declarations)",
    )
