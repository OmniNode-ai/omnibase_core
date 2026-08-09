# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Direct unit tests for EventBusSemanticFake (OMN-15789).

Covers:
- Basic lifecycle/protocol-surface parity with EventBusInmemory.
- AC4 (fake-raises half): each unsupported-list capability raises
  ModelOnexError(UNSUPPORTED_CAPABILITY_ERROR), never silently passes.
- AC5: the OMN-15781-class regression ("publish while consumer unjoined +
  auto_offset_reset=latest = message silently dropped") reproduced entirely
  in-process, independent of any live broker.

These are direct unit tests against EventBusSemanticFake (not routed
through the parametrized `event_bus_substrate`/`fidelity_event_bus_substrate`
fixtures) precisely because AC4 and AC5 are semantic_fake-specific claims,
not cross-substrate ones -- see
`omnibase_core.event_bus.testing.contract_event_bus_substrate` for the
tests that DO run across substrates.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.event_bus.event_bus_semantic_fake import EventBusSemanticFake
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
class TestEventBusSemanticFakeLifecycle:
    @pytest.mark.asyncio
    async def test_start_and_close(self) -> None:
        bus = EventBusSemanticFake(environment="test", group="unit")
        await bus.start()

        health: TypedDictEventBusHealth = await bus.health_check()
        assert health["healthy"] is True
        assert health["connected"] is True

        await bus.close()
        health = await bus.health_check()
        assert health["healthy"] is False

    @pytest.mark.asyncio
    async def test_properties(self) -> None:
        bus = EventBusSemanticFake(environment="dev", group="grp")
        assert bus.environment == "dev"
        assert bus.group == "grp"
        assert bus.adapter is bus

    def test_rejects_multi_partition_construction(self) -> None:
        with pytest.raises(ModelOnexError) as exc_info:
            EventBusSemanticFake(partition_count=2)
        assert (
            exc_info.value.error_code
            == EnumCoreErrorCode.UNSUPPORTED_CAPABILITY_ERROR.value
        )

    def test_rejects_non_positive_max_history(self) -> None:
        with pytest.raises(ModelOnexError) as exc_info:
            EventBusSemanticFake(max_history=0)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR.value


@pytest.mark.unit
class TestEventBusSemanticFakeBasicPubSub:
    @pytest.mark.asyncio
    async def test_basic_publish_subscribe(self) -> None:
        bus = EventBusSemanticFake(environment="test", group="unit")
        await bus.start()

        received: list[ModelEventMessage] = []

        async def handler(msg: ModelEventMessage) -> None:
            received.append(msg)

        identity = _FakeNodeIdentity()
        await bus.subscribe(
            "events.test", identity, handler, auto_offset_reset="latest"
        )
        await bus.publish("events.test", None, b"hello")

        assert len(received) == 1
        assert received[0].value == b"hello"

    @pytest.mark.asyncio
    async def test_publish_before_start_raises(self) -> None:
        bus = EventBusSemanticFake()
        with pytest.raises(ModelOnexError) as exc_info:
            await bus.publish("t", None, b"x")
        assert exc_info.value.error_code == EnumCoreErrorCode.SERVICE_UNAVAILABLE.value

    @pytest.mark.asyncio
    async def test_subscribe_requires_identity_or_group_id(self) -> None:
        bus = EventBusSemanticFake()
        await bus.start()

        async def handler(msg: ModelEventMessage) -> None:
            return

        with pytest.raises(ModelOnexError):
            await bus.subscribe("t", None, handler)

    @pytest.mark.asyncio
    async def test_subscribe_rejects_invalid_auto_offset_reset(self) -> None:
        bus = EventBusSemanticFake()
        await bus.start()

        async def handler(msg: ModelEventMessage) -> None:
            return

        with pytest.raises(ModelOnexError) as exc_info:
            await bus.subscribe(
                "t", _FakeNodeIdentity(), handler, auto_offset_reset="not-a-real-value"
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR.value


@pytest.mark.unit
class TestEventBusSemanticFakeOmn15781ClassRegression:
    """AC5: reproduce the OMN-15781 failure shape without any live broker."""

    @pytest.mark.asyncio
    async def test_publish_before_join_with_latest_silently_drops_message(self) -> None:
        """The exact live failure OMN-15781 needed a real broker to prove.

        beta-gateway-canary.yaml set auto_offset_reset="latest"; a consumer
        crash/restart window meant the group was unjoined when a message
        published, and that message was gone forever -- never redelivered,
        because "latest" never replays pre-join backlog. This test proves
        EventBusSemanticFake reproduces exactly that shape in-process.
        """
        bus = EventBusSemanticFake(environment="onex-dev", group="gateway-forwarder")
        await bus.start()

        topic = "onex.evt.omnibase-infra.delegation-completed.v1"
        identity = _FakeNodeIdentity(node_name="gateway-forwarder-outage-window")

        # Message published WHILE the consumer group is unjoined (simulating
        # the crash/restart outage window from OMN-15781).
        await bus.publish(topic, None, b"delegation-completed-during-outage")

        received: list[ModelEventMessage] = []

        async def handler(msg: ModelEventMessage) -> None:
            received.append(msg)

        # Consumer rejoins with auto_offset_reset="latest", matching the
        # defective beta-gateway-canary.yaml config OMN-15781 fixed.
        await bus.subscribe(topic, identity, handler, auto_offset_reset="latest")

        assert received == [], (
            "With auto_offset_reset='latest', the message published during "
            "the unjoined window is silently dropped -- reproducing the "
            "OMN-15781 backlog-loss shape entirely in-process."
        )

        # Prove the fix direction too: the SAME backlog, with
        # auto_offset_reset="earliest" (the OMN-15781 fix), is NOT dropped.
        bus2 = EventBusSemanticFake(environment="onex-dev", group="gateway-forwarder-2")
        await bus2.start()
        await bus2.publish(topic, None, b"delegation-completed-during-outage")

        received2: list[ModelEventMessage] = []

        async def handler2(msg: ModelEventMessage) -> None:
            received2.append(msg)

        await bus2.subscribe(
            topic,
            _FakeNodeIdentity(node_name="gateway-forwarder-fixed"),
            handler2,
            auto_offset_reset="earliest",
        )
        assert len(received2) == 1, (
            "auto_offset_reset='earliest' (the OMN-15781 fix) must replay "
            "the backlog produced during the unjoined window."
        )


@pytest.mark.unit
class TestEventBusSemanticFakeUnsupportedCapabilities:
    """AC4 (fake-raises half): every unsupported-list capability MUST raise.

    See `omnibase_infra`'s real_broker integration tests for the "identical
    test passes on real_broker" half where the underlying broker capability
    is actually reachable through EventBusKafka's surface.
    """

    @pytest.mark.asyncio
    async def test_begin_transaction_raises(self) -> None:
        bus = EventBusSemanticFake()
        await bus.start()
        with pytest.raises(ModelOnexError) as exc_info:
            await bus.begin_transaction()
        assert (
            exc_info.value.error_code
            == EnumCoreErrorCode.UNSUPPORTED_CAPABILITY_ERROR.value
        )

    @pytest.mark.asyncio
    async def test_publish_to_partition_raises(self) -> None:
        bus = EventBusSemanticFake()
        await bus.start()
        with pytest.raises(ModelOnexError) as exc_info:
            await bus.publish_to_partition("t", 1, None, b"x")
        assert (
            exc_info.value.error_code
            == EnumCoreErrorCode.UNSUPPORTED_CAPABILITY_ERROR.value
        )

    @pytest.mark.asyncio
    async def test_get_consumer_lag_raises(self) -> None:
        bus = EventBusSemanticFake()
        await bus.start()
        with pytest.raises(ModelOnexError) as exc_info:
            await bus.get_consumer_lag("t", "g")
        assert (
            exc_info.value.error_code
            == EnumCoreErrorCode.UNSUPPORTED_CAPABILITY_ERROR.value
        )

    @pytest.mark.asyncio
    async def test_simulate_broker_failover_raises(self) -> None:
        bus = EventBusSemanticFake()
        await bus.start()
        with pytest.raises(ModelOnexError) as exc_info:
            await bus.simulate_broker_failover()
        assert (
            exc_info.value.error_code
            == EnumCoreErrorCode.UNSUPPORTED_CAPABILITY_ERROR.value
        )

    @pytest.mark.asyncio
    async def test_publish_tombstone_raises(self) -> None:
        bus = EventBusSemanticFake()
        await bus.start()
        with pytest.raises(ModelOnexError) as exc_info:
            await bus.publish_tombstone("t", b"key")
        assert (
            exc_info.value.error_code
            == EnumCoreErrorCode.UNSUPPORTED_CAPABILITY_ERROR.value
        )

    @pytest.mark.asyncio
    async def test_configure_wire_codec_raises(self) -> None:
        bus = EventBusSemanticFake()
        await bus.start()
        with pytest.raises(ModelOnexError) as exc_info:
            await bus.configure_wire_codec(compression="gzip", batch_size=100)
        assert (
            exc_info.value.error_code
            == EnumCoreErrorCode.UNSUPPORTED_CAPABILITY_ERROR.value
        )


@pytest.mark.unit
class TestEventBusSemanticFakeRebalanceKnob:
    @pytest.mark.asyncio
    async def test_arm_rebalance_drop_removes_membership_on_next_delivery(self) -> None:
        bus = EventBusSemanticFake()
        await bus.start()
        topic = "t"
        identity = _FakeNodeIdentity(node_name="rebalance-unit")
        received: list[ModelEventMessage] = []

        async def handler(msg: ModelEventMessage) -> None:
            received.append(msg)

        await bus.subscribe(topic, identity, handler, auto_offset_reset="latest")
        group_id = "test.test-svc.rebalance-unit.consume.v1"
        # Sanity: this group_id must actually be the one subscribe() derived.
        committed_before = await bus.get_committed_offset(topic, group_id)
        assert committed_before == 0

        bus.arm_rebalance_drop(topic, group_id)
        await bus.publish(topic, None, b"dropped")

        assert received == []
        committed_after = await bus.get_committed_offset(topic, group_id)
        assert committed_after == 0, "A dropped message must not advance the commit."

        # Membership was removed by the rebalance -- a second publish must
        # also not be delivered (group is no longer joined at all).
        await bus.publish(topic, None, b"also-not-delivered")
        assert received == []
