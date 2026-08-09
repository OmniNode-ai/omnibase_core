# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""In-process ``ProtocolEventBus`` fake that models real broker SEMANTICS.

``EventBusInmemory`` delivers synchronously to whoever is subscribed at
publish time and has no concept of consumer-group join semantics,
``auto_offset_reset``, commit offsets, or rebalance windows. A test that only
exercises it can pass while the identical code fails against real Kafka --
the named anti-pattern in ``feedback_real_dispatch_path_tests`` ("isolation
tests pass while live fails"). OMN-15781 (omnibase_infra) had to prove
"publish while consumer unjoined + auto_offset_reset=latest = message
silently dropped" against a REAL broker because no in-process substrate could
express it.

``EventBusSemanticFake`` sits between ``EventBusInmemory`` and a real broker.
It faithfully models:

- Consumer-group join/leave, with delivery gated to only-while-joined.
- ``auto_offset_reset`` "earliest" (replay retained history from offset 0, or
  from the group's last committed offset if one exists) vs "latest" (only
  messages published after join).
- Per-``(topic, group_id)`` commit-offset tracking, so a rejoining group
  resumes from its committed offset rather than re-applying
  ``auto_offset_reset``.
- An explicit, test-triggerable rebalance-window knob
  (:meth:`arm_rebalance_drop`) that drops an in-flight message on a
  group-membership change mid-delivery.

And it explicitly RAISES -- never silently passes -- for anything on its
unsupported list, forcing the caller to escalate to the ``real_broker`` leg
of the ``event_bus_substrate`` fixture (see
``omnibase_core.event_bus.testing.fixture_event_bus_substrate``):

- Exactly-once / transactional producer semantics (:meth:`begin_transaction`).
- Multi-partition ordering and key-based partition assignment
  (:meth:`publish_to_partition`, and constructing with ``partition_count`` != 1).
- Consumer lag / backpressure / broker-side quota throttling
  (:meth:`get_consumer_lag`).
- Broker failover / leader election / ISR shrink-expand
  (:meth:`simulate_broker_failover`).
- Compacted-topic tombstone semantics (:meth:`publish_tombstone`).
- Wire-protocol / codec-level behavior: batching, compression
  (:meth:`configure_wire_codec`).

Protocol Compatibility:
    ``ProtocolEventBus`` from ``omnibase_core`` using duck typing (no
    explicit inheritance required per ONEX patterns) -- same surface as
    ``EventBusInmemory``.

.. versionadded:: OMN-15789
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import NoReturn

from omnibase_core.enums.enum_consumer_group_purpose import EnumConsumerGroupPurpose
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.event_bus.model_event_bus_readiness import (
    ModelEventBusReadiness,
)
from omnibase_core.models.event_bus.model_event_headers import ModelEventHeaders
from omnibase_core.models.event_bus.model_event_message import ModelEventMessage
from omnibase_core.types.typed_dict.typed_dict_event_bus_health import (
    TypedDictEventBusHealth,
)

from .protocol_node_identity_like import ProtocolNodeIdentityLike
from .util_consumer_group import compute_consumer_group_id

logger = logging.getLogger(__name__)


# Valid values for the `auto_offset_reset` subscribe() kwarg. Mirrors the
# Kafka consumer config of the same name.
_VALID_AUTO_OFFSET_RESET: frozenset[str] = frozenset({"earliest", "latest"})

_UNSUPPORTED_ESCALATION_HINT = (
    "not modeled by EventBusSemanticFake -- escalate this test to the "
    "'real_broker' leg of the event_bus_substrate fixture "
    "(pytest.mark.integration + pytest.mark.kafka, gated on "
    "KAFKA_BOOTSTRAP_SERVERS + KAFKA_INTEGRATION_TESTS=1)."
)


def _raise_unsupported(capability: str) -> NoReturn:
    raise ModelOnexError(
        f"EventBusSemanticFake does not model {capability}: "
        f"{_UNSUPPORTED_ESCALATION_HINT}",
        error_code=EnumCoreErrorCode.UNSUPPORTED_CAPABILITY_ERROR,
        context={"capability": capability},
    )


class EventBusSemanticFake:
    """In-process ``ProtocolEventBus`` fake with broker-faithful group semantics.

    Unlike ``EventBusInmemory``, this fake tracks consumer-group membership,
    commit offsets, and ``auto_offset_reset`` per ``(topic, group_id)`` pair,
    and exposes an explicit rebalance-window knob. Anything it cannot
    faithfully model raises :class:`ModelOnexError` with
    ``EnumCoreErrorCode.UNSUPPORTED_CAPABILITY_ERROR`` rather than silently
    behaving as a no-op.
    """

    def __init__(
        self,
        environment: str = "local",
        group: str = "default",
        max_history: int = 1000,
        partition_count: int = 1,
    ) -> None:
        if max_history < 1:
            raise ModelOnexError(
                f"max_history must be a positive integer, got {max_history}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        if partition_count != 1:
            # Multi-partition ordering + key-based partition assignment is on
            # the explicit unsupported list -- fail at construction, not at
            # first publish, so a caller cannot silently proceed under a
            # false single-partition assumption.
            _raise_unsupported("multi-partition ordering and partition assignment")

        self._environment = environment
        self._group = group
        self._max_history = max_history

        # Retained per-topic history, oldest-first. Offset N is at index N
        # for as long as it fits in max_history (matches Kafka retention:
        # once the tail is evicted, "earliest" resolves to the oldest
        # retained offset, not offset 0).
        self._event_history: dict[str, deque[ModelEventMessage]] = defaultdict(
            lambda: deque(maxlen=max_history)
        )
        self._history_base_offset: dict[str, int] = defaultdict(int)
        self._topic_offsets: dict[str, int] = defaultdict(int)

        # (topic, group_id) -> single active member callback. A real Kafka
        # consumer group has exactly one member per partition; this fake has
        # exactly one partition, so exactly one active member per group.
        self._group_members: dict[
            tuple[str, str], Callable[[ModelEventMessage], Awaitable[None]]
        ] = {}
        # (topic, group_id) -> next offset to deliver (the "commit" offset).
        # Absence means the group has never joined this topic before.
        self._group_committed_offset: dict[tuple[str, str], int] = {}
        # (topic, group_id) pairs armed to drop the next in-flight delivery
        # via a simulated rebalance. See arm_rebalance_drop().
        self._pending_rebalance: set[tuple[str, str]] = set()

        self._lock = asyncio.Lock()
        self._started = False
        self._shutdown = False

    # ------------------------------------------------------------------
    # ProtocolEventBus surface
    # ------------------------------------------------------------------

    @property
    def adapter(self) -> EventBusSemanticFake:
        """No adapter for the fake bus -- returns self."""
        return self

    @property
    def environment(self) -> str:
        return self._environment

    @property
    def group(self) -> str:
        return self._group

    async def start(self) -> None:
        async with self._lock:
            self._started = True
            self._shutdown = False
        logger.info(
            "EventBusSemanticFake started",
            extra={"environment": self._environment, "group": self._group},
        )

    async def shutdown(self) -> None:
        await self.close()

    async def close(self) -> None:
        async with self._lock:
            self._group_members.clear()
            self._pending_rebalance.clear()
            self._started = False
            self._shutdown = True
        logger.info(
            "EventBusSemanticFake closed",
            extra={"environment": self._environment, "group": self._group},
        )

    async def publish(
        self,
        topic: str,
        key: bytes | None,
        value: bytes,
        headers: ModelEventHeaders | None = None,
    ) -> None:
        """Publish a message, delivering it only to currently-joined groups.

        Delivery to each joined ``(topic, group_id)`` is synchronous and, in
        the absence of an armed rebalance (:meth:`arm_rebalance_drop`),
        commits that group's offset immediately after the callback returns
        (auto-commit-on-delivery). A group armed for rebalance is dropped
        from membership and the message is neither delivered nor committed
        to it -- modeling a mid-delivery consumer-group rebalance losing an
        uncommitted in-flight message.
        """
        if not self._started:
            raise ModelOnexError(
                "Event bus not started. Call start() first.",
                error_code=EnumCoreErrorCode.SERVICE_UNAVAILABLE,
            )

        if headers is None:
            headers = ModelEventHeaders(
                source=f"{self._environment}.{self._group}",
                event_type=topic,
                timestamp=datetime.now(UTC),
            )

        async with self._lock:
            offset = self._topic_offsets[topic]
            self._topic_offsets[topic] = offset + 1
            message = ModelEventMessage(
                topic=topic,
                key=key,
                value=value,
                headers=headers,
                offset=str(offset),
                partition=0,
            )
            self._event_history[topic].append(message)
            self._history_base_offset[topic] = (
                offset + 1 - len(self._event_history[topic])
            )
            # Snapshot current membership for this topic. Iterating a
            # snapshot (not the live dict) means a callback that triggers a
            # rebalance drop for another group mid-loop cannot corrupt this
            # delivery pass.
            members = [
                (group_id, callback)
                for (msg_topic, group_id), callback in self._group_members.items()
                if msg_topic == topic
            ]

        for group_id, callback in members:
            key_pair = (topic, group_id)

            async with self._lock:
                rebalanced = key_pair in self._pending_rebalance
                if rebalanced:
                    self._pending_rebalance.discard(key_pair)
                    self._group_members.pop(key_pair, None)

            if rebalanced:
                logger.warning(
                    "Simulated rebalance dropped in-flight message",
                    extra={
                        "topic": topic,
                        "group_id": group_id,
                        "offset": message.offset,
                    },
                )
                continue

            await callback(message)

            async with self._lock:
                # Only commit if the group is still joined -- unsubscribe()
                # racing with delivery must not resurrect a stale commit.
                if key_pair in self._group_members:
                    self._group_committed_offset[key_pair] = offset + 1

    async def publish_envelope(
        self,
        envelope: object,
        topic: str,
        *,
        key: bytes | None = None,
    ) -> None:
        """Publish an event envelope to a topic (protocol compatibility)."""
        envelope_dict: object
        if hasattr(envelope, "model_dump"):
            envelope_dict = envelope.model_dump(mode="json")
        else:
            envelope_dict = envelope

        try:
            value = json.dumps(envelope_dict).encode("utf-8")
        except TypeError as e:
            raise ModelOnexError(
                f"Envelope is not JSON-serializable: {e}. "
                f"Got type: {type(envelope).__name__}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from e

        headers = ModelEventHeaders(
            source=f"{self._environment}.{self._group}",
            event_type=topic,
            content_type="application/json",
            timestamp=datetime.now(UTC),
        )
        await self.publish(topic, key, value, headers)

    async def subscribe(
        self,
        topic: str,
        node_identity: ProtocolNodeIdentityLike | None = None,
        on_message: Callable[[ModelEventMessage], Awaitable[None]] | None = None,
        *,
        group_id: str | None = None,
        purpose: EnumConsumerGroupPurpose = EnumConsumerGroupPurpose.CONSUME,
        required_for_readiness: bool = False,
        auto_offset_reset: str = "latest",
    ) -> Callable[[], Awaitable[None]]:
        """Join a consumer group on ``topic`` (a "group join").

        Args:
            auto_offset_reset: ``"earliest"`` or ``"latest"``. Only consulted
                the FIRST time this ``(topic, group_id)`` pair joins (no
                committed offset yet). A rejoin always resumes from the
                group's last committed offset, exactly like a real broker --
                the argument is ignored on rejoin, never re-applied.

        Returns:
            An unsubscribe ("leave group") coroutine. Leaving does not clear
            the committed offset: a subsequent rejoin resumes from it.
        """
        del required_for_readiness  # readiness gating is out of fidelity-contract scope
        if on_message is None:
            raise ModelOnexError(
                "on_message callback is required",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        if auto_offset_reset not in _VALID_AUTO_OFFSET_RESET:
            raise ModelOnexError(
                f"auto_offset_reset must be one of {sorted(_VALID_AUTO_OFFSET_RESET)}, "
                f"got {auto_offset_reset!r}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        if group_id is not None:
            effective_group_id = group_id
        elif node_identity is not None:
            effective_group_id = compute_consumer_group_id(
                env=node_identity.env,
                service=node_identity.service,
                node_name=node_identity.node_name,
                version=node_identity.version,
                purpose=purpose,
            )
        else:
            raise ModelOnexError(
                "subscribe() requires either node_identity or group_id",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        key_pair = (topic, effective_group_id)

        async with self._lock:
            already_committed = key_pair in self._group_committed_offset
            if already_committed:
                start_offset = self._group_committed_offset[key_pair]
            elif auto_offset_reset == "earliest":
                start_offset = self._history_base_offset.get(topic, 0)
            else:  # "latest"
                start_offset = self._topic_offsets.get(topic, 0)

            base_offset = self._history_base_offset.get(topic, 0)
            history = self._event_history.get(topic, ())
            replay_start_index = max(0, start_offset - base_offset)
            backlog = list(history)[replay_start_index:]

            self._group_members[key_pair] = on_message
            self._pending_rebalance.discard(key_pair)

        # Replay backlog (if any) synchronously and outside the lock, so a
        # slow/erroring handler cannot deadlock concurrent publish() calls.
        # Each replayed message advances the commit offset immediately,
        # matching the auto-commit-on-delivery model publish() uses.
        for msg in backlog:
            await on_message(msg)
            async with self._lock:
                if key_pair in self._group_members:
                    self._group_committed_offset[key_pair] = int(msg.offset or 0) + 1

        async with self._lock:
            if key_pair not in self._group_committed_offset:
                self._group_committed_offset[key_pair] = start_offset

        logger.debug(
            "Consumer group joined",
            extra={
                "topic": topic,
                "group_id": effective_group_id,
                "auto_offset_reset": auto_offset_reset,
                "replayed": len(backlog),
            },
        )

        async def unsubscribe() -> None:
            async with self._lock:
                if self._group_members.get(key_pair) is on_message:
                    self._group_members.pop(key_pair, None)

        return unsubscribe

    async def start_consuming(self) -> None:
        """Block until shutdown. Delivery here is push-based via publish()."""
        if not self._started:
            await self.start()
        while not self._shutdown:
            await asyncio.sleep(0.1)

    async def broadcast_to_environment(
        self,
        command: str,
        payload: dict[str, object],  # dict-str-any-ok: protocol compat
        target_environment: str | None = None,
    ) -> None:
        env = target_environment or self._environment
        topic = f"{env}.broadcast"
        value = json.dumps({"command": command, "payload": payload}).encode("utf-8")
        headers = ModelEventHeaders(
            source=f"{self._environment}.{self._group}",
            event_type="broadcast",
            content_type="application/json",
            timestamp=datetime.now(UTC),
        )
        await self.publish(topic, None, value, headers)

    async def send_to_group(
        self,
        command: str,
        payload: dict[str, object],  # dict-str-any-ok: protocol compat
        target_group: str,
    ) -> None:
        topic = f"{self._environment}.{target_group}"
        value = json.dumps({"command": command, "payload": payload}).encode("utf-8")
        headers = ModelEventHeaders(
            source=f"{self._environment}.{self._group}",
            event_type="group_command",
            content_type="application/json",
            timestamp=datetime.now(UTC),
        )
        await self.publish(topic, None, value, headers)

    async def health_check(self) -> TypedDictEventBusHealth:
        async with self._lock:
            member_count = len(self._group_members)
            topic_count = len({topic for topic, _ in self._group_members})
        return TypedDictEventBusHealth(
            healthy=self._started,
            connected=self._started,
            status=f"joined_groups={member_count} topics={topic_count}",
        )

    async def get_readiness_status(self) -> ModelEventBusReadiness:
        started = self._started
        return ModelEventBusReadiness(
            is_ready=started,
            consumers_started=started,
            required_topics=(),
            required_topics_ready=started,
        )

    # ------------------------------------------------------------------
    # Test-triggerable fidelity knobs
    # ------------------------------------------------------------------

    def arm_rebalance_drop(self, topic: str, group_id: str) -> None:
        """Arm a one-shot rebalance-window drop for ``(topic, group_id)``.

        The NEXT time ``publish()`` attempts to deliver to this group, the
        group is instead dropped from membership (simulating a
        mid-delivery ``LeaveGroup``/rebalance) and that message is neither
        delivered nor committed -- an uncommitted in-flight message lost to
        a rebalance window, the explicit knob required by the fidelity
        contract. Call :meth:`subscribe` again afterwards to rejoin (it will
        resume from the last committed offset, per the earliest/latest
        contract -- NOT re-deliver the dropped message, exactly like a real
        broker never redelivers a message a rebalanced-out consumer never
        acked).
        """
        self._pending_rebalance.add((topic, group_id))

    async def get_committed_offset(self, topic: str, group_id: str) -> int | None:
        """Return the current committed offset for ``(topic, group_id)``.

        Returns ``None`` if the group has never joined this topic.
        """
        async with self._lock:
            return self._group_committed_offset.get((topic, group_id))

    # ------------------------------------------------------------------
    # Explicit unsupported list -- MUST raise, never silently pass.
    # ------------------------------------------------------------------

    async def begin_transaction(self) -> None:
        """Exactly-once / transactional producer semantics are NOT modeled.

        Raises:
            ModelOnexError: Always. Escalate to ``real_broker``.
        """
        _raise_unsupported("exactly-once/transactional producer semantics")

    async def publish_to_partition(
        self,
        topic: str,
        partition: int,
        key: bytes | None,
        value: bytes,
    ) -> None:
        """Explicit partition assignment is NOT modeled (single partition only).

        Raises:
            ModelOnexError: Always. Escalate to ``real_broker``.
        """
        _raise_unsupported(
            "multi-partition ordering and key-based partition assignment"
        )

    async def get_consumer_lag(self, topic: str, group_id: str) -> int:
        """Consumer lag / backpressure / broker quota throttling are NOT modeled.

        Raises:
            ModelOnexError: Always. Escalate to ``real_broker``.
        """
        _raise_unsupported(
            "consumer lag, backpressure, and broker-side quota throttling"
        )

    async def simulate_broker_failover(self) -> None:
        """Broker failover / leader election / ISR shrink-expand are NOT modeled.

        Raises:
            ModelOnexError: Always. Escalate to ``real_broker``.
        """
        _raise_unsupported("broker failover, leader election, and ISR shrink-expand")

    async def publish_tombstone(self, topic: str, key: bytes) -> None:
        """Compacted-topic tombstone semantics are NOT modeled.

        Raises:
            ModelOnexError: Always. Escalate to ``real_broker``.
        """
        _raise_unsupported("compacted-topic tombstone semantics")

    async def configure_wire_codec(
        self, *, compression: str | None = None, batch_size: int | None = None
    ) -> None:
        """Wire-protocol/codec-level behavior (batching, compression) is NOT modeled.

        Raises:
            ModelOnexError: Always. Escalate to ``real_broker``.
        """
        _raise_unsupported("wire-protocol/codec-level behavior (batching, compression)")


__all__: list[str] = ["EventBusSemanticFake"]
