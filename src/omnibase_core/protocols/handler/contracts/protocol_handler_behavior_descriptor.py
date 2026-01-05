"""
Protocol for describing handler behavior characteristics.

Domain: Handler contract type definitions for behavior semantics.

This module defines ProtocolHandlerBehaviorDescriptor which provides semantic
information about how a handler operates, enabling the runtime to make informed
decisions about caching, retrying, and scheduling.

See Also:
    - protocol_handler_contract.py: Uses behavior descriptors for contract specs
    - protocol_execution_constraints.py: Defines retry limits when retry_safe is True
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolHandlerBehaviorDescriptor(Protocol):
    """
    Protocol for describing handler behavior characteristics.

    A behavior descriptor provides semantic information about how a handler
    operates, enabling the runtime to make informed decisions about caching,
    retrying, and scheduling. This information is critical for building
    reliable distributed systems where handler behavior must be predictable.

    Behavior descriptors answer key questions about a handler:
        - Can the operation be safely retried?
        - Will the same input always produce the same output?
        - Does the operation have external effects?
        - Is the operation safe to cache?

    This protocol is useful for:
        - Retry logic implementation in orchestrators
        - Cache invalidation strategies
        - Idempotency key generation
        - Side effect tracking and auditing
        - Distributed transaction coordination

    Attributes:
        idempotent: Whether calling the handler multiple times with the same
            input produces the same result without additional side effects.
        deterministic: Whether the handler produces consistent output for
            identical input, independent of when or where it runs.
        side_effects: Categories of side effects the handler may produce,
            enabling effect tracking and rollback planning.
        retry_safe: Whether the handler can be safely retried on failure
            without causing data corruption or duplicate effects.

    Example:
        ```python
        class HttpGetBehavior:
            '''Behavior descriptor for idempotent HTTP GET operations.'''

            @property
            def idempotent(self) -> bool:
                return True  # GET requests are idempotent

            @property
            def deterministic(self) -> bool:
                return False  # Response may change over time

            @property
            def side_effects(self) -> list[str]:
                return ["network"]  # Makes network calls

            @property
            def retry_safe(self) -> bool:
                return True  # Safe to retry GET requests

        behavior = HttpGetBehavior()
        assert isinstance(behavior, ProtocolHandlerBehaviorDescriptor)

        if behavior.retry_safe and behavior.idempotent:
            print("Handler is safe for automatic retry with caching")
        ```

    Note:
        The relationship between properties is important:
        - An idempotent handler is typically retry_safe
        - A deterministic handler with no side effects is cacheable
        - Side effects should be exhaustively listed for audit purposes

    See Also:
        ProtocolHandlerContract: Uses behavior descriptors for contract specs.
        ProtocolExecutionConstraints: Defines retry limits when retry_safe is True.
    """

    @property
    def idempotent(self) -> bool:
        """
        Whether the handler operation is idempotent.

        An idempotent operation can be called multiple times with the same
        input and will produce the same result without causing additional
        side effects beyond the first call.

        Idempotency Implications:
            - True: Safe to cache results, safe to retry without idempotency keys
            - False: May require idempotency keys, careful retry handling needed

        Examples of Idempotent Operations:
            - HTTP GET, PUT, DELETE (by specification)
            - Database SELECT queries
            - Setting a value (not incrementing)
            - Reading from a message queue (with acknowledgment)

        Examples of Non-Idempotent Operations:
            - HTTP POST (creates new resource each time)
            - Incrementing a counter
            - Sending an email or notification
            - Appending to a log

        Returns:
            True if the operation is idempotent, False otherwise.
        """
        ...

    @property
    def deterministic(self) -> bool:
        """
        Whether the handler produces deterministic output.

        A deterministic handler will always produce the same output given
        the same input, regardless of when or where it runs. This property
        is independent of side effects - a handler can be deterministic
        but still have side effects.

        Determinism Implications:
            - True: Results can be cached, replays produce same results
            - False: Each execution may produce different results

        Factors that Break Determinism:
            - Current time/date usage
            - Random number generation
            - External service calls with variable responses
            - System state dependencies (environment variables, etc.)

        Returns:
            True if the handler produces deterministic output, False otherwise.
        """
        ...

    @property
    def side_effects(self) -> list[str]:
        """
        List of side effect categories the handler may produce.

        Side effects represent observable interactions with the external
        world beyond returning a value. Tracking side effects enables
        proper rollback planning, audit logging, and transaction coordination.

        Common Side Effect Categories:
            - "network": Makes HTTP/TCP/UDP calls to external services
            - "filesystem": Reads or writes files
            - "database": Queries or modifies database state
            - "message_queue": Publishes or consumes messages
            - "cache": Reads or writes cache entries
            - "metrics": Emits metrics or telemetry
            - "logging": Writes to external log systems
            - "email": Sends email notifications
            - "webhook": Triggers external webhooks

        Returns:
            List of side effect category strings. An empty list indicates
            a pure computation with no external effects. The list should
            be exhaustive - omitting a side effect category may lead to
            incorrect assumptions by the runtime.
        """
        ...

    @property
    def retry_safe(self) -> bool:
        """
        Whether the handler is safe to retry on failure.

        A retry-safe handler can be re-executed after a failure without
        causing data corruption, duplicate effects, or inconsistent state.
        This property is related to but distinct from idempotency.

        Retry Safety vs Idempotency:
            - Idempotent + Retry Safe: Can retry freely (most desirable)
            - Not Idempotent + Retry Safe: May create duplicates but no corruption
            - Idempotent + Not Retry Safe: Unusual, may indicate partial failures
            - Not Idempotent + Not Retry Safe: Requires careful error handling

        Factors Affecting Retry Safety:
            - Atomic operations are generally retry safe
            - Operations with multiple steps may not be retry safe
            - External service idempotency affects retry safety

        Returns:
            True if the handler can be safely retried, False otherwise.
        """
        ...


__all__ = ["ProtocolHandlerBehaviorDescriptor"]
