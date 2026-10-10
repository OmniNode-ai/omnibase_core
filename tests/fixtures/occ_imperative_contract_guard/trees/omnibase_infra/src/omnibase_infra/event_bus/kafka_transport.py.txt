# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Kafka face for the unified-runtime transport protocols (epic OMN-14717, S3).

Introduced for the unified-runtime transport seam (ticket OMN-14756; see
``docs/plans/2026-07-17-single-runtime-transport-di-unification-plan.md`` sections
(c)/(d), step S3) and used by the production hybrid gateway runtime for explicit
cross-broker acknowledgement. This is the concrete Kafka implementation of the two
core transport protocols

* ``omnibase_core.protocols.runtime.protocol_transport_consumer.ProtocolTransportConsumer``
* ``omnibase_core.protocols.runtime.protocol_transport_producer.ProtocolTransportProducer``

so the ONE runtime in core can run on the real broker via DI, with core never
importing Kafka (dependency inversion: this impl lives in infra and points inward).

Scope discipline (plan I6 — "runtime owns policy, transport owns mechanism")
---------------------------------------------------------------------------
This class is ONLY the raw Kafka client behind the protocol. It carries **zero**
dispatch / coercion / fan-out / DLQ / message-retry logic — ``RuntimeDispatch``
(core, S4) owns every one of those decisions and expresses them through the two
protocol primitives (``poll`` / ``commit`` / ``nack`` / ``send``). The mapping to
Kafka:

* ``poll``   -> ``AIOKafkaConsumer.getmany`` (per-partition, offset-ordered).
* ``commit`` -> ``AIOKafkaConsumer.commit({tp: offset+1})``. Kafka's committed
  offset is the *next* offset to fetch, so committing ``msg.offset + 1`` advances
  the partition high-water mark to ``msg.offset`` and thereby commits every offset
  ``<= msg.offset`` on that partition (plan HOLE 1 / conformance
  ``test_commit_at_k_commits_all_leq_k_on_partition``).
* ``nack``   -> ``AIOKafkaConsumer.seek(tp, msg.offset)``. Does NOT advance the
  committed offset; re-exposes ``msg`` and every later same-partition offset for
  redelivery (Kafka ``seek``; conformance
  ``test_nack_redelivers_from_offset_including_later``).
* ``send``   -> ``AIOKafkaProducer.send_and_wait`` (awaits the broker ack).
* ``send_with_coordinate`` -> the same call, returning the ``(topic,
  partition, offset)`` the broker assigned (OMN-17201).

The opt-in refused-topic retry is transport mechanism, not deployment policy: it
can peel broker-refused subscribe topics and retry them, but the composition root
owns whether to enable it and which retry interval to supply.

Two settings are FORCED for these NEW transport consumers and are deliberately not
read from the shared config (plan S3): ``enable_auto_commit=False`` (the runtime,
not the client, decides when an offset is durable) and ``auto_offset_reset`` defaults
to ``"earliest"`` (a pull-based at-least-once consumer must see the existing backlog
on first boot of a group). The legacy push-callback consumers in ``EventBusKafka``
keep their per-consumer ``self._config.enable_auto_commit`` setting untouched — this
face is a separate class and changes nothing about them.

Substitutability
----------------
``KafkaTransport`` is exercised by the SAME parametrized
``TransportConformanceSuite`` that certifies ``InMemoryTransport`` in core (S2). The
suite asserting identical observable Kafka semantics against both impls is what
licenses "in-memory golden chain => Kafka golden chain".
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import logging
import time
from collections.abc import Callable, Collection, Mapping, Sequence
from typing import cast

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import (
    KafkaError,
    TopicAuthorizationFailedError,
    UnknownTopicOrPartitionError,
)
from aiokafka.structs import TopicPartition

from omnibase_core.models.runtime.model_transport_message import ModelTransportMessage
from omnibase_infra.enums import EnumInfraTransportType
from omnibase_infra.errors import (
    ModelInfraErrorContext,
    ProtocolConfigurationError,
)
from omnibase_infra.event_bus.kafka_auth import build_aiokafka_auth_kwargs
from omnibase_infra.event_bus.models.config import ModelKafkaEventBusConfig
from omnibase_infra.topics.topic_namespace import (
    apply_topic_namespace,
    resolve_topic_namespace,
    strip_topic_namespace,
)

__all__ = ["KafkaTransport"]

logger = logging.getLogger(__name__)


class KafkaTransport:
    """Concrete Kafka transport: one instance is both consumer and producer.

    Consumer identity (``group`` + assigned ``topics``) is construction-time config
    supplied by the composition root — there is no runtime ``subscribe`` call,
    mirroring the pull-based protocol and the in-memory transport. A producer-only
    instance is constructed with no ``topics``; a consumer instance is constructed
    with the topics it is assigned. A "restart" is simply a new instance on the same
    ``group``: with ``enable_auto_commit=False`` it resumes from the committed
    offset, so every uncommitted offset is redelivered.
    """

    # Bounds for the post-position-change prefetch (see _prime). One batch only —
    # never the whole backlog — so priming is a latency optimization, not a load.
    _PRIME_POLL_MS = 500
    _PRIME_MAX_POLLS = 10
    _PRIME_MAX_RECORDS = 500

    def __init__(
        self,
        *,
        config: ModelKafkaEventBusConfig,
        group: str = "onex.transport.kafka",
        topics: Sequence[str] = (),
        auto_offset_reset: str = "earliest",
        refused_topic_retry_seconds: float | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if (
            refused_topic_retry_seconds is not None
            and not refused_topic_retry_seconds > 0
        ):
            context = ModelInfraErrorContext.with_correlation(
                transport_type=EnumInfraTransportType.KAFKA,
                operation="validate_config",
                target_name="kafka_transport",
            )
            raise ProtocolConfigurationError(
                "refused_topic_retry_seconds must be greater than zero",
                context=context,
                parameter="refused_topic_retry_seconds",
                value=refused_topic_retry_seconds,
            )
        self._config = config
        self._group = group
        # CANONICAL topics -- the runtime's view, and what every comparison,
        # log line and caught-up probe answer is expressed in.
        self._topics: tuple[str, ...] = tuple(topics)
        # PHYSICAL topics -- what this process actually subscribes to on the
        # broker. Identical to ``_topics`` unless a deployment namespace is
        # configured, and resolved once at construction rather than per call
        # so one process cannot straddle two namespaces mid-flight
        # (OMN-18891).
        self._topic_namespace: str = resolve_topic_namespace()
        self._physical_topics: tuple[str, ...] = tuple(
            apply_topic_namespace(t, namespace=self._topic_namespace)
            for t in self._topics
        )
        self._auto_offset_reset = auto_offset_reset
        self._refused_topic_retry_seconds = refused_topic_retry_seconds
        self._clock = clock
        self._refused_physical_topics: set[str] = set()
        self._next_refused_topic_retry_at: float | None = None
        self._producer: AIOKafkaProducer | None = None
        self._consumer: AIOKafkaConsumer | None = None
        self._started = False
        # Eagerly-prefetched, not-yet-returned messages (see _prime): serving these
        # first is what lets poll() return promptly right after a position change
        # (assign/seek), instead of racing the fetcher's refetch.
        self._buffer: list[ModelTransportMessage] = []

    @classmethod
    def from_bootstrap(
        cls,
        bootstrap: str,
        *,
        group: str = "onex.transport.kafka",
        topics: Sequence[str] = (),
        auto_offset_reset: str = "earliest",
    ) -> KafkaTransport:
        """Build a transport bound to an explicit bootstrap-servers override.

        Mirrors ``EventBusKafka.from_bootstrap``: the default config (with env
        overrides) is the base, then ``bootstrap_servers`` is set to the supplied
        value so the caller wins over ``KAFKA_BOOTSTRAP_SERVERS``.
        """
        config = ModelKafkaEventBusConfig.default().model_copy(
            update={"bootstrap_servers": bootstrap}
        )
        return cls(
            config=config,
            group=group,
            topics=topics,
            auto_offset_reset=auto_offset_reset,
        )

    # -- auth / client-version plumbing (reused from EventBusKafka's helpers) ----

    def _auth_kwargs(self) -> dict[str, object]:
        return build_aiokafka_auth_kwargs(self._config)

    def _client_version_kwargs(self, client_cls: type[object]) -> dict[str, object]:
        if self._config.api_version is None:
            return {}
        try:
            parameters = inspect.signature(client_cls.__init__).parameters
        except (TypeError, ValueError):
            return {}
        if "api_version" not in parameters:
            return {}
        return {"api_version": self._config.api_version}

    # -- lifecycle --------------------------------------------------------------

    async def start(self) -> None:
        """Start the producer and, if ``topics`` were assigned, the consumer."""
        if self._started:
            return

        try:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self._config.bootstrap_servers,
                acks=self._config.acks_aiokafka,
                enable_idempotence=self._config.enable_idempotence,
                max_request_size=self._config.max_request_size,
                retry_backoff_ms=self._config.reconnect_backoff_ms,
                **self._client_version_kwargs(AIOKafkaProducer),
                **self._auth_kwargs(),
            )
            await self._producer.start()

            if self._topics:
                await self._start_consumer()
        except BaseException:
            await self.close()
            raise

        self._started = True

    async def _start_consumer(self) -> None:
        """Construct, start, and prime a fresh consumer bound to ``self._topics``.

        Factored out of ``start()`` so ``restart_consumer`` can rejoin the group
        from zero (a brand-new client instance -- the only way to recover from a
        silent ``max_poll_interval_ms`` idle-eviction, see
        ``has_group_membership``) without touching ``self._producer``. A single
        ``KafkaTransport`` instance can back both one gateway direction's
        consumer AND the other direction's (plus status/heartbeat) producer, so
        a watchdog-triggered consumer recreate (``NodeGatewayDelivery``,
        OMN-15748/OMN-15690) must never go through ``close()`` + ``start()``,
        which stops both clients.
        """
        while True:
            active_topics = tuple(
                topic
                for topic in self._physical_topics
                if topic not in self._refused_physical_topics
            )
            if not active_topics:
                self._consumer = None
                self._schedule_refused_topic_retry()
                return

            # Group ``subscribe`` (topics passed positionally): the consumer joins
            # the group and, on join, NATIVELY resumes each partition from its
            # group-committed offset (a fresh group starts at ``auto_offset_reset``).
            # This is what makes "restart resumes from the committed offset" and
            # "uncommitted offsets redeliver on restart" hold, with no manual
            # ``seek`` dance. A single transport instance is the sole group member,
            # so it is assigned every partition of its topics — matching the unified
            # runtime's single-poll-loop-per-topic-set model (single-owner-per-topic
            # is the S6 boot invariant, R1). The one-time join latency is absorbed by
            # ``_prime`` below so the runtime's first ``poll`` still returns promptly.
            consumer = AIOKafkaConsumer(
                *active_topics,
                bootstrap_servers=self._config.bootstrap_servers,
                group_id=self._group,
                # FORCED for the new transport consumers (plan S3): the runtime, not
                # the client, decides when an offset is durable. Legacy push
                # consumers keep their per-consumer config setting untouched.
                enable_auto_commit=False,
                auto_offset_reset=self._auto_offset_reset,
                session_timeout_ms=self._config.session_timeout_ms,
                heartbeat_interval_ms=self._config.heartbeat_interval_ms,
                max_poll_interval_ms=self._config.max_poll_interval_ms,
                retry_backoff_ms=self._config.reconnect_backoff_ms,
                **self._client_version_kwargs(AIOKafkaConsumer),
                **self._auth_kwargs(),
            )
            self._consumer = consumer
            try:
                await consumer.start()
            except (TopicAuthorizationFailedError, UnknownTopicOrPartitionError) as exc:
                if self._refused_topic_retry_seconds is None:
                    raise
                with contextlib.suppress(Exception):
                    await consumer.stop()
                self._consumer = None
                refused = self._identify_refused_topics(consumer, active_topics, exc)
                if not refused:
                    raise
                for topic in active_topics:
                    if topic not in refused:
                        continue
                    self._refused_physical_topics.add(topic)
                    logger.warning(
                        "kafka_transport_topic_refused topic=%s group=%s error=%s "
                        "retry_in_seconds=%s",
                        strip_topic_namespace(topic, namespace=self._topic_namespace),
                        self._group,
                        type(exc).__name__,
                        self._refused_topic_retry_seconds,
                    )
                continue

            # Trigger the group join + first fetch now, buffering the first batch, so
            # the runtime's first poll() returns the available records instead of
            # racing the lazy rebalance.
            await self._prime(consumer)
            self._schedule_refused_topic_retry()
            return

    def _identify_refused_topics(
        self,
        consumer: AIOKafkaConsumer,
        active_topics: tuple[str, ...],
        exc: KafkaError,
    ) -> set[str]:
        """Identify refused physical topics from aiokafka's metadata snapshot.

        aiokafka registers every subscribed topic for metadata at consumer
        construction (``client.set_topics``) and bootstraps before
        ``_wait_topics``, so by the time either error is raised the snapshot
        covers the whole subscription. An authorization refusal is read only
        from the broker's explicit answer (``unauthorized_topics`` and the
        error's own topic argument); "no partitions" is consulted only for
        ``UnknownTopicOrPartitionError``, which aiokafka raises without naming
        the topic, so an admitted topic is never peeled on a guess.
        """
        refused: set[str] = set()
        cluster = getattr(getattr(consumer, "_client", None), "cluster", None)
        if cluster is not None:
            unauthorized = getattr(cluster, "unauthorized_topics", ())
            if isinstance(unauthorized, Collection):
                refused.update(
                    topic for topic in active_topics if topic in unauthorized
                )
            partitions_for_topic = getattr(cluster, "partitions_for_topic", None)
            if isinstance(exc, UnknownTopicOrPartitionError) and callable(
                partitions_for_topic
            ):
                lookup = cast("Callable[[str], object | None]", partitions_for_topic)
                for topic in active_topics:
                    with contextlib.suppress(Exception):
                        if lookup(topic) is None:
                            refused.add(topic)

        if not refused and exc.args:
            fallback = exc.args[0]
            if isinstance(fallback, str) and fallback in active_topics:
                refused.add(fallback)
        return refused

    def _schedule_refused_topic_retry(self) -> None:
        """Schedule the next opt-in retry when at least one topic is refused."""
        if (
            self._refused_physical_topics
            and self._refused_topic_retry_seconds is not None
        ):
            self._next_refused_topic_retry_at = (
                self._clock() + self._refused_topic_retry_seconds
            )
        else:
            self._next_refused_topic_retry_at = None

    async def _retry_refused_topics_if_due(self) -> None:
        """Rebuild the subscription when the refused-topic interval expires."""
        retry_at = self._next_refused_topic_retry_at
        if (
            self._refused_topic_retry_seconds is None
            or not self._refused_physical_topics
            or retry_at is None
            or self._clock() < retry_at
        ):
            return

        previous_refused = set(self._refused_physical_topics)
        canonical_topics = sorted(
            strip_topic_namespace(topic, namespace=self._topic_namespace)
            for topic in previous_refused
        )
        logger.info(
            "kafka_transport_topic_retry topics=%s group=%s",
            ",".join(canonical_topics),
            self._group,
        )
        self._refused_physical_topics.clear()
        self._next_refused_topic_retry_at = None
        if self._consumer is not None:
            try:
                await self._consumer.stop()
            finally:
                self._consumer = None
        await self._start_consumer()

        admitted = previous_refused - self._refused_physical_topics
        for topic in sorted(admitted):
            logger.info(
                "kafka_transport_topic_admitted topic=%s group=%s",
                strip_topic_namespace(topic, namespace=self._topic_namespace),
                self._group,
            )

    async def restart_consumer(self) -> None:
        """Recreate ONLY the consumer-side client; the shared producer stays up.

        A gateway direction's membership-loss watchdog recovery
        (``NodeGatewayDelivery._recover_stalled_direction``,
        OMN-15748/OMN-15690) must rejoin the group from a fresh client without
        killing the producer this same instance also serves for the OTHER
        direction's forward-publish and every status/heartbeat publish --
        ``close()`` + ``start()`` stops both clients and would silently break
        those for the duration of the recreate. Requires an assigned
        ``topics`` set (a producer-only transport has nothing to restart).
        """
        if not self._topics:
            context = ModelInfraErrorContext.with_correlation(
                transport_type=EnumInfraTransportType.KAFKA,
                operation="restart_consumer",
                target_name="kafka_transport",
            )
            raise ProtocolConfigurationError(
                "KafkaTransport.restart_consumer() requires topics=[...]; "
                "this instance is producer-only.",
                context=context,
                parameter="topics",
                value=list(self._topics),
            )
        self._buffer.clear()
        if self._consumer is not None:
            try:
                await self._consumer.stop()
            finally:
                self._consumer = None
        await self._start_consumer()

    async def _prime(self, consumer: AIOKafkaConsumer) -> None:
        """Eagerly fetch ONE batch into ``self._buffer`` after a position change.

        Kafka fetches lazily: the first ``getmany`` after a group join or a ``seek``
        can return empty while the join/refetch is still in flight. A pull runtime
        with a generous poll timeout would just retry, but a short-timeout caller
        (and the shared conformance suite's 50ms drain) would see a spurious empty
        batch. Priming one bounded batch here makes the next ``poll`` return the
        already-available records deterministically. It is a pure latency
        optimization — bounded by ``max_records`` (never the whole backlog) and
        touching neither offsets nor commits.

        The loop tolerates join latency (an early empty ``getmany`` while the
        rebalance completes) without hanging on a genuinely empty position: once the
        consumer has an assignment, two consecutive empty fetches mean "nothing
        available", so priming returns with an empty buffer.
        """
        empty_after_assignment = 0
        for _ in range(self._PRIME_MAX_POLLS):
            raw = await consumer.getmany(
                timeout_ms=self._PRIME_POLL_MS, max_records=self._PRIME_MAX_RECORDS
            )
            if raw:
                for topic_partition in sorted(
                    raw, key=lambda tp: (tp.topic, tp.partition)
                ):
                    for record in raw[topic_partition]:
                        self._buffer.append(self._to_model(topic_partition, record))
                return
            if consumer.assignment():
                empty_after_assignment += 1
                if empty_after_assignment >= 2:
                    return

    async def close(self) -> None:
        """Stop the consumer and producer; safe to call more than once."""
        self._buffer.clear()
        first_error: BaseException | None = None
        if self._consumer is not None:
            try:
                await self._consumer.stop()
            except BaseException as exc:  # noqa: BLE001 — cleanup must attempt both clients.
                first_error = exc
            finally:
                self._consumer = None
        if self._producer is not None:
            try:
                await self._producer.stop()
            except BaseException as exc:  # noqa: BLE001 — cleanup must attempt both clients.
                if first_error is None:
                    first_error = exc
            finally:
                self._producer = None
        self._started = False
        if first_error is not None:
            raise first_error

    def has_group_membership(self) -> bool:
        """Best-effort local check: does the consumer still hold a partition assignment?

        Not authoritative on its own -- ``assignment()`` reflects the client's
        last-known state and can be momentarily stale across a rebalance. Used
        as a corroborating signal for the delivery-loop staleness watchdog
        (``NodeGatewayDelivery``, OMN-15748/OMN-15690): a silent
        ``max_poll_interval_ms`` idle-eviction (aiokafka's client-side
        ``GroupCoordinator._heartbeat_routine``) drops group membership with
        zero exception raised to the caller, so the watchdog cannot rely on
        task failure alone to detect it.
        """
        if self._consumer is None:
            if (
                self._refused_topic_retry_seconds is not None
                and bool(self._physical_topics)
                and set(self._physical_topics) == self._refused_physical_topics
            ):
                return True
            return False
        try:
            return bool(self._consumer.assignment())
        except Exception:  # noqa: BLE001 — boundary: best-effort probe, never raises
            return False

    async def caught_up_topics(self, topics: frozenset[str]) -> frozenset[str]:
        """Return the subset of ``topics`` whose consumer has caught up (LAG=0).

        Used by the S6 phantom-subscription alarm (OMN-14758, §d): a topic is
        "caught up" when, for every ASSIGNED partition of that topic, the consumer's
        fetch position has reached the broker high-water mark. A topic with no assigned
        partition (or unknown high-water) is NOT reported caught-up. Best-effort and
        side-effect-free: a probe failure yields an empty set rather than raising.
        """
        consumer = self._consumer
        if consumer is None:
            return frozenset()
        partitions_by_topic: dict[str, list[TopicPartition]] = {}
        for tp in consumer.assignment():
            # The assignment carries PHYSICAL names and the caller asks in
            # CANONICAL ones, so map before comparing. Answering in canonical
            # names keeps this probe's contract unchanged (OMN-18891).
            canonical = strip_topic_namespace(tp.topic, namespace=self._topic_namespace)
            if canonical in topics:
                partitions_by_topic.setdefault(canonical, []).append(tp)
        caught_up: set[str] = set()
        for topic, partitions in partitions_by_topic.items():
            all_caught = True
            for tp in partitions:
                high_water = consumer.highwater(tp)
                position = await consumer.position(tp)
                if high_water is None or position < high_water:
                    all_caught = False
                    break
            if all_caught:
                caught_up.add(topic)
        return frozenset(caught_up)

    # -- consumer protocol ------------------------------------------------------

    @property
    def refused_topics(self) -> frozenset[str]:
        """Canonical topic names currently excluded after broker refusal."""
        return frozenset(
            strip_topic_namespace(topic, namespace=self._topic_namespace)
            for topic in self._refused_physical_topics
        )

    def _require_consumer(self) -> AIOKafkaConsumer:
        if self._consumer is None:
            context = ModelInfraErrorContext.with_correlation(
                transport_type=EnumInfraTransportType.KAFKA,
                operation="poll",
                target_name="kafka_transport",
            )
            raise ProtocolConfigurationError(
                "KafkaTransport consumer used before start() or without assigned "
                "topics; construct with topics=[...] and await start().",
                context=context,
                parameter="topics",
                value=list(self._topics),
            )
        return self._consumer

    async def poll(
        self, *, max_messages: int, timeout_ms: int
    ) -> Sequence[ModelTransportMessage]:
        """Pull up to ``max_messages`` records, in per-partition offset order.

        ``getmany`` returns ``{TopicPartition: [records...]}`` where each partition's
        records are already ascending by offset. Advancing the consumer's fetch
        position is what makes ``nack`` (a ``seek`` back) and restart-redelivery
        observable; the committed offset only moves on an explicit ``commit``.

        Any records eagerly prefetched by ``_prime`` after the last position change
        are served first (in per-partition offset order), so a poll immediately after
        ``start``/``nack`` returns the already-available records without racing the
        fetcher.
        """
        if max_messages < 1:
            context = ModelInfraErrorContext.with_correlation(
                transport_type=EnumInfraTransportType.KAFKA,
                operation="poll",
                target_name="kafka_transport",
            )
            raise ProtocolConfigurationError(
                f"max_messages must be a positive integer, got {max_messages}",
                context=context,
                parameter="max_messages",
                value=max_messages,
            )
        if self._buffer:
            batch = self._buffer[:max_messages]
            del self._buffer[:max_messages]
            return batch
        await self._retry_refused_topics_if_due()
        if (
            self._consumer is None
            and self._refused_topic_retry_seconds is not None
            and bool(self._physical_topics)
            and set(self._physical_topics) == self._refused_physical_topics
        ):
            await asyncio.sleep(timeout_ms / 1000)
            return []
        consumer = self._require_consumer()
        raw = await consumer.getmany(timeout_ms=timeout_ms, max_records=max_messages)
        polled: list[ModelTransportMessage] = []
        # Deterministic partition ordering; records within a partition stay
        # offset-ascending as getmany returns them.
        for topic_partition in sorted(raw, key=lambda tp: (tp.topic, tp.partition)):
            for record in raw[topic_partition]:
                polled.append(self._to_model(topic_partition, record))
        return polled

    @staticmethod
    def _to_model(
        topic_partition: TopicPartition, record: object
    ) -> ModelTransportMessage:
        """Map an aiokafka ``ConsumerRecord`` to the transport-agnostic model."""
        raw_headers = getattr(record, "headers", None) or ()
        headers: dict[str, bytes] = {}
        has_idempotency_key = False
        for key, value in raw_headers:
            if value is None:
                context = ModelInfraErrorContext.with_correlation(
                    transport_type=EnumInfraTransportType.KAFKA,
                    operation="poll",
                    target_name="kafka_transport",
                )
                raise ProtocolConfigurationError(
                    "KafkaTransport cannot map a nullable Kafka header into "
                    "ModelTransportMessage.headers, which requires bytes.",
                    context=context,
                    parameter=f"headers[{key!r}]",
                    value=None,
                )
            if key == "idempotency_key":
                if has_idempotency_key:
                    context = ModelInfraErrorContext.with_correlation(
                        transport_type=EnumInfraTransportType.KAFKA,
                        operation="poll",
                        target_name="kafka_transport",
                    )
                    raise ProtocolConfigurationError(
                        "KafkaTransport cannot map duplicate idempotency_key "
                        "headers into ModelTransportMessage.headers.",
                        context=context,
                        parameter="headers['idempotency_key']",
                        value="duplicate",
                    )
                has_idempotency_key = True
            headers[key] = value if isinstance(value, bytes) else bytes(value)
        offset = int(record.offset)  # type: ignore[attr-defined]
        return ModelTransportMessage(
            # CANONICAL: the runtime routes handlers by this name. ``commit``
            # and ``nack`` re-apply the namespace when they rebuild the
            # broker-facing TopicPartition (OMN-18891).
            topic=strip_topic_namespace(
                record.topic  # type: ignore[attr-defined]
            ),
            partition=int(record.partition),  # type: ignore[attr-defined]
            offset=offset,
            key=record.key,  # type: ignore[attr-defined]
            value=record.value,  # type: ignore[attr-defined]
            headers=headers,
            # Opaque cursor: TopicPartition + offset. The runtime never interprets
            # it; commit()/nack() reconstruct the same coordinate from the model.
            ack_token=(topic_partition, offset),
        )

    async def commit(self, message: object) -> None:
        """Advance the partition committed offset to ``message`` (commits all <= it).

        ``message`` is typed ``object`` (a supertype of the protocol's
        ``ProtocolTransportMessage``) so this impl stays contravariantly compatible
        with the protocol while narrowing to the concrete ``ModelTransportMessage``
        it yields from ``poll`` — the same convention as ``InMemoryTransport``.
        Committing ``offset + 1`` (the next offset to fetch) advances the high-water
        mark to ``msg.offset``, committing every earlier offset on the partition.
        """
        msg = cast("ModelTransportMessage", message)
        consumer = self._require_consumer()
        # ``msg.topic`` is CANONICAL; the broker coordinate is PHYSICAL.
        topic_partition = TopicPartition(
            apply_topic_namespace(msg.topic, namespace=self._topic_namespace),
            msg.partition,
        )
        await consumer.commit({topic_partition: msg.offset + 1})

    async def nack(self, message: object) -> None:
        """Re-expose ``message`` and later same-partition offsets (Kafka ``seek``).

        Does NOT advance the committed offset; seeks the live consumer's fetch
        position back to ``msg.offset`` so the next ``poll`` refetches it and every
        later offset on that partition.

        Sibling partitions are NOT touched (OMN-14757). ``_prime`` eagerly prefetches
        one bounded batch across EVERY assigned partition, advancing every partition's
        fetch position. A ``seek`` rewinds only the nacked partition, so its buffered
        records are stale and must be refetched — but the buffered records from OTHER
        partitions are the ONLY remaining copy at their (already-advanced) fetch
        position. Clearing the whole buffer here (the prior behaviour) dropped them:
        they became invisible until a consumer restart even though the runtime never
        touched them — an at-least-once liveness bug and a substitutability break vs
        the per-partition-lazy in-memory transport, whose ``nack`` touches only the
        nacked partition. So we discard ONLY the nacked partition's stale residue,
        RETAIN the sibling residue, and re-prime to refill the sought partition.
        """
        msg = cast("ModelTransportMessage", message)
        consumer = self._require_consumer()
        # ``msg.topic`` is CANONICAL; the broker coordinate is PHYSICAL.
        topic_partition = TopicPartition(
            apply_topic_namespace(msg.topic, namespace=self._topic_namespace),
            msg.partition,
        )
        consumer.seek(topic_partition, msg.offset)
        # Keep prefetched residue from OTHER (topic, partition)s — dropping it strands
        # those messages until restart. Only the nacked partition's buffered records
        # are stale post-seek; drop just those and re-prime to refill from the sought
        # position. Per-partition offset order is preserved: retained siblings stay
        # ascending, and the re-primed nacked-partition records append after them.
        self._buffer = [
            buffered
            for buffered in self._buffer
            if (buffered.topic, buffered.partition) != (msg.topic, msg.partition)
        ]
        await self._prime(consumer)

    # -- producer protocol ------------------------------------------------------

    async def send(
        self,
        topic: str,
        key: bytes | None,
        value: bytes,
        headers: Mapping[str, bytes],
    ) -> None:
        """Publish one event to ``topic`` and await the broker acknowledgement."""
        if self._producer is None:
            context = ModelInfraErrorContext.with_correlation(
                transport_type=EnumInfraTransportType.KAFKA,
                operation="send",
                target_name="kafka_transport",
            )
            raise ProtocolConfigurationError(
                "KafkaTransport producer used before start(); await start() first.",
                context=context,
                parameter="producer",
                value=None,
            )
        await self.send_with_coordinate(topic, key, value, headers)

    async def send_with_coordinate(
        self,
        topic: str,
        key: bytes | None,
        value: bytes,
        headers: Mapping[str, bytes],
    ) -> tuple[str, int, int]:
        """Publish one event and return the ``(topic, partition, offset)`` it took.

        OMN-17201. ``send`` satisfies ``ProtocolTransportProducer`` and returns
        nothing, which is the right shape for every caller that only needs "the
        broker took it". The gateway lane mirror needs strictly more: an
        acknowledgement proves A broker took the record, never that the
        INTENDED broker did, and the coordinate is the only thing on the
        acknowledgement that can be compared against what the mirror's own
        source consumer later reads. ``AIOKafkaProducer.send_and_wait`` has
        always returned this metadata; this method stops discarding it.
        """
        if self._producer is None:
            context = ModelInfraErrorContext.with_correlation(
                transport_type=EnumInfraTransportType.KAFKA,
                operation="send",
                target_name="kafka_transport",
            )
            raise ProtocolConfigurationError(
                "KafkaTransport producer used before start(); await start() first.",
                context=context,
                parameter="producer",
                value=None,
            )
        kafka_headers: list[tuple[str, bytes]] | None = [
            (key_, value_) for key_, value_ in headers.items()
        ] or None
        metadata = await self._producer.send_and_wait(
            apply_topic_namespace(topic, namespace=self._topic_namespace),
            value=value,
            key=key,
            headers=kafka_headers,
        )
        # The coordinate is returned in CANONICAL terms so a caller comparing
        # it against what it asked to publish, which is what the gateway lane
        # mirror does, still matches (OMN-18891).
        return (
            strip_topic_namespace(metadata.topic, namespace=self._topic_namespace),
            metadata.partition,
            metadata.offset,
        )
