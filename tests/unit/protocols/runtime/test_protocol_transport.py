# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for the net-new transport protocols (OMN-14719, epic OMN-14717).

Currently unused foundation. These tests prove the protocols are importable, typed,
``@runtime_checkable``, and that the concrete ``ModelTransportMessage`` structurally
satisfies ``ProtocolTransportMessage`` (dependency inversion — the protocol layer
never imports the concrete model, keeping the OMN-14340 protocols->models ratchet
green).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pytest

from omnibase_core.models.runtime import ModelTransportMessage
from omnibase_core.protocols.runtime import (
    ProtocolTransportConsumer,
    ProtocolTransportMessage,
    ProtocolTransportProducer,
)


def _message(partition: int = 0, offset: int = 0) -> ModelTransportMessage:
    return ModelTransportMessage(
        topic="onex.cmd.example.v1",
        partition=partition,
        offset=offset,
        key=None,
        value=b"payload",
        headers={},
        ack_token=(partition, offset),
    )


class _FakeConsumer:
    """Minimal structural implementation used to prove the protocol is satisfiable."""

    def __init__(self) -> None:
        self.started = False
        self.closed = False
        self.committed: list[ProtocolTransportMessage] = []
        self.nacked: list[ProtocolTransportMessage] = []
        self._queue: list[ModelTransportMessage] = [
            _message(offset=0),
            _message(offset=1),
        ]

    async def start(self) -> None:
        self.started = True

    async def close(self) -> None:
        self.closed = True

    async def poll(
        self, *, max_messages: int, timeout_ms: int
    ) -> Sequence[ProtocolTransportMessage]:
        batch = self._queue[:max_messages]
        self._queue = self._queue[max_messages:]
        return batch

    async def commit(self, message: ProtocolTransportMessage) -> None:
        self.committed.append(message)

    async def nack(self, message: ProtocolTransportMessage) -> None:
        self.nacked.append(message)


class _FakeProducer:
    def __init__(self) -> None:
        self.sent: list[tuple[str, bytes | None, bytes, Mapping[str, bytes]]] = []

    async def send(
        self,
        topic: str,
        key: bytes | None,
        value: bytes,
        headers: Mapping[str, bytes],
    ) -> None:
        self.sent.append((topic, key, value, headers))


def _accepts_message(message: ProtocolTransportMessage) -> int:
    # Static: the runtime reads partition/offset/ack_token off the structural shape.
    return message.partition + message.offset


def _accepts_consumer(consumer: ProtocolTransportConsumer) -> ProtocolTransportConsumer:
    return consumer


def _accepts_producer(producer: ProtocolTransportProducer) -> ProtocolTransportProducer:
    return producer


def test_concrete_model_satisfies_message_protocol_statically() -> None:
    msg = _message(partition=2, offset=5)
    # Assigning the concrete model to the structural protocol type is the mypy check.
    as_protocol: ProtocolTransportMessage = msg
    assert _accepts_message(as_protocol) == 7


def test_concrete_model_is_runtime_checkable_message() -> None:
    assert isinstance(_message(), ProtocolTransportMessage)


def test_fake_consumer_satisfies_consumer_protocol() -> None:
    consumer = _FakeConsumer()
    assert isinstance(consumer, ProtocolTransportConsumer)
    assert _accepts_consumer(consumer) is consumer


def test_fake_producer_satisfies_producer_protocol() -> None:
    producer = _FakeProducer()
    assert isinstance(producer, ProtocolTransportProducer)
    assert _accepts_producer(producer) is producer


@pytest.mark.asyncio
async def test_fake_consumer_poll_commit_nack_flow() -> None:
    consumer: ProtocolTransportConsumer = _FakeConsumer()
    await consumer.start()
    batch = await consumer.poll(max_messages=1, timeout_ms=10)
    assert len(batch) == 1
    await consumer.commit(batch[0])
    remaining = await consumer.poll(max_messages=10, timeout_ms=10)
    assert len(remaining) == 1
    await consumer.nack(remaining[0])
    await consumer.close()


@pytest.mark.asyncio
async def test_fake_producer_send_awaits() -> None:
    producer: ProtocolTransportProducer = _FakeProducer()
    await producer.send("onex.dlq.example.v1", None, b"body", {"h": b"v"})
    assert isinstance(producer, _FakeProducer)
    assert producer.sent == [("onex.dlq.example.v1", None, b"body", {"h": b"v"})]
