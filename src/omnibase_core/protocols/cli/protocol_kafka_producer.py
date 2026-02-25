# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Kafka producer protocol for the registry-driven CLI dispatch system.

Defines the minimal interface required by ServiceCommandDispatcher to publish
events to the Kafka event bus.  Any object implementing this protocol
can be injected as the Kafka producer — no hard dependency on a specific
Kafka library (confluent_kafka, aiokafka, etc.) is required.

.. versionadded:: 0.19.0  (OMN-2553)
"""

from __future__ import annotations

__all__ = [
    "ProtocolKafkaProducer",
]

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolKafkaProducer(Protocol):
    """Minimal Kafka producer interface required by ServiceCommandDispatcher.

    Any object that implements ``produce(topic, key, value)`` and ``flush()``
    satisfies this protocol.  In production, a ``confluent_kafka.Producer``
    or similar is injected; in tests, a simple in-memory stub is sufficient.

    .. versionadded:: 0.19.0  (OMN-2553)
    """

    def produce(self, topic: str, key: str, value: bytes) -> None:
        """Publish a message to a Kafka topic.

        Args:
            topic: Target Kafka topic name.
            key: Message key (string).
            value: Message payload as raw bytes.
        """
        ...

    def flush(self, timeout: float = 5.0) -> None:
        """Flush pending messages.

        Args:
            timeout: Max seconds to wait for delivery.
        """
        ...
