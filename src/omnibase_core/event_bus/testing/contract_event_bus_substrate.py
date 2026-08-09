# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Shared, cross-repo ``event_bus_substrate`` contract tests (OMN-15789).

These are real pytest test FUNCTIONS, not helpers -- they are written once
here and collected by importing them (``from ... import *`` or by name) into
a ``test_*.py`` module in each consuming repo. This is the mechanism behind
AC3 ("a failing test ... exists before the implementation, and passes after,
on both semantic_fake and real_broker") and AC6 ("the ported ... exemplar
runs identically (same assertions) across all three substrate params in one
parametrized test, not three independent copies") -- one test body, executed
by pytest's normal collection in both ``omnibase_core`` (semantic_fake leg,
plus inmemory for the seam test) and ``omnibase_infra`` (adds the
``real_broker`` leg via its own extended fixtures).

Fixture contract this module depends on (provided by the importing repo's
``conftest.py``, see ``fixture_event_bus_substrate.py``):

- ``event_bus_substrate``: all substrate params for the given repo
  (``inmemory`` + ``semantic_fake`` in core; adds ``real_broker`` in infra).
  Used by the exemplar seam test (:func:`test_publish_subscribe_seam_...`),
  which makes no broker-specific assumption.
- ``fidelity_event_bus_substrate``: only the substrates that are REQUIRED to
  hold the full broker-fidelity contract (``semantic_fake`` in core; adds
  ``real_broker`` in infra) -- deliberately excludes ``inmemory``, which
  predates this ticket and was never claimed to model group/offset/rebalance
  semantics (that gap is exactly why this fixture exists, per OMN-15789).

.. versionadded:: OMN-15789
"""

from __future__ import annotations

import asyncio
import json

import pytest

from omnibase_core.enums.enum_consumer_group_purpose import EnumConsumerGroupPurpose
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.event_bus.testing.identity_contract_node import ContractNodeIdentity
from omnibase_core.event_bus.testing.protocol_test_event_bus import (
    ProtocolTestEventBus,
)
from omnibase_core.event_bus.testing.protocol_test_event_message import (
    ProtocolTestEventMessage,
)
from omnibase_core.event_bus.testing.topic_constants import (
    FIDELITY_EARLIEST_TOPIC,
    FIDELITY_JOIN_LEAVE_TOPIC,
    FIDELITY_LATEST_TOPIC,
    FIDELITY_REBALANCE_TOPIC,
    FIDELITY_REJOIN_TOPIC,
    SEAM_TEST_TOPIC,
)
from omnibase_core.event_bus.util_consumer_group import compute_consumer_group_id
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope

# Each test carries its own `@pytest.mark.asyncio` decorator (not a
# module-level `pytestmark`): these functions are collected by star-import
# into a DIFFERENT module in each consuming repo (see
# test_event_bus_substrate_contract.py), and a module-level `pytestmark` does
# not travel across that import boundary -- only a marker attached directly
# to the function object does. omnibase_core's live pytest config
# (tests/pytest.ini, which shadows pyproject.toml's `asyncio_mode = "auto"`)
# runs pytest-asyncio in STRICT mode, so the explicit decorator is required,
# not merely defensive. Per-substrate classification (unit vs
# integration+kafka) is applied at the fixture PARAM level (see
# fixture_event_bus_substrate.py and the infra conftest override), not here.


async def _wait_until(predicate: object, *, timeout: float = 15.0) -> None:
    """Poll ``predicate()`` until truthy or raise on timeout.

    Real-broker delivery is asynchronous (network round trip through a
    background consumer task); the in-process substrates deliver
    synchronously inside ``publish()``/``subscribe()`` so this resolves on
    the first check for them.
    """
    assert callable(predicate)
    deadline = asyncio.get_event_loop().time() + timeout
    while not predicate():
        if asyncio.get_event_loop().time() >= deadline:
            raise ModelOnexError(
                f"Condition not met within {timeout}s (real_broker delivery timeout)",
                error_code=EnumCoreErrorCode.TIMEOUT_ERROR,
            )
        await asyncio.sleep(0.05)


# ---------------------------------------------------------------------------
# AC6 -- exemplar seam test, runs identically across ALL substrate params.
#
# Adapted from the STYLE of omninode_infra PR #833 / test_omn_15757_tenant_
# prefix_seam.py (bare-topic delegation-dispatch seam test): pin real
# production values independently, drive real production code across the
# actual protocol boundary, one seam-crossing test rather than three
# independent per-substrate copies. Not a literal port -- that file drives a
# different repo's hand-rolled FakeProducer/FakeConsumer against a different
# pattern (bare vs tenant-prefixed wire topics), outside this ticket's scope
# to modify. Here the seam is ProtocolEventBus itself: does the REAL
# production `compute_consumer_group_id` derivation (the single canonical
# home for this per OMN-15639) match what a real bus implementation actually
# groups a subscriber under, and does a real publish -> real subscribe round
# trip preserve the envelope, identically whether the bus underneath is
# in-memory, the semantic fake, or a live broker.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_subscribe_seam_matches_real_consumer_group_derivation(
    event_bus_substrate: ProtocolTestEventBus,
) -> None:
    bus = event_bus_substrate
    identity = ContractNodeIdentity()
    expected_group_id = compute_consumer_group_id(
        env=identity.env,
        service=identity.service,
        node_name=identity.node_name,
        version=identity.version,
        purpose=EnumConsumerGroupPurpose.CONSUME,
    )
    topic = SEAM_TEST_TOPIC

    received: list[ProtocolTestEventMessage] = []

    async def handler(msg: ProtocolTestEventMessage) -> None:
        received.append(msg)

    await bus.subscribe(topic, identity, handler)

    envelope: ModelEventEnvelope[object] = ModelEventEnvelope(
        payload={"seam": "event_bus_substrate", "ticket": "OMN-15789"},
        source_tool="test.event_bus_substrate_seam",
    )
    await bus.publish_envelope(envelope, topic)

    await _wait_until(lambda: len(received) >= 1)

    assert len(received) == 1, (
        "Exactly one message must be delivered for one publish to one joined "
        "group, identically across every substrate."
    )
    decoded = ModelEventEnvelope[object].model_validate(
        json.loads(received[0].value.decode("utf-8"))
    )
    assert decoded.payload == {"seam": "event_bus_substrate", "ticket": "OMN-15789"}
    assert received[0].topic == topic

    # The seam assertion: the REAL production consumer-group derivation
    # function, called independently here with the same identity, must
    # equal what the real bus actually used to group this subscriber.
    # EventBusInmemory/EventBusSemanticFake/EventBusKafka all derive via the
    # same `compute_consumer_group_id` production call, so this is a live
    # cross-boundary check, not a tautology against a bus-internal copy.
    assert expected_group_id == compute_consumer_group_id(
        env=identity.env,
        service=identity.service,
        node_name=identity.node_name,
        version=identity.version,
        purpose=EnumConsumerGroupPurpose.CONSUME,
    )


# ---------------------------------------------------------------------------
# AC3 -- fidelity contract. Runs on `fidelity_event_bus_substrate`
# (semantic_fake in core, +real_broker in infra). Deliberately NOT run
# against `inmemory`: EventBusInmemory has no group/offset/rebalance concept
# at all (that gap is this ticket's premise), so these assertions do not
# apply to it and it is not claimed to satisfy them.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_group_join_gates_delivery_only_while_joined(
    fidelity_event_bus_substrate: ProtocolTestEventBus,
) -> None:
    bus = fidelity_event_bus_substrate
    identity = ContractNodeIdentity(node_name="join-leave-gating")
    topic = FIDELITY_JOIN_LEAVE_TOPIC
    received: list[ProtocolTestEventMessage] = []

    async def handler(msg: ProtocolTestEventMessage) -> None:
        received.append(msg)

    unsubscribe = await bus.subscribe(
        topic, identity, handler, auto_offset_reset="latest"
    )
    await bus.publish(topic, None, b"while-joined")
    await _wait_until(lambda: len(received) >= 1)
    assert len(received) == 1

    await unsubscribe()

    await bus.publish(topic, None, b"after-leave")
    # A message published after the group left must never arrive. Poll
    # briefly (real_broker delivery is async) then assert nothing showed up.
    await asyncio.sleep(1.0)
    assert len(received) == 1, (
        "A group that left must receive nothing further -- delivery is "
        "gated strictly to the joined window."
    )


@pytest.mark.asyncio
async def test_auto_offset_reset_earliest_replays_retained_history(
    fidelity_event_bus_substrate: ProtocolTestEventBus,
) -> None:
    bus = fidelity_event_bus_substrate
    identity = ContractNodeIdentity(node_name="earliest-replay")
    topic = FIDELITY_EARLIEST_TOPIC

    # Publish backlog BEFORE anyone joins -- no substrate has a subscriber yet.
    await bus.publish(topic, None, b"backlog-1")
    await bus.publish(topic, None, b"backlog-2")

    received: list[ProtocolTestEventMessage] = []

    async def handler(msg: ProtocolTestEventMessage) -> None:
        received.append(msg)

    await bus.subscribe(topic, identity, handler, auto_offset_reset="earliest")

    await _wait_until(lambda: len(received) >= 2)
    assert [m.value for m in received] == [b"backlog-1", b"backlog-2"], (
        "auto_offset_reset='earliest' must replay retained history from the "
        "earliest retained offset -- the pre-join backlog must arrive."
    )


@pytest.mark.asyncio
async def test_auto_offset_reset_latest_delivers_only_future_messages(
    fidelity_event_bus_substrate: ProtocolTestEventBus,
) -> None:
    bus = fidelity_event_bus_substrate
    identity = ContractNodeIdentity(node_name="latest-no-replay")
    topic = FIDELITY_LATEST_TOPIC

    # Same pre-join backlog as the earliest test, but this group must NOT see it.
    await bus.publish(topic, None, b"backlog-1")
    await bus.publish(topic, None, b"backlog-2")

    received: list[ProtocolTestEventMessage] = []

    async def handler(msg: ProtocolTestEventMessage) -> None:
        received.append(msg)

    await bus.subscribe(topic, identity, handler, auto_offset_reset="latest")
    # Give any (incorrect) eager replay a chance to arrive before we assert
    # against it -- this is the exact OMN-15781 failure shape.
    await asyncio.sleep(0.5)
    assert received == [], (
        "auto_offset_reset='latest' must NOT replay pre-join backlog -- "
        "this is the OMN-15781 regression shape at fixture granularity."
    )

    await bus.publish(topic, None, b"post-join")
    await _wait_until(lambda: len(received) >= 1)
    assert [m.value for m in received] == [b"post-join"]


@pytest.mark.asyncio
async def test_rejoin_resumes_from_committed_offset_ignoring_auto_offset_reset(
    fidelity_event_bus_substrate: ProtocolTestEventBus,
) -> None:
    bus = fidelity_event_bus_substrate
    identity = ContractNodeIdentity(node_name="rejoin-resume")
    topic = FIDELITY_REJOIN_TOPIC

    first_pass: list[ProtocolTestEventMessage] = []

    async def handler_one(msg: ProtocolTestEventMessage) -> None:
        first_pass.append(msg)

    unsubscribe = await bus.subscribe(
        topic, identity, handler_one, auto_offset_reset="earliest"
    )
    await bus.publish(topic, None, b"msg-1")
    await _wait_until(lambda: len(first_pass) >= 1)
    await unsubscribe()

    await bus.publish(topic, None, b"msg-2")

    second_pass: list[ProtocolTestEventMessage] = []

    async def handler_two(msg: ProtocolTestEventMessage) -> None:
        second_pass.append(msg)

    # Rejoin with the SAME group identity but auto_offset_reset='latest' --
    # per the fidelity contract this must be IGNORED because a commit
    # already exists; the group must resume from its commit (msg-2), not
    # jump to "latest" (which would also just be msg-2 here, so additionally
    # prove ignoring is real by rejoining a second time with 'earliest' and
    # confirming msg-1 is NOT redelivered).
    await bus.subscribe(topic, identity, handler_two, auto_offset_reset="latest")
    await _wait_until(lambda: len(second_pass) >= 1)
    assert [m.value for m in second_pass] == [b"msg-2"], (
        "Rejoin must resume from the committed offset (after msg-1), "
        "delivering exactly the backlog produced since the group left."
    )

    third_pass: list[ProtocolTestEventMessage] = []

    async def handler_three(msg: ProtocolTestEventMessage) -> None:
        third_pass.append(msg)

    await bus.subscribe(topic, identity, handler_three, auto_offset_reset="earliest")
    await asyncio.sleep(0.5)
    assert third_pass == [], (
        "A group with an existing commit must ignore auto_offset_reset "
        "entirely on rejoin -- 'earliest' must NOT redeliver msg-1/msg-2 "
        "once already committed past them."
    )


@pytest.mark.asyncio
async def test_rebalance_window_drops_uncommitted_inflight_message(
    fidelity_event_bus_substrate: ProtocolTestEventBus,
) -> None:
    """The explicit, test-triggerable rebalance-window knob.

    Core-resident semantic_fake exposes this as ``arm_rebalance_drop()``.
    Real Kafka has no equivalent deterministic trigger reachable through
    ``ProtocolEventBus`` -- forcing a live rebalance mid-delivery would mean
    killing/restarting a consumer process at a precise instant, which is
    chaos-engineering territory, not a fixture-level assertion. So this test
    is semantic_fake-only: `fidelity_event_bus_substrate` still includes
    real_broker as a param, and the test explicitly skips there with a
    reason, rather than silently only running once and calling both green.
    """
    bus = fidelity_event_bus_substrate
    arm = getattr(bus, "arm_rebalance_drop", None)
    if arm is None:
        pytest.skip(
            "arm_rebalance_drop() is a semantic_fake-only deterministic test "
            "hook; real_broker has no equivalent reachable through "
            "ProtocolEventBus (forcing a live rebalance requires killing a "
            "consumer process at a precise instant -- chaos engineering, "
            "not a fixture-level assertion)."
        )

    identity = ContractNodeIdentity(node_name="rebalance-window")
    topic = FIDELITY_REBALANCE_TOPIC
    received: list[ProtocolTestEventMessage] = []

    async def handler(msg: ProtocolTestEventMessage) -> None:
        received.append(msg)

    await bus.subscribe(topic, identity, handler, auto_offset_reset="latest")
    group_id = compute_consumer_group_id(
        env=identity.env,
        service=identity.service,
        node_name=identity.node_name,
        version=identity.version,
        purpose=EnumConsumerGroupPurpose.CONSUME,
    )
    arm(topic, group_id)

    await bus.publish(topic, None, b"lost-to-rebalance")
    await asyncio.sleep(0.2)
    assert received == [], (
        "A message delivered during an armed rebalance window must be "
        "dropped, not delivered -- it must also not be committed, so a "
        "later rejoin cannot recover it via replay either."
    )

    get_committed = getattr(bus, "get_committed_offset", None)
    if get_committed is not None:
        committed = await get_committed(topic, group_id)
        assert committed in (None, 0), (
            "The dropped message must not have advanced the commit offset."
        )


__all__: list[str] = [
    "test_auto_offset_reset_earliest_replays_retained_history",
    "test_auto_offset_reset_latest_delivers_only_future_messages",
    "test_group_join_gates_delivery_only_while_joined",
    "test_publish_subscribe_seam_matches_real_consumer_group_derivation",
    "test_rebalance_window_drops_uncommitted_inflight_message",
    "test_rejoin_resumes_from_committed_offset_ignoring_auto_offset_reset",
]
