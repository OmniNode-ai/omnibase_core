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
    - : ModelOnexEnvelope refactoring
    - ModelOnexEnvelopeV1: Predecessor with simpler fields (deprecated)
"""

import warnings
from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_handler_type import EnumHandlerType
from omnibase_core.models.core.model_envelope_metadata import ModelEnvelopeMetadata
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types.type_serializable_value import SerializedDict


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

        payload (SerializedDict): The actual message data as a dictionary.
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

    Security Considerations:
        The ``error`` field may contain information about internal system state
        that should not be exposed to external clients. Follow these guidelines
        when handling error messages in envelopes:

        **1. Internal vs External Errors:**

        Use detailed errors for internal logging and debugging, but sanitize
        before sending to external clients. The correlation_id enables
        correlating sanitized responses with detailed internal logs.

        **2. Information to Avoid Exposing:**

        - Stack traces and exception details
        - Database connection strings or query details
        - Internal file paths or directory structures
        - User credentials, tokens, or session identifiers
        - Internal service names, IPs, or network topology
        - Configuration details or environment variables

        **3. Safe vs Unsafe Error Message Examples:**

        .. code-block:: python

            # UNSAFE - exposes internal details
            error="Database error: connection to postgres://user:pass@db.internal:5432 failed"
            error="FileNotFoundError: /var/app/secrets/config.yaml not found"
            error="Authentication failed for user admin with token eyJhbGc..."

            # SAFE - generic but actionable
            error="Service temporarily unavailable"
            error="Request failed: invalid input"
            error="Authentication failed"

            # SAFE - specific but sanitized
            error="Validation failed: field 'email' is required"
            error="Resource not found: user_id does not exist"
            error="Rate limit exceeded: retry after 60 seconds"

        **4. Recommended Sanitization Pattern:**

        Log full error details internally with the correlation_id, then return
        a sanitized message in the envelope. Use the correlation_id to connect
        sanitized client responses with detailed server-side logs.

        .. code-block:: python

            from datetime import UTC, datetime
            from uuid import uuid4

            # 1. Capture the full error internally
            try:
                result = database.query(sql)
            except DatabaseError as e:
                # Full details logged internally with correlation_id
                logger.error(
                    f"Database query failed: {e}",
                    extra={
                        "correlation_id": str(request.correlation_id),
                        "sql_error_code": e.code,
                        "operation": request.operation,
                    }
                )

                # 2. Return sanitized error to client
                response = ModelOnexEnvelope(
                    envelope_id=uuid4(),
                    envelope_version=request.envelope_version,
                    correlation_id=request.correlation_id,
                    causation_id=request.envelope_id,
                    source_node="data_service",
                    target_node=request.source_node,
                    operation=f"{request.operation}_RESPONSE",
                    payload={},
                    timestamp=datetime.now(UTC),
                    is_response=True,
                    success=False,
                    # Sanitized: no internal details, includes reference ID
                    error=f"Data retrieval failed. Reference: {str(request.correlation_id)[:8]}",
                )

        **5. Error Severity Classification:**

        Consider classifying errors by severity to determine sanitization level:

        - **Client Errors (4xx)**: Can include specific validation details
          (e.g., "field 'email' format invalid")
        - **Server Errors (5xx)**: Should be generic (e.g., "Internal error")
          with correlation_id reference for support

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

    # NOTE: SerializedDict (which uses SerializableValue internally) is used here
    # as an acceptable exception to strict typing. Rationale:
    # - Envelopes are generic message containers that MUST accept arbitrary
    #   JSON-serializable data from any producer
    # - Type safety is enforced at the application layer where specific payload
    #   schemas (e.g., ModelUserCreatedPayload) are defined and validated
    # - This is a core messaging primitive, not a domain model - forcing typed
    #   payloads here would require envelope-per-message-type, defeating the purpose
    # - Consumers should use payload.get() with appropriate type guards or
    #   Pydantic model_validate() to parse expected payload structures
    # See: scripts/validation/validate-dict-any-usage.py for the validation script
    payload: SerializedDict = Field(
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

    # SECURITY WARNING: The error field may contain sensitive information.
    # Before exposing to external clients:
    # - Log detailed errors internally with correlation_id for debugging
    # - Sanitize error messages to remove stack traces, connection strings,
    #   file paths, credentials, and internal service topology
    # - Use correlation_id[:8] as a reference ID for client-facing errors
    # See "Security Considerations" in class docstring for detailed guidance.
    error: str | None = Field(
        default=None,
        description="Error message if the operation failed. Only meaningful when "
        "is_response=True and success=False. SECURITY: Sanitize before exposing "
        "to external clients - see class docstring Security Considerations.",
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
                stacklevel=3,  # Skip: warn() -> validator -> Pydantic __init__ -> user code
            )

        # Rule 2: Response with success=False should have error message
        if self.is_response and self.success is False and not has_error:
            warnings.warn(
                "ModelOnexEnvelope is a response with success=False but no error "
                "message. Failed responses should include an error for debugging. "
                f"[correlation_id={self.correlation_id}, operation={self.operation}]",
                UserWarning,
                stacklevel=3,  # Skip: warn() -> validator -> Pydantic __init__ -> user code
            )

        return self

    # ==========================================================================
    # Factory Methods
    # ==========================================================================

    @classmethod
    def create_request(
        cls,
        operation: str,
        payload: SerializedDict,
        source_node: str,
        *,
        target_node: str | None = None,
        handler_type: EnumHandlerType | None = None,
        correlation_id: UUID | None = None,
        envelope_version: ModelSemVer | None = None,
        metadata: ModelEnvelopeMetadata | None = None,
        source_node_id: UUID | None = None,
    ) -> Self:
        """
        Create a request envelope with sensible defaults.

        This factory method simplifies the creation of request envelopes by:
        - Auto-generating envelope_id (always unique)
        - Auto-generating correlation_id if not provided
        - Defaulting envelope_version to 1.0.0 if not provided
        - Setting timestamp to current UTC time
        - Setting is_response=False (this is a request)

        Args:
            operation: Operation or event type identifier (e.g., 'GET_DATA',
                'USER_CREATE'). Describes what action this envelope represents.
            payload: The actual message data as a dictionary. Contains the
                business-specific content of the request.
            source_node: Name/identifier of the node creating this request.
                Used for debugging and routing responses.
            target_node: Optional target node name for routing. If None, the
                request may be handled by any capable node.
            handler_type: Optional handler type for routing decisions
                (HTTP, KAFKA, DATABASE, etc.).
            correlation_id: Optional correlation ID for tracking. If not
                provided, a new UUID is generated automatically.
            envelope_version: Optional envelope format version. Defaults to
                1.0.0 if not provided.
            metadata: Optional typed metadata for the envelope. Defaults to
                an empty ModelEnvelopeMetadata instance.
            source_node_id: Optional UUID of the specific node instance
                creating this request.

        Returns:
            A new ModelOnexEnvelope configured as a request.

        Example:
            .. code-block:: python

                from omnibase_core.models.core.model_onex_envelope import (
                    ModelOnexEnvelope,
                )

                # Simple request with auto-generated IDs
                request = ModelOnexEnvelope.create_request(
                    operation="GET_USER",
                    payload={"user_id": "123"},
                    source_node="api_gateway",
                    target_node="user_service",
                )

                # Request with explicit correlation ID for tracking
                from uuid import uuid4
                correlation = uuid4()
                request = ModelOnexEnvelope.create_request(
                    operation="CREATE_ORDER",
                    payload={"items": [{"id": 1, "qty": 2}]},
                    source_node="checkout_service",
                    correlation_id=correlation,
                )

        See Also:
            - :meth:`create_response`: Create a response from a request envelope

        .. versionadded:: 0.3.6
        """
        from datetime import UTC, datetime
        from uuid import uuid4

        return cls(
            envelope_id=uuid4(),
            envelope_version=envelope_version or ModelSemVer(major=1, minor=0, patch=0),
            correlation_id=correlation_id or uuid4(),
            source_node=source_node,
            source_node_id=source_node_id,
            target_node=target_node,
            handler_type=handler_type,
            operation=operation,
            payload=payload,
            metadata=metadata or ModelEnvelopeMetadata(),
            timestamp=datetime.now(UTC),
            is_response=False,
            success=None,
            error=None,
        )

    @classmethod
    def create_response(
        cls,
        request: "ModelOnexEnvelope",
        payload: SerializedDict,
        *,
        success: bool = True,
        error: str | None = None,
        source_node: str | None = None,
        operation: str | None = None,
        metadata: ModelEnvelopeMetadata | None = None,
        source_node_id: UUID | None = None,
        handler_type: EnumHandlerType | None = None,
    ) -> Self:
        """
        Create a response envelope from a request envelope.

        This factory method simplifies response creation by:
        - Auto-generating a unique envelope_id
        - Preserving the correlation_id from the request
        - Setting causation_id to the request's envelope_id (chain tracking)
        - Swapping source/target nodes if source_node not provided
        - Using the same envelope_version as the request
        - Setting timestamp to current UTC time
        - Setting is_response=True

        Args:
            request: The original request envelope to respond to. The response
                will inherit correlation_id and set causation_id to the
                request's envelope_id.
            payload: The response data as a dictionary. Contains the
                business-specific response content.
            success: Whether the operation succeeded. Defaults to True.
            error: Error message if the operation failed. Should be set when
                success=False to provide debugging information.
            source_node: Optional source node for the response. If not provided,
                defaults to the request's target_node (response comes from the
                target that processed the request).
            operation: Optional operation name for the response. If not provided,
                defaults to the request's operation with "_RESPONSE" suffix.
            metadata: Optional typed metadata for the response. Defaults to
                an empty ModelEnvelopeMetadata instance.
            source_node_id: Optional UUID of the specific node instance
                creating this response.
            handler_type: Optional handler type for routing the response.
                If not provided, inherits from the request.

        Returns:
            A new ModelOnexEnvelope configured as a response with proper
            causation chain linking.

        Example:
            .. code-block:: python

                from omnibase_core.models.core.model_onex_envelope import (
                    ModelOnexEnvelope,
                )

                # Create request
                request = ModelOnexEnvelope.create_request(
                    operation="GET_USER",
                    payload={"user_id": "123"},
                    source_node="api_gateway",
                    target_node="user_service",
                )

                # Create successful response
                response = ModelOnexEnvelope.create_response(
                    request=request,
                    payload={"user": {"id": "123", "name": "Alice"}},
                    success=True,
                )

                # Create error response
                error_response = ModelOnexEnvelope.create_response(
                    request=request,
                    payload={},
                    success=False,
                    error="User not found: 123",
                )

                # Verify causation chain
                assert response.correlation_id == request.correlation_id
                assert response.causation_id == request.envelope_id

        See Also:
            - :meth:`create_request`: Create a request envelope

        .. versionadded:: 0.3.6
        """
        from datetime import UTC, datetime
        from uuid import uuid4

        # Determine source_node: use provided, else swap from request's target
        response_source = source_node or request.target_node or request.source_node

        # Determine target_node: response goes back to request's source
        response_target = request.source_node

        # Determine operation: use provided, else append _RESPONSE suffix
        response_operation = operation or f"{request.operation}_RESPONSE"

        return cls(
            envelope_id=uuid4(),
            envelope_version=request.envelope_version,
            correlation_id=request.correlation_id,
            causation_id=request.envelope_id,  # Causation chain linking
            source_node=response_source,
            source_node_id=source_node_id,
            target_node=response_target,
            handler_type=handler_type or request.handler_type,
            operation=response_operation,
            payload=payload,
            metadata=metadata or ModelEnvelopeMetadata(),
            timestamp=datetime.now(UTC),
            is_response=True,
            success=success,
            error=error,
        )
