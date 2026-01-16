"""
Protocol for event destination abstraction (ISP - Interface Segregation Principle).

This module provides the ProtocolEventSink protocol definition for components
that handle event persistence to various destinations (memory, file, Kafka).

Location:
    ``omnibase_core.protocols.validation.protocol_event_sink``

Design Principles:
    - Minimal interface: Only event-writing related methods
    - Runtime checkable: Supports duck typing with @runtime_checkable
    - ISP compliant: Components that only write events don't need full bus interface
    - Async-first: All I/O operations are async for non-blocking behavior

Import Example:
    .. code-block:: python

        from omnibase_core.protocols.validation import ProtocolEventSink

        class MyFileSink:
            async def write(self, event: ModelContractValidationEventBase) -> None:
                # Write event to file
                ...

            async def flush(self) -> None:
                # Flush buffered events
                ...

            async def close(self) -> None:
                # Close file handle
                ...

            @property
            def sink_type(self) -> str:
                return "file"

            @property
            def is_ready(self) -> bool:
                return True

See Also:
    - :class:`ModelEventDestination`: Configuration for event destinations
    - :class:`ServiceContractValidationEventEmitter`: Emitter using sinks
    - :class:`ModelContractValidationEventBase`: Base event type

.. versionadded:: 0.4.0
    Initial implementation as part of OMN-1151 event emitter service.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.models.events.contract_validation import (
        ModelContractValidationEventBase,
    )

__all__ = ["ProtocolEventSink"]


@runtime_checkable
class ProtocolEventSink(Protocol):
    """
    Protocol for event destination abstraction.

    This is a minimal interface for components that write events to various
    destinations (memory, file, Kafka, etc.). It follows the Interface
    Segregation Principle (ISP) by separating event writing concerns from
    subscription and lifecycle management.

    Use Cases:
        - Memory sink for testing and in-process event collection
        - File sink for persistent JSONL event logging
        - Kafka sink for distributed event streaming (future)

    Thread Safety:
        Implementations should document their thread safety guarantees.
        Memory sinks are typically not thread-safe; file and Kafka sinks
        may provide thread-safe implementations.

    Example:
        >>> from omnibase_core.protocols.validation import ProtocolEventSink
        >>>
        >>> class MyMemorySink:
        ...     def __init__(self) -> None:
        ...         self._events: list[ModelContractValidationEventBase] = []
        ...         self._ready = True
        ...
        ...     async def write(self, event: ModelContractValidationEventBase) -> None:
        ...         self._events.append(event)
        ...
        ...     async def flush(self) -> None:
        ...         pass  # No-op for memory
        ...
        ...     async def close(self) -> None:
        ...         self._ready = False
        ...
        ...     @property
        ...     def sink_type(self) -> str:
        ...         return "memory"
        ...
        ...     @property
        ...     def is_ready(self) -> bool:
        ...         return self._ready
        >>>
        >>> # Verify protocol compliance
        >>> sink = MyMemorySink()
        >>> isinstance(sink, ProtocolEventSink)
        True

    .. versionadded:: 0.4.0
    """

    async def write(self, event: ModelContractValidationEventBase) -> None:
        """
        Write a single event to the destination.

        This method may buffer events internally for performance. Call
        :meth:`flush` to ensure all buffered events are persisted.

        Args:
            event: The contract validation event to write.

        Raises:
            ModelOnexError: If writing fails (I/O error, serialization, etc.).

        Note:
            Implementations should handle serialization internally.
            Events are Pydantic models with built-in JSON serialization.
        """
        ...

    async def flush(self) -> None:
        """
        Flush any buffered events to the destination.

        This ensures all previously written events are persisted to the
        underlying storage. For unbuffered sinks (like memory), this
        may be a no-op.

        Raises:
            ModelOnexError: If flushing fails (I/O error, connection lost, etc.).
        """
        ...

    async def close(self) -> None:
        """
        Close the sink and release any resources.

        After calling close, the sink should not accept any more writes.
        The :attr:`is_ready` property should return False after close.

        This method should be idempotent - calling close multiple times
        should not raise errors.

        Raises:
            ModelOnexError: If closing fails (though implementations should
                try to close gracefully even on error).
        """
        ...

    @property
    def sink_type(self) -> str:
        """
        Return the type of this sink.

        Returns:
            str: One of "memory", "file", "kafka", or custom type.

        Note:
            This is used for diagnostic logging and sink selection.
        """
        ...

    @property
    def is_ready(self) -> bool:
        """
        Check if the sink is ready to accept writes.

        Returns:
            bool: True if the sink can accept writes, False otherwise.

        Note:
            Returns False after :meth:`close` is called or if the sink
            encounters an unrecoverable error.
        """
        ...
