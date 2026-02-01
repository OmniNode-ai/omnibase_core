"""
In-memory event sink for contract validation events.

Location:
    ``omnibase_core.services.sinks.service_sink_memory``

.. versionadded:: 0.4.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_event_sink_type import EnumEventSinkType
from omnibase_core.errors import ModelOnexError

if TYPE_CHECKING:
    from omnibase_core.models.events.contract_validation import (
        ModelContractValidationEventBase,
    )

__all__ = ["ServiceMemorySink"]


class ServiceMemorySink:
    """
    In-memory event sink for testing and process-local collection.

    Stores events in an internal list that can be retrieved programmatically.
    Useful for testing and scenarios where events need to be processed
    within the same process.

    Attributes:
        name: Unique identifier for this sink.

    Thread Safety:
        This sink is NOT thread-safe. Use thread-local instances or
        external synchronization for concurrent access.

    Event Ordering:
        Events are stored in insertion order. Calls to `get_events()` return
        events in the same order they were written, enabling deterministic
        replay and testing of event sequences.

    Example:
        >>> sink = ServiceMemorySink(name="test")
        >>> await sink.write(event)
        >>> events = sink.get_events()
        >>> len(events)
        1

    .. versionadded:: 0.4.0
    """

    def __init__(self, name: str = "memory") -> None:
        """
        Initialize the memory sink.

        Args:
            name: Unique identifier for this sink.
        """
        self._name = name
        self._events: list[ModelContractValidationEventBase] = []
        self._ready = True

    async def write(self, event: ModelContractValidationEventBase) -> None:
        """
        Write an event to memory.

        Args:
            event: The event to store.

        Raises:
            ModelOnexError: If the sink is closed.
        """
        if not self._ready:
            raise ModelOnexError(
                message=f"Memory sink '{self._name}' is closed",
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                sink_name=self._name,
            )
        self._events.append(event)

    async def flush(self) -> None:  # stub-ok: intentional no-op
        """Flush is a no-op for memory sink."""
        return  # Memory sink doesn't need flushing

    async def close(self) -> None:
        """Close the sink, preventing further writes."""
        self._ready = False

    @property
    def sink_type(self) -> str:
        """Return the sink type."""
        return EnumEventSinkType.MEMORY.value

    @property
    def is_ready(self) -> bool:
        """Check if the sink is ready."""
        return self._ready

    def get_events(self) -> list[ModelContractValidationEventBase]:
        """
        Get all stored events.

        Returns:
            list: Copy of all stored events.
        """
        return list(self._events)

    def clear(self) -> None:
        """Clear all stored events."""
        self._events.clear()

    @property
    def event_count(self) -> int:
        """Return the number of stored events."""
        return len(self._events)
