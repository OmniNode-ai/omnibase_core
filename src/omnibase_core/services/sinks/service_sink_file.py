"""
File-based event sink for contract validation events.

Location:
    ``omnibase_core.services.sinks.service_sink_file``

.. versionadded:: 0.4.0
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_event_sink_type import EnumEventSinkType
from omnibase_core.errors import ModelOnexError

if TYPE_CHECKING:
    from omnibase_core.models.events.contract_validation import (
        ModelContractValidationEventBase,
    )

__all__ = ["ServiceFileSink"]


class ServiceFileSink:
    """
    File-based event sink for persistent JSONL logging.

    Writes events as newline-delimited JSON (JSONL format) to a file.
    Supports buffered writing with configurable flush intervals.

    Attributes:
        name: Unique identifier for this sink.
        file_path: Path to the output file.

    Thread Safety:
        This sink is NOT thread-safe. Use thread-local instances or
        external synchronization for concurrent access.

    Example:
        >>> sink = ServiceFileSink(
        ...     name="events",
        ...     file_path=Path("/tmp/events.jsonl"),
        ... )
        >>> await sink.write(event)
        >>> await sink.flush()
        >>> await sink.close()

    .. versionadded:: 0.4.0
    """

    def __init__(
        self,
        name: str,
        file_path: Path,
        buffer_size: int = 100,
    ) -> None:
        """
        Initialize the file sink.

        Args:
            name: Unique identifier for this sink.
            file_path: Path to the output file.
            buffer_size: Number of events to buffer before auto-flush.
        """
        self._name = name
        self._file_path = file_path
        self._buffer_size = buffer_size
        self._buffer: list[str] = []
        self._ready = True
        self._event_count = 0

    async def write(self, event: ModelContractValidationEventBase) -> None:
        """
        Write an event to the buffer.

        Args:
            event: The event to write.

        Raises:
            ModelOnexError: If the sink is closed or serialization fails.
        """
        if not self._ready:
            raise ModelOnexError(
                message=f"File sink '{self._name}' is closed",
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                sink_name=self._name,
            )

        try:
            # Serialize event to JSON
            # mode="json" ensures UUIDs and other types are serialized correctly
            event_dict = event.model_dump(mode="json")
            json_line = json.dumps(event_dict, default=str, ensure_ascii=False)
            self._buffer.append(json_line)
            self._event_count += 1

            # Auto-flush if buffer is full
            if len(self._buffer) >= self._buffer_size:
                await self.flush()

        except (TypeError, ValueError) as e:
            raise ModelOnexError(
                message=f"Failed to serialize event: {e}",
                error_code=EnumCoreErrorCode.CONVERSION_ERROR,
                sink_name=self._name,
                event_type=type(event).__name__,
            ) from e

    async def flush(self) -> None:
        """
        Flush buffered events to file.

        Writes all buffered events to the file and clears the buffer.

        Raises:
            ModelOnexError: If writing to file fails.
        """
        if not self._buffer:
            return

        try:
            # Ensure parent directory exists
            self._file_path.parent.mkdir(parents=True, exist_ok=True)

            # Append to file
            with self._file_path.open("a", encoding="utf-8") as f:
                for line in self._buffer:
                    f.write(line + "\n")

            self._buffer.clear()

        except OSError as e:
            raise ModelOnexError(
                message=f"Failed to write to file: {e}",
                error_code=EnumCoreErrorCode.FILE_WRITE_ERROR,
                sink_name=self._name,
                file_path=str(self._file_path),
            ) from e

    async def close(self) -> None:
        """
        Close the sink after flushing remaining events.

        Raises:
            ModelOnexError: If final flush fails.
        """
        try:
            await self.flush()
        finally:
            self._ready = False

    @property
    def sink_type(self) -> str:
        """Return the sink type."""
        return EnumEventSinkType.FILE.value

    @property
    def is_ready(self) -> bool:
        """Check if the sink is ready."""
        return self._ready

    @property
    def event_count(self) -> int:
        """Return the total number of events written."""
        return self._event_count

    @property
    def buffer_count(self) -> int:
        """Return the number of events in the buffer."""
        return len(self._buffer)
