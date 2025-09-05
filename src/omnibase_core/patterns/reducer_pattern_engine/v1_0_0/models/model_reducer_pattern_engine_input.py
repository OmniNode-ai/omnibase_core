"""ONEX-compliant input model for Reducer Pattern Engine with envelope support."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_event_envelope import ModelEventEnvelope
from omnibase_core.model.core.model_onex_event import ModelOnexEvent

from .model_workflow_request import ModelWorkflowRequest


class ModelReducerPatternEngineInput(BaseModel):
    """
    ONEX-compliant input model for Reducer Pattern Engine with envelope support.

    Supports both direct workflow requests and envelope-wrapped requests for
    full ONEX 4-node architecture compliance and inter-node communication.
    """

    # Core request data
    workflow_request: ModelWorkflowRequest = Field(
        ..., description="The workflow request to process"
    )

    # ONEX envelope for protocol compliance (optional for backward compatibility)
    envelope: Optional[ModelEventEnvelope] = Field(
        None, description="ONEX event envelope for protocol-compliant routing"
    )

    # Protocol metadata
    protocol_version: str = Field(
        default="1.0.0", description="Protocol version for compatibility"
    )

    source_node_id: Optional[str] = Field(
        None, description="Source node ID for distributed processing"
    )

    target_node_id: Optional[str] = Field(
        None, description="Target node ID for routing"
    )

    # Processing options
    processing_options: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional processing options and configurations",
    )

    # Tracing and correlation
    correlation_id: UUID = Field(
        default_factory=uuid4, description="Correlation ID for request tracking"
    )

    request_id: UUID = Field(
        default_factory=uuid4, description="Unique request identifier"
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Request creation timestamp"
    )

    @classmethod
    def from_workflow_request(
        cls, workflow_request: ModelWorkflowRequest, **kwargs
    ) -> "ModelReducerPatternEngineInput":
        """
        Create input from a workflow request for backward compatibility.

        Args:
            workflow_request: The workflow request to wrap
            **kwargs: Additional fields to set

        Returns:
            ModelReducerPatternEngineInput: Input model with workflow request
        """
        return cls(
            workflow_request=workflow_request,
            correlation_id=workflow_request.correlation_id,
            **kwargs,
        )

    @classmethod
    def from_envelope(
        cls, envelope: ModelEventEnvelope, **kwargs
    ) -> "ModelReducerPatternEngineInput":
        """
        Create input from ONEX event envelope for protocol compliance.

        Args:
            envelope: ONEX event envelope containing workflow request
            **kwargs: Additional fields to set

        Returns:
            ModelReducerPatternEngineInput: Input model with envelope

        Raises:
            ValueError: If envelope payload is not a valid workflow request
        """
        # Extract workflow request from envelope payload
        if not isinstance(envelope.payload, ModelOnexEvent):
            raise ValueError("Envelope payload must be a ModelOnexEvent")

        # For now, assume the event data contains the workflow request
        # In a real implementation, you'd need proper event type handling
        event_data = envelope.payload.data
        if not isinstance(event_data, dict):
            raise ValueError("Event data must contain workflow request data")

        # Create workflow request from event data
        workflow_request = ModelWorkflowRequest(**event_data)

        return cls(
            workflow_request=workflow_request,
            envelope=envelope,
            correlation_id=envelope.correlation_id,
            source_node_id=envelope.source_node_id,
            **kwargs,
        )

    def to_envelope(self) -> ModelEventEnvelope:
        """
        Convert input to ONEX event envelope for protocol compliance.

        Returns:
            ModelEventEnvelope: Envelope wrapping this input
        """
        # Create event from workflow request
        event = ModelOnexEvent(
            event_id=str(uuid4()),
            event_type="workflow_processing_request",
            data=self.workflow_request.model_dump(),
            metadata={
                "protocol_version": self.protocol_version,
                "processing_options": self.processing_options,
                "request_id": str(self.request_id),
            },
        )

        # If we already have an envelope, update it
        if self.envelope:
            self.envelope.payload = event
            return self.envelope

        # Create new envelope
        from omnibase_core.model.core.model_route_spec import ModelRouteSpec

        route_spec = ModelRouteSpec(
            routing_strategy="direct",
            target_node_id=self.target_node_id or "reducer_pattern_engine",
            max_hops=5,
        )

        return ModelEventEnvelope.create_direct(
            payload=event,
            route_spec=route_spec,
            source_node_id=self.source_node_id or "unknown",
            correlation_id=self.correlation_id,
        )

    def get_correlation_id(self) -> UUID:
        """Get the correlation ID, preferring envelope if available."""
        if self.envelope:
            return self.envelope.correlation_id
        return self.correlation_id

    def get_source_node_id(self) -> Optional[str]:
        """Get the source node ID, preferring envelope if available."""
        if self.envelope:
            return self.envelope.source_node_id
        return self.source_node_id

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str,
        }
