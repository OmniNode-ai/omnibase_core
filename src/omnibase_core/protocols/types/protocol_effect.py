"""
ProtocolEffect - Protocol for effect nodes.

This module provides the protocol definition for nodes that implement
the EFFECT pattern with transactional side effects and resilience support.

OMN-662: Node Protocol Definitions for ONEX Four-Node Architecture.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable
from uuid import UUID

if TYPE_CHECKING:
    from omnibase_core.models.configuration.model_circuit_breaker import (
        ModelCircuitBreaker,
    )
    from omnibase_core.models.effect.model_effect_input import ModelEffectInput
    from omnibase_core.models.effect.model_effect_output import ModelEffectOutput


@runtime_checkable
class ProtocolEffect(Protocol):
    """
    Protocol for effect nodes with transaction and resilience support.

    Defines the interface for nodes that implement the EFFECT pattern
    with external I/O operations, transactional boundaries, and
    comprehensive resilience patterns.

    EFFECT nodes are:
    - Transactional: Operations can be wrapped in atomic transactions
    - Resilient: Support retry, circuit breaker, and timeout patterns
    - Rollbackable: Failed operations trigger compensating actions
    - Handler-based: Dispatch to registered effect handlers by type

    Supported Effect Types:
    - FILE_OPERATION: File system read/write
    - DATABASE_OPERATION: SQL/NoSQL queries
    - API_CALL: HTTP/gRPC requests
    - EVENT_EMISSION: Message queue publishing
    - DIRECTORY_OPERATION: Directory traversal
    - TICKET_STORAGE: Ticket system integration
    - METRICS_COLLECTION: Telemetry emission

    Example:
        class MyEffect:
            async def process(
                self,
                input_data: ModelEffectInput,
            ) -> ModelEffectOutput:
                # Execute effect with transaction support
                return ModelEffectOutput(
                    result={"status": "success"},
                    operation_id=input_data.operation_id,
                    effect_type=input_data.effect_type,
                    transaction_state=EnumTransactionState.COMMITTED,
                    processing_time_ms=25.0,
                )

        node: ProtocolEffect = MyEffect()  # Type-safe!
    """

    async def process(
        self,
        input_data: ModelEffectInput,
    ) -> ModelEffectOutput:
        """
        Execute effect operations with full resilience patterns.

        This is the core effect interface. Implementations must:
        - Accept ModelEffectInput with operation configuration
        - Return ModelEffectOutput with transaction state
        - Support retry with exponential backoff
        - Support circuit breaker patterns
        - Handle transaction rollback on failure

        Args:
            input_data: Effect input with operation_data, resilience config,
                       and optional transaction settings.

        Returns:
            Effect output with result, transaction state, and metrics.

        Raises:
            ModelOnexError: If circuit breaker is open, transaction rollback
                fails, no handler is registered for the effect type, or
                the effect operation fails after all retry attempts.
        """
        ...

    def get_circuit_breaker(self, operation_id: UUID) -> ModelCircuitBreaker:
        """
        Get or create circuit breaker for an operation.

        Circuit breakers prevent cascading failures by failing fast
        when an operation repeatedly fails. Each operation_id has
        its own circuit breaker with independent state.

        Args:
            operation_id: Unique identifier for the operation.

        Returns:
            Circuit breaker instance for the operation.
        """
        ...

    def reset_circuit_breakers(self) -> None:
        """
        Reset all circuit breakers to closed state.

        Clears failure counts and resets all circuit breakers to
        allow operations to proceed. Use during recovery or testing.
        """
        ...

    def get_registered_handlers(self) -> dict[str, bool]:
        """
        Get registration status of all known effect handlers.

        Returns a dictionary mapping handler names to their
        registration status in the DI container.

        Returns:
            Dictionary with handler names and registration booleans.
            Example: {"HTTP": True, "DB": True, "KAFKA": False}
        """
        ...

    def get_handler_registration_report(self) -> str:
        """
        Get human-readable handler registration status report.

        Returns a formatted string showing which handlers are
        registered and available for effect execution.

        Returns:
            Multi-line string report of handler status.
        """
        ...


__all__ = ["ProtocolEffect"]
