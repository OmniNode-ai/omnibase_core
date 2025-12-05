"""
ModelOnexEnvelope - Enhanced event envelope for standardized message wrapping.

This model provides a comprehensive envelope format for wrapping events with
metadata including correlation IDs, timestamps, source information, routing
data, and request/response patterns. This is the canonical envelope format
for ONEX inter-service communication.

Architecture:
    Enhanced wrapper around any payload (dict) with:
    - Correlation and causation chain tracking
    - Routing support (target_node, handler_type)
    - Request/response pattern (is_response, success, error)
    - Extended metadata support

Usage:
    # Request envelope
    request = ModelOnexEnvelope(
        envelope_id=uuid4(),
        envelope_version=ModelSemVer(major=1, minor=0, patch=0),
        correlation_id=correlation_id,
        source_node="client_service",
        target_node="server_service",
        operation="GET_DATA",
        payload={"query": "test"},
        timestamp=datetime.now(UTC),
    )

    # Response envelope with causation chain
    response = ModelOnexEnvelope(
        envelope_id=uuid4(),
        envelope_version=ModelSemVer(major=1, minor=0, patch=0),
        correlation_id=correlation_id,  # Same as request
        causation_id=request.envelope_id,  # Points to request
        source_node="server_service",
        target_node="client_service",
        operation="GET_DATA_RESPONSE",
        payload={"data": "result"},
        timestamp=datetime.now(UTC),
        is_response=True,
        success=True,
    )

Part of omnibase_core framework - provides standardized event wrapping
with enhanced tracking and routing capabilities.

Related:
    - OMN-224: ModelOnexEnvelope refactoring
    - ModelOnexEnvelopeV1: Predecessor with simpler fields (deprecated)
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_handler_type import EnumHandlerType
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelOnexEnvelope(BaseModel):
    """
    Enhanced event envelope for standardized message wrapping.

    This is the canonical envelope format for ONEX inter-service communication,
    providing comprehensive tracking and routing capabilities. It replaces
    ModelOnexEnvelopeV1 with enhanced fields for:

    - Causation chain tracking (causation_id)
    - Routing support (target_node, handler_type)
    - Request/response pattern (is_response, success, error)
    - Extended metadata support

    Key Fields:
        - envelope_id: UUID for this specific envelope
        - envelope_version: Format version (ModelSemVer)
        - correlation_id: UUID for tracking related events
        - causation_id: UUID of the causing event (for causation chain)
        - source_node: Node that created this envelope
        - source_node_id: UUID of the node instance (optional)
        - target_node: Target node for routing (optional)
        - handler_type: Handler type for routing (optional)
        - operation: Operation/event type identifier
        - payload: The actual event data (as dict)
        - metadata: Additional metadata (optional)
        - timestamp: When the envelope was created
        - is_response: Whether this is a response envelope
        - success: Response success status (optional)
        - error: Error message if failed (optional)

    Example:
        # Create a request envelope
        request = ModelOnexEnvelope(
            envelope_id=uuid4(),
            envelope_version=ModelSemVer(major=1, minor=0, patch=0),
            correlation_id=uuid4(),
            source_node="metrics_service",
            operation="METRICS_RECORDED",
            payload={"metric": "value"},
            timestamp=datetime.now(UTC),
        )

        # Serialize to JSON
        json_str = request.model_dump_json()

        # Deserialize from JSON
        restored = ModelOnexEnvelope.model_validate_json(json_str)

    Thread Safety:
        This model is mutable (frozen=False) but validates on assignment.
        Safe for concurrent read access. For concurrent writes, use
        external synchronization.

    .. versionadded:: 0.3.6
        Replaces ModelOnexEnvelopeV1 with enhanced fields.
    """

    # ==========================================================================
    # Core Identity Fields (Required)
    # ==========================================================================

    envelope_id: UUID = Field(
        ...,
        description="Unique identifier for this envelope instance.",
    )

    envelope_version: ModelSemVer = Field(
        ...,
        description="Envelope format version following semantic versioning.",
    )

    correlation_id: UUID = Field(
        ...,
        description="Correlation ID for tracking related events across services.",
    )

    # ==========================================================================
    # Causation Chain (Optional)
    # ==========================================================================

    causation_id: UUID | None = Field(
        default=None,
        description="ID of the causing event for causation chain tracking. "
        "Points to the envelope_id of the event that caused this one.",
    )

    # ==========================================================================
    # Source Information (Required + Optional)
    # ==========================================================================

    source_node: str = Field(
        ...,
        description="Name/identifier of the node that created this envelope.",
    )

    source_node_id: UUID | None = Field(
        default=None,
        description="UUID of the node instance that created this envelope. "
        "Used for node-to-node tracking in distributed systems.",
    )

    # ==========================================================================
    # Routing Information (Optional)
    # ==========================================================================

    target_node: str | None = Field(
        default=None,
        description="Target node name for routing. If None, envelope may be "
        "broadcast or handled by any capable node.",
    )

    handler_type: EnumHandlerType | None = Field(
        default=None,
        description="Handler type for routing decisions. Specifies how the "
        "envelope should be processed (HTTP, KAFKA, DATABASE, etc.).",
    )

    # ==========================================================================
    # Operation Information (Required)
    # ==========================================================================

    operation: str = Field(
        ...,
        description="Operation or event type identifier. Describes what action "
        "or event this envelope represents (e.g., 'GET_DATA', 'USER_CREATED').",
    )

    # ==========================================================================
    # Payload and Metadata (Required + Optional)
    # ==========================================================================

    payload: dict[str, Any] = Field(
        ...,
        description="The actual message data as a dictionary. Contains the "
        "business-specific content of the envelope.",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for the envelope. Can include "
        "trace_id, request_id, custom headers, or other contextual data.",
    )

    # ==========================================================================
    # Timestamp (Required)
    # ==========================================================================

    timestamp: datetime = Field(
        ...,
        description="When the envelope was created. Should be timezone-aware.",
    )

    # ==========================================================================
    # Request/Response Pattern (Optional)
    # ==========================================================================

    is_response: bool = Field(
        default=False,
        description="Whether this envelope is a response to a previous request. "
        "When True, success and error fields become meaningful.",
    )

    success: bool | None = Field(
        default=None,
        description="Response success status. Only meaningful when is_response=True. "
        "None indicates status is not applicable or not yet determined.",
    )

    error: str | None = Field(
        default=None,
        description="Error message if the operation failed. Only meaningful when "
        "is_response=True and success=False.",
    )

    # ==========================================================================
    # Model Configuration
    # ==========================================================================

    model_config = ConfigDict(
        frozen=False,  # Allow modification for testing/debugging
        validate_assignment=True,  # Validate on attribute assignment
    )

    # ==========================================================================
    # String Representation
    # ==========================================================================

    def __str__(self) -> str:
        """
        Human-readable representation of the envelope.

        Returns a concise string showing the operation type, correlation ID
        (truncated), and source node for quick identification.

        Returns:
            str: Formatted string like:
                "ModelOnexEnvelope[op=GET_DATA, corr=12345678, src=client_service]"
        """
        corr_short = str(self.correlation_id)[:8]
        return (
            f"ModelOnexEnvelope["
            f"op={self.operation}, "
            f"corr={corr_short}, "
            f"src={self.source_node}]"
        )
