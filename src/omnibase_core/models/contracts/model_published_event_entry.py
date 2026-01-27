"""Published event entry model for YAML contracts.

ONEX infra extension - used for contract-level event publishing declarations.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelPublishedEventEntry(BaseModel):
    """Simple published event entry for YAML contracts.

    ONEX infra extension - used for contract-level event publishing declarations.
    Defines events that a node may publish during execution.

    Example YAML:
        published_events:
          - topic: "jobs.events.created.v1"
            event_type: "ModelEventJobCreated"
          - topic: "jobs.events.completed.v1"
            event_type: "ModelEventJobCompleted"
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    topic: str = Field(..., description="Topic pattern for event publishing")
    event_type: str = Field(..., description="Event type name")
