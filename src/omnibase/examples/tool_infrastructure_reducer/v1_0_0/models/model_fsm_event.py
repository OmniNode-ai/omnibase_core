"""
ModelFSMEvent - Event definition for triggering state transitions.

Generated from FSM subcontract following ONEX contract-driven patterns.
Provides event specification including payload schema and processing configuration.
"""

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class FSMEventType(str, Enum):
    """Type classification of FSM events."""

    SYSTEM = "system"
    USER = "user"
    EXTERNAL = "external"
    TIMER = "timer"
    ERROR = "error"


class ModelFSMEvent(BaseModel):
    """
    Event definition for triggering state transitions.

    Defines events that can trigger state transitions including:
    - Event identification and classification
    - Priority for conflict resolution
    - Payload schema validation
    - Processing timeout configuration
    """

    # Core identification
    event_name: str = Field(
        ...,
        description="Unique identifier for the event",
        pattern=r"^ev_[a-z][a-z0-9_]*$",
        min_length=4,
        max_length=50,
    )

    event_type: FSMEventType = Field(
        ..., description="Type classification of the event"
    )

    description: str = Field(
        ...,
        description="Human-readable description of the event",
        min_length=5,
        max_length=200,
    )

    # Event configuration
    priority: int = Field(
        default=1, description="Event priority for conflict resolution", ge=1, le=10
    )

    payload_schema: Optional[Dict[str, Any]] = Field(
        default=None, description="JSON Schema for event payload validation"
    )

    timeout_ms: Optional[int] = Field(
        default=None,
        description="Timeout for event processing in milliseconds",
        ge=100,
        le=60000,
    )

    class Config:
        json_schema_extra = {
            "example": {
                "event_name": "ev_bootstrap",
                "event_type": "system",
                "description": "Bootstrap event to start infrastructure loading",
                "priority": 1,
                "payload_schema": {
                    "type": "object",
                    "properties": {"correlation_id": {"type": "string"}},
                },
                "timeout_ms": 5000,
            }
        }
