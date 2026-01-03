"""
HandlerLocal - Echo handler for development and testing.

WARNING: This handler is for development and testing purposes ONLY.
         DO NOT use in production environments.

This handler provides simple echo, transform, and error operations for
testing the ONEX runtime without requiring external dependencies. It
enables rapid iteration during development and comprehensive testing
of the runtime's envelope routing and handler execution.

Supported Operations:
    - echo: Returns the input payload unchanged
    - transform: Applies simple transformations (uppercase strings, double numbers)
    - error: Deliberately returns an error envelope for testing error handling

Usage:
    .. code-block:: python

        from omnibase_core.runtime.handlers import HandlerLocal

        handler = HandlerLocal()

        # Echo operation
        envelope = ModelOnexEnvelope.create_request(
            operation="echo",
            payload={"message": "hello"},
            source_node="test_client",
        )
        response = await handler.execute(envelope)
        # response.payload == {"message": "hello"}

        # Transform operation
        envelope = ModelOnexEnvelope.create_request(
            operation="transform",
            payload={"text": "hello", "count": 5},
            source_node="test_client",
        )
        response = await handler.execute(envelope)
        # response.payload == {"text": "HELLO", "count": 10}

Related:
    - OMN-230: HandlerLocal implementation
    - ProtocolHandler: Protocol interface for handlers
    - EnumHandlerType.LOCAL: Handler type classification

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = ["HandlerLocal"]

from omnibase_core.enums.enum_handler_type import EnumHandlerType
from omnibase_core.enums.enum_log_level import EnumLogLevel
from omnibase_core.logging.logging_structured import emit_log_event_sync
from omnibase_core.models.core.model_onex_envelope import ModelOnexEnvelope
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types.type_serializable_value import SerializedDict
from omnibase_core.types.typed_dict_handler_metadata import TypedDictHandlerMetadata
from omnibase_core.types.typed_dict_health_check_result import (
    TypedDictHealthCheckResult,
)


class HandlerLocal:
    """
    Local echo handler for development and testing purposes.

    WARNING: This handler is for development and testing purposes ONLY.
             DO NOT use in production environments. It has no security,
             authentication, or audit capabilities.

    This handler implements the ProtocolHandler protocol and provides
    simple operations for testing the ONEX runtime:

    - **echo**: Returns the input payload unchanged in the response
    - **transform**: Applies simple transformations to payload values:
        - Strings are uppercased
        - Numbers are doubled
        - Other types are passed through unchanged
    - **error**: Returns an error envelope for testing error handling

    Thread Safety:
        This handler is stateless and thread-safe. It can be safely shared
        across multiple coroutines without synchronization.

    Attributes:
        handler_type: Returns EnumHandlerType.LOCAL

    Example:
        .. code-block:: python

            from omnibase_core.runtime.handlers import HandlerLocal

            handler = HandlerLocal()

            # Verify protocol compliance
            from omnibase_core.protocols.runtime import ProtocolHandler
            assert isinstance(handler, ProtocolHandler)

            # Execute echo operation
            request = ModelOnexEnvelope.create_request(
                operation="echo",
                payload={"data": "test"},
                source_node="client",
            )
            response = await handler.execute(request)
            assert response.success is True
            assert response.payload == {"data": "test"}

    .. versionadded:: 0.4.0
    """

    def __init__(self) -> None:
        """
        Initialize the HandlerLocal.

        Logs a warning on initialization to remind developers that this
        handler should not be used in production environments.
        """
        emit_log_event_sync(
            level=EnumLogLevel.WARNING,
            message=(
                "HandlerLocal initialized. This handler is for dev/test only. "
                "DO NOT use in production environments."
            ),
            context={
                "handler_type": EnumHandlerType.LOCAL.value,
                "dev_test_only": True,
            },
        )

    @property
    def handler_type(self) -> EnumHandlerType:
        """
        Return the handler type classification.

        Returns:
            EnumHandlerType: Always returns EnumHandlerType.LOCAL.
        """
        return EnumHandlerType.LOCAL

    async def execute(self, envelope: ModelOnexEnvelope) -> ModelOnexEnvelope:
        """
        Execute handler logic for the given envelope.

        Processes the envelope based on the operation field:
        - "echo": Returns payload unchanged
        - "transform": Applies transformations to payload values
        - "error": Returns an error envelope
        - Any other operation: Returns success with echo behavior

        Args:
            envelope: The input envelope containing the operation request.
                The operation field determines the behavior, and the
                payload contains the data to process.

        Returns:
            ModelOnexEnvelope: The response envelope containing the result.
                Uses create_response() for proper causation chain tracking.
        """
        operation = envelope.operation.lower()

        if operation == "echo":
            return self._handle_echo(envelope)
        elif operation == "transform":
            return self._handle_transform(envelope)
        elif operation == "error":
            return self._handle_error(envelope)
        else:
            # Default to echo behavior for unknown operations
            return self._handle_echo(envelope)

    def _handle_echo(self, envelope: ModelOnexEnvelope) -> ModelOnexEnvelope:
        """
        Handle echo operation - return payload unchanged.

        Args:
            envelope: The input envelope.

        Returns:
            ModelOnexEnvelope: Response with the same payload.
        """
        return ModelOnexEnvelope.create_response(
            request=envelope,
            payload=envelope.payload.copy(),
            success=True,
        )

    def _handle_transform(self, envelope: ModelOnexEnvelope) -> ModelOnexEnvelope:
        """
        Handle transform operation - apply simple transformations.

        Transformations applied:
        - Strings: Converted to uppercase
        - Numbers (int/float): Doubled
        - Other types: Passed through unchanged

        Args:
            envelope: The input envelope with payload to transform.

        Returns:
            ModelOnexEnvelope: Response with transformed payload.
        """
        transformed_payload: SerializedDict = {}

        for key, value in envelope.payload.items():
            if isinstance(value, str):
                transformed_payload[key] = value.upper()
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                transformed_payload[key] = value * 2
            else:
                transformed_payload[key] = value

        return ModelOnexEnvelope.create_response(
            request=envelope,
            payload=transformed_payload,
            success=True,
        )

    def _handle_error(self, envelope: ModelOnexEnvelope) -> ModelOnexEnvelope:
        """
        Handle error operation - return an error envelope.

        This operation deliberately returns an error for testing
        error handling in the runtime.

        Args:
            envelope: The input envelope.

        Returns:
            ModelOnexEnvelope: Error response with success=False.
        """
        error_message = envelope.payload.get(
            "error_message", "Deliberate error for testing"
        )
        if not isinstance(error_message, str):
            error_message = str(error_message)

        return ModelOnexEnvelope.create_response(
            request=envelope,
            payload={},
            success=False,
            error=error_message,
        )

    def describe(self) -> TypedDictHandlerMetadata:
        """
        Return handler metadata for registration and discovery.

        Returns:
            TypedDictHandlerMetadata: Handler metadata with:
                - name: "local_handler"
                - version: 1.0.0
                - description: Handler purpose (includes dev/test warning)
                - capabilities: ["echo", "transform", "error"]
        """
        return {
            "name": "handler_local",
            "version": ModelSemVer(major=1, minor=0, patch=0),
            "description": (
                "Local echo handler for dev/test only. WARNING: Not for production use."
            ),
            "capabilities": ["echo", "transform", "error"],
        }

    def health_check(self) -> TypedDictHealthCheckResult:
        """
        Perform a health check on the handler.

        This method is used for monitoring and observability.
        For HandlerLocal, it always returns healthy with a flag
        indicating this is a dev/test-only handler.

        Returns:
            TypedDictHealthCheckResult: Health check result with:
                - dev_test_only: True (always)
                - status: "healthy" (always, since no external deps)
        """
        return {
            "dev_test_only": True,
            "status": "healthy",
        }
