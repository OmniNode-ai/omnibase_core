"""
Contract validation event emitter service.

This module provides a service for emitting contract validation events to
configurable destinations (memory, file, Kafka). It implements the sink
abstraction pattern for flexible event routing.

Location:
    ``omnibase_core.services.service_contract_validation_event_emitter``

Design Notes:
    - Supports multiple concurrent destinations
    - Memory sink for testing and in-process collection
    - File sink for persistent JSONL event logging
    - Correlation ID propagation for request tracing
    - Async-first design for non-blocking I/O

Import Example:
    .. code-block:: python

        from omnibase_core.services.service_contract_validation_event_emitter import (
            ServiceContractValidationEventEmitter,
        )
        from omnibase_core.models.validation.model_event_destination import (
            ModelEventDestination,
        )

        # Create emitter with memory destination
        emitter = ServiceContractValidationEventEmitter(
            destinations=[ModelEventDestination.create_memory()],
        )

        # Emit an event
        await emitter.emit(validation_started_event)

        # Get events from memory sink
        events = emitter.get_events("memory")

See Also:
    - :class:`ProtocolEventSink`: Protocol for event sinks
    - :class:`ModelEventDestination`: Destination configuration
    - :class:`ModelContractValidationEventBase`: Base event type

.. versionadded:: 0.4.0
    Initial implementation as part of OMN-1151 event emitter service.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_event_sink_type import EnumEventSinkType
from omnibase_core.errors import ModelOnexError
from omnibase_core.models.validation.model_event_destination import (
    ModelEventDestination,
)
from omnibase_core.services.sinks import ServiceFileSink, ServiceMemorySink

if TYPE_CHECKING:
    from omnibase_core.models.events.contract_validation import (
        ModelContractValidationEventBase,
    )

__all__ = [
    "ServiceContractValidationEventEmitter",
    "ServiceFileSink",
    "ServiceMemorySink",
]


class ServiceContractValidationEventEmitter:
    """
    Contract validation event emitter service.

    Emits contract validation events to configurable destinations.
    Supports memory sinks for testing, file sinks for persistent logging,
    and (future) Kafka sinks for distributed streaming.

    Attributes:
        correlation_id: Optional correlation ID for request tracing.

    Thread Safety:
        This service is NOT thread-safe. The internal sink list and sink
        instances can be modified during emit operations. Use separate
        emitter instances per thread, or ensure all configuration is
        complete before concurrent use.

    Example:
        >>> from omnibase_core.services.service_contract_validation_event_emitter import (
        ...     ServiceContractValidationEventEmitter,
        ... )
        >>> from omnibase_core.models.validation.model_event_destination import (
        ...     ModelEventDestination,
        ... )
        >>>
        >>> # Create emitter with memory and file destinations
        >>> emitter = ServiceContractValidationEventEmitter(
        ...     destinations=[
        ...         ModelEventDestination.create_memory(),
        ...         ModelEventDestination.create_file(
        ...             name="log",
        ...             file_path="/tmp/events.jsonl",
        ...         ),
        ...     ],
        ...     correlation_id=uuid4(),
        ... )
        >>>
        >>> # Emit event
        >>> await emitter.emit(validation_started_event)
        >>>
        >>> # Get memory events
        >>> events = emitter.get_events("memory")
        >>>
        >>> # Cleanup
        >>> await emitter.close()

    .. versionadded:: 0.4.0
    """

    def __init__(
        self,
        destinations: list[ModelEventDestination] | None = None,
        correlation_id: UUID | None = None,
    ) -> None:
        """
        Initialize the event emitter.

        Args:
            destinations: List of event destinations. If None, creates a
                default memory destination.
            correlation_id: Optional correlation ID for request tracing.
                Will be propagated to all emitted events.
        """
        self._correlation_id = correlation_id
        self._sinks: dict[str, ServiceMemorySink | ServiceFileSink] = {}
        self._destinations = destinations or [ModelEventDestination.create_memory()]
        self._emit_count = 0
        self._last_emit_time: datetime | None = None
        self._closed = False

        # Initialize sinks for enabled destinations
        for dest in self._destinations:
            if dest.enabled:
                self._create_sink(dest)

    def _create_sink(self, dest: ModelEventDestination) -> None:
        """
        Create a sink for the given destination.

        Args:
            dest: Destination configuration.

        Raises:
            ModelOnexError: If sink creation fails or type is unsupported.
        """
        if dest.destination_type == EnumEventSinkType.MEMORY:
            self._sinks[dest.destination_name] = ServiceMemorySink(
                name=dest.destination_name
            )

        elif dest.destination_type == EnumEventSinkType.FILE:
            if not dest.file_path:
                raise ModelOnexError(
                    message="file_path required for file destination",
                    error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
                    destination_name=dest.destination_name,
                )
            self._sinks[dest.destination_name] = ServiceFileSink(
                name=dest.destination_name,
                file_path=Path(dest.file_path),
                buffer_size=dest.buffer_size,
            )

        elif dest.destination_type == EnumEventSinkType.KAFKA:
            # Kafka sink reserved for future implementation
            raise ModelOnexError(
                message="Kafka sink not yet implemented",
                error_code=EnumCoreErrorCode.METHOD_NOT_IMPLEMENTED,
                destination_name=dest.destination_name,
            )

        else:
            raise ModelOnexError(
                message=f"Unsupported destination type: {dest.destination_type}",
                error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
                destination_name=dest.destination_name,
                destination_type=str(dest.destination_type),
            )

    @property
    def correlation_id(self) -> UUID | None:
        """Get the correlation ID."""
        return self._correlation_id

    @correlation_id.setter
    def correlation_id(self, value: UUID | None) -> None:
        """Set the correlation ID for subsequent events."""
        self._correlation_id = value

    @property
    def emit_count(self) -> int:
        """Get the total number of events emitted."""
        return self._emit_count

    @property
    def last_emit_time(self) -> datetime | None:
        """Get the timestamp of the last emitted event."""
        return self._last_emit_time

    @property
    def sink_names(self) -> list[str]:
        """Get the names of all active sinks."""
        return list(self._sinks.keys())

    async def emit(self, event: ModelContractValidationEventBase) -> None:
        """
        Emit an event to all configured destinations.

        If a correlation_id is set on this emitter and the event doesn't
        have one, the emitter's correlation_id will be propagated.

        Args:
            event: The event to emit.

        Raises:
            ModelOnexError: If emitting to any sink fails.

        Note:
            Events are emitted to all sinks. If one sink fails, the error
            is raised after attempting all sinks (fail-late behavior may
            be implemented in future versions).
        """
        if self._closed:
            raise ModelOnexError(
                message="Cannot emit events: emitter is closed",
                error_code=EnumCoreErrorCode.INVALID_OPERATION,
            )

        if not self._sinks:
            raise ModelOnexError(
                message="No active sinks configured",
                error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
            )

        # Propagate correlation ID if not set on event
        event_to_emit = event
        if self._correlation_id and event.correlation_id is None:
            # Create a new event with the correlation_id set
            # Since events are frozen, we need to create a copy
            event_data = event.model_dump()
            event_data["correlation_id"] = self._correlation_id
            event_to_emit = type(event).model_validate(event_data)

        # Emit to all sinks
        errors: list[tuple[str, Exception]] = []
        for sink_name, sink in self._sinks.items():
            if sink.is_ready:
                try:
                    await sink.write(event_to_emit)
                except asyncio.CancelledError:
                    # CRITICAL: Re-raise CancelledError to honor task cancellation.
                    # Cancellation should not be collected - it must propagate immediately.
                    raise
                except Exception as e:  # catch-all-ok: collect all errors
                    errors.append((sink_name, e))

        self._emit_count += 1
        self._last_emit_time = datetime.now(UTC)

        # Report first error if any occurred
        if errors:
            sink_name, first_error = errors[0]
            if isinstance(first_error, ModelOnexError):
                raise first_error
            raise ModelOnexError(
                message=f"Failed to emit event to sink '{sink_name}': {first_error}",
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                sink_name=sink_name,
                failed_sinks=[name for name, _ in errors],
            ) from first_error

    async def flush(self) -> None:
        """
        Flush all sinks.

        Ensures all buffered events are persisted to their destinations.

        Raises:
            ModelOnexError: If flushing any sink fails.
        """
        errors: list[tuple[str, Exception]] = []
        for sink_name, sink in self._sinks.items():
            if sink.is_ready:
                try:
                    await sink.flush()
                except asyncio.CancelledError:
                    # CRITICAL: Re-raise CancelledError to honor task cancellation.
                    # Cancellation should not be collected - it must propagate immediately.
                    raise
                except Exception as e:  # catch-all-ok: collect all errors
                    errors.append((sink_name, e))

        if errors:
            sink_name, first_error = errors[0]
            if isinstance(first_error, ModelOnexError):
                raise first_error
            raise ModelOnexError(
                message=f"Failed to flush sink '{sink_name}': {first_error}",
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                sink_name=sink_name,
            ) from first_error

    async def close(self) -> None:
        """
        Close all sinks.

        Flushes remaining events and releases resources. After close,
        no more events can be emitted.

        Raises:
            ModelOnexError: If closing any sink fails.
        """
        errors: list[tuple[str, Exception]] = []
        for sink_name, sink in self._sinks.items():
            try:
                await sink.close()
            except asyncio.CancelledError:
                # CRITICAL: Re-raise CancelledError to honor task cancellation.
                # Mark as closed before propagating to indicate partial cleanup.
                self._closed = True
                raise
            except Exception as e:  # catch-all-ok: ensure all sinks closed
                errors.append((sink_name, e))

        # Mark as closed regardless of errors
        self._closed = True

        if errors:
            sink_name, first_error = errors[0]
            if isinstance(first_error, ModelOnexError):
                raise first_error
            raise ModelOnexError(
                message=f"Failed to close sink '{sink_name}': {first_error}",
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                sink_name=sink_name,
            ) from first_error

    def get_events(
        self, sink_name: str = "memory"
    ) -> list[ModelContractValidationEventBase]:
        """
        Get events from a memory sink.

        Args:
            sink_name: Name of the memory sink. Defaults to "memory".

        Returns:
            list: Copy of all events in the specified sink.

        Raises:
            ModelOnexError: If sink not found or is not a memory sink.
        """
        sink = self._sinks.get(sink_name)
        if sink is None:
            raise ModelOnexError(
                message=f"Sink '{sink_name}' not found",
                error_code=EnumCoreErrorCode.NOT_FOUND,
                sink_name=sink_name,
                available_sinks=list(self._sinks.keys()),
            )

        if not isinstance(sink, ServiceMemorySink):
            raise ModelOnexError(
                message=f"Sink '{sink_name}' is not a memory sink",
                error_code=EnumCoreErrorCode.INVALID_OPERATION,
                sink_name=sink_name,
                sink_type=sink.sink_type,
            )

        return sink.get_events()

    def clear_events(self, sink_name: str = "memory") -> None:
        """
        Clear events from a memory sink.

        Args:
            sink_name: Name of the memory sink. Defaults to "memory".

        Raises:
            ModelOnexError: If sink not found or is not a memory sink.
        """
        sink = self._sinks.get(sink_name)
        if sink is None:
            raise ModelOnexError(
                message=f"Sink '{sink_name}' not found",
                error_code=EnumCoreErrorCode.NOT_FOUND,
                sink_name=sink_name,
            )

        if not isinstance(sink, ServiceMemorySink):
            raise ModelOnexError(
                message=f"Sink '{sink_name}' is not a memory sink",
                error_code=EnumCoreErrorCode.INVALID_OPERATION,
                sink_name=sink_name,
                sink_type=sink.sink_type,
            )

        sink.clear()

    def get_sink_stats(self) -> dict[str, dict[str, int | bool | str]]:
        """
        Get statistics for all sinks.

        Returns:
            dict: Mapping of sink name to stats dict with keys:
                - type: Sink type (memory, file, kafka)
                - ready: Whether sink is ready
                - event_count: Number of events written
                - buffer_count: Number of events in buffer (file only)
        """
        stats: dict[str, dict[str, int | bool | str]] = {}
        for sink_name, sink in self._sinks.items():
            sink_stats: dict[str, int | bool | str] = {
                "type": sink.sink_type,
                "ready": sink.is_ready,
                "event_count": sink.event_count,
            }
            if isinstance(sink, ServiceFileSink):
                sink_stats["buffer_count"] = sink.buffer_count
            stats[sink_name] = sink_stats
        return stats
