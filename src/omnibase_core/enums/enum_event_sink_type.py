# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Event sink type enumeration.

This module defines the types of event sinks (destinations) supported
by the contract validation event emitter.

Location:
    ``omnibase_core.enums.enum_event_sink_type``

Import Example:
    .. code-block:: python

        from omnibase_core.enums import EnumEventSinkType

        sink_type = EnumEventSinkType.FILE
        print(sink_type.value)  # "file"

See Also:
    - :class:`ProtocolEventSink`: Protocol for event sinks
    - :class:`ModelEventDestination`: Configuration model for destinations
    - :class:`ServiceContractValidationEventEmitter`: Event emitter service

.. versionadded:: 0.4.0
    Initial implementation as part of OMN-1151 event emitter service.
"""

from enum import Enum

__all__ = ["EnumEventSinkType"]


class EnumEventSinkType(str, Enum):
    """
    Event sink type enumeration.

    Defines the supported types of event destinations for contract
    validation events.

    Attributes:
        MEMORY: In-memory storage for testing and process-local collection.
            Events are stored in a list and can be retrieved programmatically.
        FILE: JSONL file output for persistent event logging.
            Events are written as newline-delimited JSON.
        KAFKA: Kafka/Redpanda topic for distributed event streaming.
            Reserved for future implementation.

    Example:
        >>> from omnibase_core.enums import EnumEventSinkType
        >>>
        >>> # Check sink type
        >>> sink_type = EnumEventSinkType.MEMORY
        >>> sink_type == "memory"
        True
        >>> sink_type.is_persistent
        False
        >>>
        >>> # File sink
        >>> file_sink = EnumEventSinkType.FILE
        >>> file_sink.is_persistent
        True

    .. versionadded:: 0.4.0
    """

    MEMORY = "memory"
    FILE = "file"
    KAFKA = "kafka"

    @property
    def is_persistent(self) -> bool:
        """
        Check if this sink type provides persistent storage.

        Returns:
            bool: True for FILE and KAFKA, False for MEMORY.

        Example:
            >>> EnumEventSinkType.MEMORY.is_persistent
            False
            >>> EnumEventSinkType.FILE.is_persistent
            True
        """
        return self in (EnumEventSinkType.FILE, EnumEventSinkType.KAFKA)

    @property
    def requires_path(self) -> bool:
        """
        Check if this sink type requires a file path.

        Returns:
            bool: True for FILE, False otherwise.
        """
        return self == EnumEventSinkType.FILE

    @property
    def requires_connection(self) -> bool:
        """
        Check if this sink type requires a network connection.

        Returns:
            bool: True for KAFKA, False otherwise.
        """
        return self == EnumEventSinkType.KAFKA
