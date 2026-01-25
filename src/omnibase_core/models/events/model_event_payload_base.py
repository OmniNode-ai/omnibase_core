"""Base model for event payloads.

Payloads are data structures embedded within events. Unlike events,
payloads do NOT carry event metadata (event_id, timestamp, correlation_id).

Event metadata belongs on the envelope (top-level event) once, not N times
inside nested payload structures.

Use this base for:
- Records returned in query responses
- Data structures embedded in event bodies
- Any model that will be nested inside an actual event

Do NOT use this base for:
- Top-level events (use ModelRuntimeEventBase)
- Standalone domain models (use appropriate domain base)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelEventPayloadBase"]


class ModelEventPayloadBase(BaseModel):
    """Base for embedded payload models within events.

    Provides consistent Pydantic configuration for frozen, validated payloads.
    Does NOT include event metadata fields (event_id, timestamp, etc.).
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        from_attributes=True,
    )
