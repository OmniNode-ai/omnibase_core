"""
Event destination configuration model.

This module provides the configuration model for event destinations,
supporting memory, file, and Kafka sink types with appropriate settings
for each destination type.

Location:
    ``omnibase_core.models.validation.model_event_destination``

Design Notes:
    - Follows the pattern from ModelLogDestination for consistency
    - Immutable (frozen) to ensure configuration integrity
    - Factory methods for common destination types
    - Validation ensures required fields per destination type

Import Example:
    .. code-block:: python

        from omnibase_core.models.validation.model_event_destination import (
            ModelEventDestination,
        )

        # Create memory destination for testing
        memory_dest = ModelEventDestination.create_memory()

        # Create file destination for persistent logging
        file_dest = ModelEventDestination.create_file(
            name="validation-events",
            file_path="/var/log/validation-events.jsonl",
        )

        # Create Kafka destination (future)
        kafka_dest = ModelEventDestination.create_kafka(
            name="kafka-events",
            topic="contract.validation.events",
            bootstrap_servers="192.168.86.200:29092",
        )

See Also:
    - :class:`ProtocolEventSink`: Protocol for event sinks
    - :class:`EnumEventSinkType`: Event sink type enumeration
    - :class:`ServiceContractValidationEventEmitter`: Event emitter service
    - :class:`ModelLogDestination`: Similar pattern for log destinations

.. versionadded:: 0.4.0
    Initial implementation as part of OMN-1151 event emitter service.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_event_sink_type import EnumEventSinkType

__all__ = ["ModelEventDestination"]


class ModelEventDestination(BaseModel):
    """
    Event destination configuration model.

    Configures where contract validation events should be sent. Supports
    memory (for testing), file (for persistent logging), and Kafka
    (for distributed streaming) destinations.

    Attributes:
        destination_type: Type of destination (memory, file, kafka).
        destination_name: Unique identifier for this destination.
        enabled: Whether this destination is enabled.
        file_path: File path for file destinations.
        topic: Kafka topic for Kafka destinations.
        bootstrap_servers: Kafka bootstrap servers for Kafka destinations.
        buffer_size: Number of events to buffer before auto-flush. Default of 100
            balances memory usage vs I/O frequency.
        flush_interval_ms: Flush interval in milliseconds. Default of 5000ms
            ensures events are persisted within reasonable time even under low load.

    Example:
        >>> from omnibase_core.models.validation.model_event_destination import (
        ...     ModelEventDestination,
        ... )
        >>>
        >>> # Memory destination for testing
        >>> memory = ModelEventDestination.create_memory()
        >>> memory.destination_type
        <EnumEventSinkType.MEMORY: 'memory'>
        >>>
        >>> # File destination
        >>> file_dest = ModelEventDestination.create_file(
        ...     name="events",
        ...     file_path="/tmp/events.jsonl",
        ... )
        >>> file_dest.file_path
        '/tmp/events.jsonl'

    Thread Safety:
        This model is immutable (frozen) and thus thread-safe for reads.
        No mutable state after construction.

    .. versionadded:: 0.4.0
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        use_enum_values=False,
    )

    destination_type: EnumEventSinkType = Field(
        ...,
        description="Type of event destination (memory, file, kafka).",
    )

    destination_name: str = Field(
        ...,
        description="Unique identifier for this destination.",
        min_length=1,
        max_length=255,
    )

    enabled: bool = Field(
        default=True,
        description="Whether this destination is enabled.",
    )

    file_path: str | None = Field(
        default=None,
        description="File path for file destinations. Required when "
        "destination_type is FILE.",
    )

    topic: str | None = Field(
        default=None,
        description="Kafka topic for Kafka destinations. Required when "
        "destination_type is KAFKA.",
    )

    bootstrap_servers: str | None = Field(
        default=None,
        description="Kafka bootstrap servers (comma-separated). Required when "
        "destination_type is KAFKA.",
    )

    buffer_size: int = Field(
        default=100,
        description="Number of events to buffer before auto-flush. Default of 100 "
        "balances memory usage vs I/O frequency. Increase for high-throughput "
        "scenarios (reduces I/O overhead), decrease for low-latency scenarios "
        "(faster persistence). Range: 1-10000.",
        ge=1,
        le=10000,
    )

    flush_interval_ms: int = Field(
        default=5000,
        description="Flush interval in milliseconds. Events are flushed when buffer "
        "is full or this interval elapses, whichever comes first. Default of 5000ms "
        "(5 seconds) ensures events are persisted within reasonable time even under "
        "low load. Decrease for lower latency (more frequent I/O), increase for "
        "higher throughput (batches more events). Range: 100-60000ms.",
        ge=100,
        le=60000,
    )

    @model_validator(mode="after")
    def validate_destination_requirements(self) -> ModelEventDestination:
        """
        Validate that required fields are present for each destination type.

        Raises:
            ValueError: If required fields are missing for the destination type.
        """
        if self.destination_type == EnumEventSinkType.FILE:
            if not self.file_path:
                msg = "file_path is required for FILE destination type"
                raise ValueError(msg)

        if self.destination_type == EnumEventSinkType.KAFKA:
            if not self.topic:
                msg = "topic is required for KAFKA destination type"
                raise ValueError(msg)
            if not self.bootstrap_servers:
                msg = "bootstrap_servers is required for KAFKA destination type"
                raise ValueError(msg)

        return self

    def is_persistent(self) -> bool:
        """
        Check if this destination provides persistent storage.

        Returns:
            bool: True for file and Kafka destinations, False for memory.
        """
        return self.destination_type.is_persistent

    def requires_connection(self) -> bool:
        """
        Check if this destination requires a network connection.

        Returns:
            bool: True for Kafka destination, False otherwise.
        """
        return self.destination_type.requires_connection

    @classmethod
    def create_memory(
        cls,
        name: str = "memory",
        buffer_size: int = 100,
    ) -> ModelEventDestination:
        """
        Factory method for memory destination.

        Creates an in-memory event destination suitable for testing
        and process-local event collection.

        Args:
            name: Unique identifier for this destination. Defaults to "memory".
            buffer_size: Buffer size for event storage. Defaults to 100.

        Returns:
            ModelEventDestination: Configured memory destination.

        Example:
            >>> dest = ModelEventDestination.create_memory()
            >>> dest.destination_type
            <EnumEventSinkType.MEMORY: 'memory'>
        """
        return cls(
            destination_type=EnumEventSinkType.MEMORY,
            destination_name=name,
            buffer_size=buffer_size,
        )

    @classmethod
    def create_file(
        cls,
        name: str,
        file_path: str,
        buffer_size: int = 100,
        flush_interval_ms: int = 5000,
    ) -> ModelEventDestination:
        """
        Factory method for file destination.

        Creates a file-based event destination that writes events
        as newline-delimited JSON (JSONL format).

        Args:
            name: Unique identifier for this destination.
            file_path: Path to the output file.
            buffer_size: Buffer size before flush. Defaults to 100.
            flush_interval_ms: Flush interval in milliseconds. Defaults to 5000.

        Returns:
            ModelEventDestination: Configured file destination.

        Example:
            >>> dest = ModelEventDestination.create_file(
            ...     name="events",
            ...     file_path="/var/log/events.jsonl",
            ... )
            >>> dest.file_path
            '/var/log/events.jsonl'
        """
        return cls(
            destination_type=EnumEventSinkType.FILE,
            destination_name=name,
            file_path=file_path,
            buffer_size=buffer_size,
            flush_interval_ms=flush_interval_ms,
        )

    @classmethod
    def create_kafka(
        cls,
        name: str,
        topic: str,
        bootstrap_servers: str,
        buffer_size: int = 100,
        flush_interval_ms: int = 1000,
    ) -> ModelEventDestination:
        """
        Factory method for Kafka destination.

        Creates a Kafka-based event destination for distributed event
        streaming. Note: Kafka sink implementation is reserved for future.

        Args:
            name: Unique identifier for this destination.
            topic: Kafka topic to publish events to.
            bootstrap_servers: Kafka bootstrap servers (comma-separated).
            buffer_size: Buffer size before flush. Defaults to 100.
            flush_interval_ms: Flush interval in milliseconds. Defaults to 1000.

        Returns:
            ModelEventDestination: Configured Kafka destination.

        Example:
            >>> dest = ModelEventDestination.create_kafka(
            ...     name="kafka-events",
            ...     topic="contract.validation.events",
            ...     bootstrap_servers="192.168.86.200:29092",
            ... )
            >>> dest.topic
            'contract.validation.events'
        """
        return cls(
            destination_type=EnumEventSinkType.KAFKA,
            destination_name=name,
            topic=topic,
            bootstrap_servers=bootstrap_servers,
            buffer_size=buffer_size,
            flush_interval_ms=flush_interval_ms,
        )
