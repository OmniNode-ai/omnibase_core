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
    .. code-block:: python

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

import warnings
from datetime import datetime
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_handler_type import EnumHandlerType
from omnibase_core.models.core.model_envelope_metadata import ModelEnvelopeMetadata
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

    Attributes:
        envelope_id (UUID): Unique identifier for this envelope instance.
            Each envelope MUST have a unique ID to enable deduplication and
            tracking across distributed systems.

        envelope_version (ModelSemVer): Envelope format version following
            semantic versioning. Used for schema evolution when the
            envelope format changes between versions.

        correlation_id (UUID): Correlation ID for tracking related events
            across services. All envelopes in a single logical transaction
            or workflow share the same correlation_id.

        causation_id (UUID | None): ID of the causing event for causation
            chain tracking. Points to the envelope_id of the event that
            directly caused this one. Enables tracing event chains.
            Defaults to None for root events.

        source_node (str): Name/identifier of the node that created this
            envelope. Used for debugging and routing responses.

        source_node_id (UUID | None): UUID of the specific node instance
            that created this envelope. Useful in horizontally scaled
            deployments where multiple instances share a source_node name.
            Defaults to None.

        target_node (str | None): Target node name for routing. If None,
            the envelope may be broadcast or handled by any capable node.
            Defaults to None.

        handler_type (EnumHandlerType | None): Handler type for routing
            decisions. Specifies how the envelope should be processed
            (HTTP, KAFKA, DATABASE, etc.). Defaults to None.

        operation (str): Operation or event type identifier. Describes what
            action or event this envelope represents (e.g., 'GET_DATA',
            'USER_CREATED').

        payload (dict[str, Any]): The actual message data as a dictionary.
            Contains the business-specific content of the envelope. Can
            contain nested structures and any JSON-serializable types.

        metadata (ModelEnvelopeMetadata): Typed metadata for the envelope.
            Contains trace_id, request_id, span_id, headers, tags, and an
            extra field for dynamic data. Defaults to an empty instance.

        timestamp (datetime): When the envelope was created. Should be
            timezone-aware (preferably UTC) for consistency across
            distributed systems.

        is_response (bool): Whether this envelope is a response to a
            previous request. When True, success and error fields become
            meaningful. Defaults to False.

        success (bool | None): Response success status. Only meaningful
            when is_response=True. None indicates status is not applicable
            or not yet determined. Defaults to None.

        error (str | None): Error message if the operation failed. Only
            meaningful when is_response=True and success=False.
            Defaults to None.

    Example:
        .. code-block:: python

            from datetime import UTC, datetime
            from uuid import uuid4

            from omnibase_core.models.core.model_onex_envelope import (
                ModelOnexEnvelope,
            )
            from omnibase_core.models.primitives.model_semver import ModelSemVer

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
        This model uses ``frozen=False`` (mutable) with ``validate_assignment=True``
        to support testing, debugging, and scenarios where envelope modification
        is required after creation.

        **Why not frozen=True?**

        - Testing often requires modifying envelope fields for different scenarios
        - Some workflows involve building envelopes incrementally
        - Response envelopes may need field updates before sending
        - Debugging tools benefit from mutable state inspection

        **Concurrent Access Guidelines:**

        - **Read Access**: Thread-safe. Multiple threads can safely read
          envelope fields simultaneously without synchronization.

        - **Write Access**: NOT thread-safe. If multiple threads may modify
          the same envelope instance, use external synchronization:

          .. code-block:: python

              import threading

              envelope = ModelOnexEnvelope(...)
              lock = threading.Lock()

              def update_envelope(new_payload: dict) -> None:
                  with lock:
                      envelope.payload = new_payload

        - **Best Practice**: Treat envelopes as effectively immutable after
          creation. Create new envelope instances rather than modifying
          existing ones when possible.

        - **Shared Instance Warning**: Do NOT share envelope instances
          across threads without synchronization. Create thread-local
          copies or use locks.

        For comprehensive threading guidance, see: ``docs/guides/THREADING.md``

    Note:
        The ``metadata`` field uses ``default_factory=ModelEnvelopeMetadata``
        rather than a mutable default value. This is the recommended Pydantic
        pattern to ensure each instance gets its own metadata object, avoiding
        shared mutable state bugs. The performance impact is negligible (model
        creation is ~100-200ns per envelope).

    Validation:
        The model performs soft validation for success/error correlation to
        ensure consistent state in response envelopes:

        1. **Error with success=True**: If ``error`` is set (non-empty string)
           and ``success=True``, a warning is issued. This is likely a mistake -
           if there's an error, success should typically be False.

        2. **success=False without error** (response only): If ``is_response=True``
           and ``success=False`` but no ``error`` is provided, a warning is issued.
           Failed responses should typically include an error message for debugging.

        These are soft validations (warnings only) to maintain backward
        compatibility. The model will still be created, but warnings help
        identify potentially inconsistent state.

        Example of proper usage:

        .. code-block:: python

            # Successful response - no error
            response = ModelOnexEnvelope(
                envelope_id=uuid4(),
                envelope_version=ModelSemVer(major=1, minor=0, patch=0),
                correlation_id=request.correlation_id,
                causation_id=request.envelope_id,
                source_node="server_service",
                target_node="client_service",
                operation="GET_DATA_RESPONSE",
                payload={"data": "result"},
                timestamp=datetime.now(UTC),
                is_response=True,
                success=True,
                error=None,  # Correct: no error for success
            )

            # Failed response - with error
            response = ModelOnexEnvelope(
                envelope_id=uuid4(),
                envelope_version=ModelSemVer(major=1, minor=0, patch=0),
                correlation_id=request.correlation_id,
                causation_id=request.envelope_id,
                source_node="server_service",
                target_node="client_service",
                operation="GET_DATA_RESPONSE",
                payload={},
                timestamp=datetime.now(UTC),
                is_response=True,
                success=False,
                error="Validation failed: missing required field",  # Correct
            )

    See Also:
        - :class:`~omnibase_core.models.primitives.model_semver.ModelSemVer`:
          Semantic versioning for envelope format
        - :class:`~omnibase_core.enums.enum_handler_type.EnumHandlerType`:
          Handler type enumeration for routing
        - ``docs/guides/THREADING.md``: Thread safety guidelines

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

    # Performance Note: default_factory creates a new ModelEnvelopeMetadata per
    # envelope. This is intentional and correct:
    # - Model creation is fast (~100-200ns, negligible overhead)
    # - Required by Pydantic to avoid mutable default sharing between instances
    # - For high-throughput scenarios (>100k envelopes/sec), consider pooling
    #   or pre-allocating envelopes at the application level
    metadata: ModelEnvelopeMetadata = Field(
        default_factory=ModelEnvelopeMetadata,
        description="Typed metadata for the envelope. Contains trace_id, "
        "request_id, span_id, headers, tags, and extra for dynamic data.",
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
        (truncated), source node, and response status for quick identification.

        Returns:
            str: Formatted string like:
                "ModelOnexEnvelope[op=GET_DATA, corr=12345678, src=client_service, resp=False]"

        Note:
            The ``resp`` field indicates whether this is a response envelope
            (``resp=True``) or a request/event envelope (``resp=False``).
            This is useful for debugging request/response flows in logs.
        """
        corr_short = str(self.correlation_id)[:8]
        return (
            f"ModelOnexEnvelope["
            f"op={self.operation}, "
            f"corr={corr_short}, "
            f"src={self.source_node}, "
            f"resp={self.is_response}]"
        )

    # ==========================================================================
    # Validation
    # ==========================================================================

    @model_validator(mode="after")
    def _validate_success_error_correlation(self) -> Self:
        """
        Validate success/error field correlation for consistent state.

        This validator ensures that the success and error fields are used
        consistently in response envelopes. It issues warnings (not errors)
        to help identify potentially inconsistent state.

        Validation Rules:
            1. If error is set and success is True, warn about inconsistency.
               An error message typically indicates failure.

            2. If is_response=True, success=False, and no error is set, warn
               that an error message should be provided for debugging.

        Returns:
            Self: The validated model instance (unchanged).

        Warns:
            UserWarning: When success/error correlation is inconsistent.
        """
        has_error = self.error is not None and len(self.error.strip()) > 0

        # Rule 1: Error present but success=True is inconsistent
        if has_error and self.success is True:
            warnings.warn(
                f"ModelOnexEnvelope has error='{self.error}' but success=True. "
                "If an error is present, success should typically be False. "
                f"[correlation_id={self.correlation_id}, operation={self.operation}]",
                UserWarning,
                stacklevel=2,
            )

        # Rule 2: Response with success=False should have error message
        if self.is_response and self.success is False and not has_error:
            warnings.warn(
                "ModelOnexEnvelope is a response with success=False but no error "
                "message. Failed responses should include an error for debugging. "
                f"[correlation_id={self.correlation_id}, operation={self.operation}]",
                UserWarning,
                stacklevel=2,
            )

        return self
