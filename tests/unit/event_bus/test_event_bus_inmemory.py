# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for the core EventBusInmemory implementation."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.event_bus.model_event_message import ModelEventMessage
from omnibase_core.types.typed_dict.typed_dict_event_bus_health import (
    TypedDictEventBusHealth,
)


@dataclass
class _FakeNodeIdentity:
    """Minimal ProtocolNodeIdentity-compatible identity for tests."""

    env: str = "test"
    service: str = "test-svc"
    node_name: str = "test-node"
    version: str = "v1"


@pytest.mark.unit
class TestEventBusInmemoryLifecycle:
    """Lifecycle (start/close) tests."""

    @pytest.mark.asyncio
    async def test_start_and_close(self) -> None:
        bus = EventBusInmemory(environment="test", group="unit")
        await bus.start()

        health: TypedDictEventBusHealth = await bus.health_check()
        assert health["healthy"] is True
        assert health["connected"] is True

        await bus.close()
        health = await bus.health_check()
        assert health["healthy"] is False

    @pytest.mark.asyncio
    async def test_shutdown_delegates_to_close(self) -> None:
        bus = EventBusInmemory()
        await bus.start()
        await bus.shutdown()

        health = await bus.health_check()
        assert health["healthy"] is False

    @pytest.mark.asyncio
    async def test_properties(self) -> None:
        bus = EventBusInmemory(environment="dev", group="grp")
        assert bus.environment == "dev"
        assert bus.group == "grp"
        assert bus.adapter is bus


@pytest.mark.unit
class TestEventBusInmemoryPubSub:
    """Publish/subscribe tests."""

    @pytest.mark.asyncio
    async def test_basic_publish_subscribe(self) -> None:
        bus = EventBusInmemory(environment="test", group="unit")
        await bus.start()

        received: list[ModelEventMessage] = []

        async def handler(msg: ModelEventMessage) -> None:
            received.append(msg)

        identity = _FakeNodeIdentity()
        unsub = await bus.subscribe("events.test", identity, handler)

        await bus.publish("events.test", b"key1", b"value1")
        assert len(received) == 1
        assert received[0].topic == "events.test"
        assert received[0].value == b"value1"
        assert received[0].key == b"key1"

        await unsub()
        await bus.publish("events.test", b"key2", b"value2")
        assert len(received) == 1  # no new messages after unsubscribe

        await bus.close()

    @pytest.mark.asyncio
    async def test_subscribe_with_explicit_group_id(self) -> None:
        bus = EventBusInmemory(environment="test", group="unit")
        await bus.start()

        received: list[ModelEventMessage] = []

        async def handler(msg: ModelEventMessage) -> None:
            received.append(msg)

        unsub = await bus.subscribe(
            "events.test", group_id="custom-group", on_message=handler
        )
        await bus.publish("events.test", None, b"payload")
        assert len(received) == 1

        await unsub()
        await bus.close()

    @pytest.mark.asyncio
    async def test_publish_before_start_raises(self) -> None:
        bus = EventBusInmemory()
        with pytest.raises(ModelOnexError):
            await bus.publish("t", None, b"v")

    @pytest.mark.asyncio
    async def test_subscribe_requires_identity_or_group(self) -> None:
        bus = EventBusInmemory()
        await bus.start()

        async def handler(msg: ModelEventMessage) -> None:
            pass

        with pytest.raises(ModelOnexError):
            await bus.subscribe("t", on_message=handler)

        await bus.close()

    @pytest.mark.asyncio
    async def test_subscribe_requires_callback(self) -> None:
        bus = EventBusInmemory()
        await bus.start()
        with pytest.raises(ModelOnexError):
            await bus.subscribe("t", _FakeNodeIdentity())
        await bus.close()

    @pytest.mark.asyncio
    async def test_publish_envelope(self) -> None:
        bus = EventBusInmemory(environment="test", group="unit")
        await bus.start()

        received: list[ModelEventMessage] = []

        async def handler(msg: ModelEventMessage) -> None:
            received.append(msg)

        await bus.subscribe("events.test", group_id="g", on_message=handler)
        await bus.publish_envelope({"key": "val"}, "events.test")

        assert len(received) == 1
        assert b'"key"' in received[0].value

        await bus.close()

    @pytest.mark.asyncio
    async def test_publish_envelope_non_serializable_raises(self) -> None:
        bus = EventBusInmemory()
        await bus.start()
        with pytest.raises(ModelOnexError):
            await bus.publish_envelope(object(), "t")
        await bus.close()


@pytest.mark.unit
class TestEventBusInmemoryHealth:
    """Health check and readiness tests."""

    @pytest.mark.asyncio
    async def test_health_check_returns_typed_dict(self) -> None:
        bus = EventBusInmemory()
        await bus.start()
        health = await bus.health_check()
        assert "healthy" in health
        assert "connected" in health
        await bus.close()

    @pytest.mark.asyncio
    async def test_readiness_status(self) -> None:
        bus = EventBusInmemory()
        readiness = await bus.get_readiness_status()
        assert readiness.is_ready is False

        await bus.start()
        readiness = await bus.get_readiness_status()
        assert readiness.is_ready is True
        assert readiness.consumers_started is True

        await bus.close()


@pytest.mark.unit
class TestEventBusInmemoryCircuitBreaker:
    """Circuit breaker tests."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_threshold(self) -> None:
        bus = EventBusInmemory(
            environment="test", group="unit", circuit_breaker_threshold=2
        )
        await bus.start()

        call_count = 0

        async def failing_handler(msg: ModelEventMessage) -> None:
            nonlocal call_count
            call_count += 1
            raise RuntimeError("boom")

        await bus.subscribe("t", group_id="g", on_message=failing_handler)

        # First two calls should invoke handler (and fail)
        await bus.publish("t", None, b"1")
        await bus.publish("t", None, b"2")
        assert call_count == 2

        # Third call: circuit is open, handler not invoked
        await bus.publish("t", None, b"3")
        assert call_count == 2

        await bus.close()

    @pytest.mark.asyncio
    async def test_circuit_breaker_reset(self) -> None:
        bus = EventBusInmemory(circuit_breaker_threshold=1)
        await bus.start()

        async def failing_handler(msg: ModelEventMessage) -> None:
            raise RuntimeError("boom")

        await bus.subscribe("t", group_id="g", on_message=failing_handler)
        await bus.publish("t", None, b"1")

        reset = await bus.reset_subscriber_circuit("t", "g")
        assert reset is True

        reset_noop = await bus.reset_subscriber_circuit("t", "nonexistent")
        assert reset_noop is False

        await bus.close()

    @pytest.mark.asyncio
    async def test_invalid_circuit_breaker_threshold(self) -> None:
        with pytest.raises(ModelOnexError):
            EventBusInmemory(circuit_breaker_threshold=0)


@pytest.mark.unit
class TestEventBusInmemoryDebugging:
    """Debugging and observability tests."""

    @pytest.mark.asyncio
    async def test_event_history(self) -> None:
        bus = EventBusInmemory(environment="test", group="unit", max_history=5)
        await bus.start()

        for i in range(7):
            await bus.publish("t", None, str(i).encode())

        history = await bus.get_event_history()
        assert len(history) == 5  # max_history=5

        history_topic = await bus.get_event_history(topic="nonexistent")
        assert len(history_topic) == 0

        await bus.clear_event_history()
        history = await bus.get_event_history()
        assert len(history) == 0

        await bus.close()

    @pytest.mark.asyncio
    async def test_subscriber_count_and_topics(self) -> None:
        bus = EventBusInmemory()
        await bus.start()

        async def handler(msg: ModelEventMessage) -> None:
            pass

        await bus.subscribe("t1", group_id="g1", on_message=handler)
        await bus.subscribe("t2", group_id="g2", on_message=handler)

        assert await bus.get_subscriber_count() == 2
        assert await bus.get_subscriber_count(topic="t1") == 1
        topics = await bus.get_topics()
        assert sorted(topics) == ["t1", "t2"]

        await bus.close()

    @pytest.mark.asyncio
    async def test_topic_offset(self) -> None:
        bus = EventBusInmemory()
        await bus.start()

        assert await bus.get_topic_offset("t") == 0
        await bus.publish("t", None, b"a")
        await bus.publish("t", None, b"b")
        assert await bus.get_topic_offset("t") == 2

        await bus.close()

    @pytest.mark.asyncio
    async def test_circuit_breaker_status(self) -> None:
        bus = EventBusInmemory(circuit_breaker_threshold=1)
        await bus.start()

        async def failing(msg: ModelEventMessage) -> None:
            raise RuntimeError("fail")

        await bus.subscribe("t", group_id="g", on_message=failing)
        await bus.publish("t", None, b"x")

        status = await bus.get_circuit_breaker_status()
        assert len(status["open_circuits"]) == 1  # type: ignore[arg-type]

        await bus.close()


@pytest.mark.unit
class TestEventBusInmemoryBroadcast:
    """Broadcast and group send tests."""

    @pytest.mark.asyncio
    async def test_broadcast_to_environment(self) -> None:
        bus = EventBusInmemory(environment="test", group="unit")
        await bus.start()

        received: list[ModelEventMessage] = []

        async def handler(msg: ModelEventMessage) -> None:
            received.append(msg)

        await bus.subscribe("test.broadcast", group_id="g", on_message=handler)
        await bus.broadcast_to_environment("reload", {"scope": "all"})

        assert len(received) == 1

        await bus.close()

    @pytest.mark.asyncio
    async def test_send_to_group(self) -> None:
        bus = EventBusInmemory(environment="test", group="unit")
        await bus.start()

        received: list[ModelEventMessage] = []

        async def handler(msg: ModelEventMessage) -> None:
            received.append(msg)

        await bus.subscribe("test.target-grp", group_id="g", on_message=handler)
        await bus.send_to_group("cmd", {"data": 1}, "target-grp")

        assert len(received) == 1

        await bus.close()


@pytest.mark.unit
class TestEventBusInmemoryInitialize:
    """Initialize method tests."""

    @pytest.mark.asyncio
    async def test_initialize_overrides_config(self) -> None:
        bus = EventBusInmemory()
        await bus.initialize(
            {"environment": "prod", "group": "svc", "max_history": "50"}
        )

        assert bus.environment == "prod"
        assert bus.group == "svc"

        health = await bus.health_check()
        assert health["healthy"] is True

        await bus.close()
