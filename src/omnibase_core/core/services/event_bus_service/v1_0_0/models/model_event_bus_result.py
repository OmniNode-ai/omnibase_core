"""
Event Bus Service Operation Result Model.

Result model for EventBusService operations with success/failure tracking.

Author: ONEX Framework Team
"""

from typing import Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_event_envelope import ModelEventEnvelope
from omnibase_core.model.core.model_onex_event import ModelOnexEvent
from omnibase_core.protocol.protocol_event_bus import ProtocolEventBus


class ModelEventBusResult(BaseModel):
    """
    Result model for Event Bus Service operations.

    Encapsulates the outcome of event bus operations with detailed
    success/failure information and relevant data.
    """

    # Operation outcome
    success: bool = Field(description="Whether the operation completed successfully")

    operation_type: str = Field(
        description="Type of operation performed (emit_start, emit_success, publish_introspection, etc.)"
    )

    message: str = Field(
        description="Human-readable description of the operation result"
    )

    # Event details
    event_id: Optional[UUID] = Field(
        default=None, description="ID of the event that was processed"
    )

    correlation_id: Optional[UUID] = Field(
        default=None, description="Correlation ID for operation tracking"
    )

    event_type: Optional[str] = Field(
        default=None, description="Type of event that was processed"
    )

    # Node information
    node_id: Optional[str] = Field(
        default=None, description="Node identifier involved in the operation"
    )

    node_name: Optional[str] = Field(
        default=None, description="Node name involved in the operation"
    )

    # Event bus information
    event_bus_available: bool = Field(
        default=False, description="Whether event bus was available for the operation"
    )

    event_bus_type: Optional[str] = Field(
        default=None, description="Type/implementation of event bus used"
    )

    # Event patterns
    patterns_processed: List[str] = Field(
        default_factory=list, description="Event patterns that were processed"
    )

    patterns_source: Optional[str] = Field(
        default=None,
        description="Source of event patterns (contract, node_name, default)",
    )

    # Subscription management
    subscriptions_created: int = Field(
        default=0, description="Number of event subscriptions created"
    )

    subscriptions_failed: int = Field(
        default=0, description="Number of event subscriptions that failed"
    )

    # Publishing details
    events_published: int = Field(
        default=0, description="Number of events successfully published"
    )

    events_failed: int = Field(
        default=0, description="Number of events that failed to publish"
    )

    retry_attempts: int = Field(default=0, description="Number of retry attempts made")

    # Error information
    error_details: Optional[str] = Field(
        default=None, description="Detailed error information if operation failed"
    )

    error_type: Optional[str] = Field(
        default=None, description="Type of error that occurred"
    )

    # Performance metrics
    processing_time_ms: Optional[float] = Field(
        default=None, description="Time taken to process the operation in milliseconds"
    )

    # Metadata and additional context
    metadata: Dict[str, Union[str, int, bool, float]] = Field(
        default_factory=dict, description="Additional metadata related to the operation"
    )

    # Result data
    created_event: Optional[ModelOnexEvent] = Field(
        default=None, description="Event object that was created (if applicable)"
    )

    created_envelope: Optional[ModelEventEnvelope] = Field(
        default=None, description="Event envelope that was created (if applicable)"
    )

    resolved_event_bus: Optional[ProtocolEventBus] = Field(
        default=None, description="Event bus instance that was resolved or used"
    )

    class Config:
        """Pydantic configuration."""

        validate_assignment = True
        extra = "forbid"
        # Allow ProtocolEventBus in the model
        arbitrary_types_allowed = True
