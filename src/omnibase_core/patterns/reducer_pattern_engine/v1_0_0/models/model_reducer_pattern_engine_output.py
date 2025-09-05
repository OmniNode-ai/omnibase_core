"""ONEX-compliant output model for Reducer Pattern Engine with envelope support."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_event_envelope import ModelEventEnvelope
from omnibase_core.model.core.model_onex_event import ModelOnexEvent

from .model_workflow_response import ModelWorkflowResponse


class ModelReducerPatternEngineOutput(BaseModel):
    """
    ONEX-compliant output model for Reducer Pattern Engine with envelope support.

    Supports both direct workflow responses and envelope-wrapped responses for
    full ONEX 4-node architecture compliance and inter-node communication.
    """

    # Core response data
    workflow_response: ModelWorkflowResponse = Field(
        ..., description="The workflow processing response"
    )

    # ONEX envelope for protocol compliance (optional for backward compatibility)
    envelope: Optional[ModelEventEnvelope] = Field(
        None, description="ONEX event envelope for protocol-compliant routing"
    )

    # Protocol metadata
    protocol_version: str = Field(
        default="1.0.0", description="Protocol version for compatibility"
    )

    source_node_id: str = Field(
        default="reducer_pattern_engine",
        description="Source node ID for distributed processing",
    )

    target_node_id: Optional[str] = Field(
        None, description="Target node ID for response routing"
    )

    # Processing metadata
    processing_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional processing metadata and metrics"
    )

    # Tracing and correlation
    correlation_id: UUID = Field(..., description="Correlation ID for request tracking")

    response_id: UUID = Field(
        default_factory=uuid4, description="Unique response identifier"
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Response creation timestamp"
    )

    # ONEX compliance metadata
    onex_compliance_version: str = Field(
        default="1.0.0", description="ONEX compliance version"
    )

    node_type: str = Field(
        default="COMPUTE", description="ONEX node type classification"
    )

    @classmethod
    def from_workflow_response(
        cls, workflow_response: ModelWorkflowResponse, **kwargs
    ) -> "ModelReducerPatternEngineOutput":
        """
        Create output from a workflow response for backward compatibility.

        Args:
            workflow_response: The workflow response to wrap
            **kwargs: Additional fields to set

        Returns:
            ModelReducerPatternEngineOutput: Output model with workflow response
        """
        return cls(
            workflow_response=workflow_response,
            correlation_id=workflow_response.correlation_id,
            processing_metadata={
                "processing_time_ms": workflow_response.processing_time_ms,
                "subreducer_name": workflow_response.subreducer_name,
                "status": (
                    workflow_response.status.value
                    if hasattr(workflow_response.status, "value")
                    else workflow_response.status
                ),
            },
            **kwargs,
        )

    @classmethod
    def from_envelope(
        cls, envelope: ModelEventEnvelope, **kwargs
    ) -> "ModelReducerPatternEngineOutput":
        """
        Create output from ONEX event envelope for protocol compliance.

        Args:
            envelope: ONEX event envelope containing workflow response
            **kwargs: Additional fields to set

        Returns:
            ModelReducerPatternEngineOutput: Output model with envelope

        Raises:
            ValueError: If envelope payload is not a valid workflow response
        """
        # Extract workflow response from envelope payload
        if not isinstance(envelope.payload, ModelOnexEvent):
            raise ValueError("Envelope payload must be a ModelOnexEvent")

        # For now, assume the event data contains the workflow response
        # In a real implementation, you'd need proper event type handling
        event_data = envelope.payload.data
        if not isinstance(event_data, dict):
            raise ValueError("Event data must contain workflow response data")

        # Create workflow response from event data
        workflow_response = ModelWorkflowResponse(**event_data)

        return cls(
            workflow_response=workflow_response,
            envelope=envelope,
            correlation_id=envelope.correlation_id,
            target_node_id=envelope.source_node_id,  # Response goes back to source
            **kwargs,
        )

    def to_envelope(self) -> ModelEventEnvelope:
        """
        Convert output to ONEX event envelope for protocol compliance.

        Returns:
            ModelEventEnvelope: Envelope wrapping this output
        """
        # Create event from workflow response
        event = ModelOnexEvent(
            event_id=str(uuid4()),
            event_type="workflow_processing_response",
            data=self.workflow_response.model_dump(),
            metadata={
                "protocol_version": self.protocol_version,
                "processing_metadata": self.processing_metadata,
                "response_id": str(self.response_id),
                "node_type": self.node_type,
                "onex_compliance_version": self.onex_compliance_version,
            },
        )

        # If we already have an envelope, update it for response
        if self.envelope:
            # Create response envelope from original request envelope
            from omnibase_core.model.core.model_route_hop import ModelRouteHop
            from omnibase_core.model.core.model_route_spec import ModelRouteSpec

            # Create return route spec
            route_spec = ModelRouteSpec(
                routing_strategy="direct",
                target_node_id=self.envelope.source_node_id,  # Return to originator
                max_hops=5,
            )

            # Add hop to trace
            response_hop = ModelRouteHop(
                node_id=self.source_node_id,
                hop_timestamp=datetime.utcnow(),
                hop_metadata={"action": "workflow_processed"},
            )

            return ModelEventEnvelope(
                envelope_id=str(uuid4()),
                created_at=datetime.utcnow(),
                route_spec=route_spec,
                trace=self.envelope.trace + [response_hop],
                payload=event,
                source_node_id=self.source_node_id,
                correlation_id=self.correlation_id,
                current_hop_count=self.envelope.current_hop_count + 1,
                metadata={
                    "response_to": self.envelope.envelope_id,
                    "processing_node": self.source_node_id,
                },
            )

        # Create new response envelope
        from omnibase_core.model.core.model_route_spec import ModelRouteSpec

        route_spec = ModelRouteSpec(
            routing_strategy="direct",
            target_node_id=self.target_node_id or "unknown",
            max_hops=5,
        )

        return ModelEventEnvelope.create_direct(
            payload=event,
            route_spec=route_spec,
            source_node_id=self.source_node_id,
            correlation_id=self.correlation_id,
        )

    def get_correlation_id(self) -> UUID:
        """Get the correlation ID, preferring envelope if available."""
        if self.envelope:
            return self.envelope.correlation_id
        return self.correlation_id

    def get_source_node_id(self) -> str:
        """Get the source node ID for response routing."""
        return self.source_node_id

    def get_target_node_id(self) -> Optional[str]:
        """Get the target node ID for response routing."""
        if self.envelope:
            return self.envelope.source_node_id  # Response goes back to source
        return self.target_node_id

    def is_success(self) -> bool:
        """Check if the workflow processing was successful."""
        status_value = (
            self.workflow_response.status.value
            if hasattr(self.workflow_response.status, "value")
            else self.workflow_response.status
        )
        return status_value in ["completed", "success"]

    def get_error_info(self) -> Optional[Dict[str, Any]]:
        """Get error information if processing failed."""
        if self.is_success():
            return None

        return {
            "error_message": self.workflow_response.error.error_message,
            "error_details": {"error_code": self.workflow_response.error.error_code},
            "error_context": self.workflow_response.error.error_context,
            "workflow_id": str(self.workflow_response.workflow_id),
            "workflow_type": self.workflow_response.workflow_type.value,
        }

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str,
        }
