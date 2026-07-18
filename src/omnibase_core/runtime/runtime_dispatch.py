# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""RuntimeDispatch — THE one runtime dispatch loop, over ``ProtocolTransport*`` (DI).

Net-new for the single-runtime / transport-via-DI unification (epic OMN-14717, ticket
OMN-14747; see
``docs/plans/2026-07-17-single-runtime-transport-di-unification-plan.md`` sections
(b)/(d)). This is S4: the single runtime, built in ``omnibase_core`` and depending ONLY
on the transport abstraction (``ProtocolTransportConsumer`` / ``ProtocolTransportProducer``,
S1). It is exercised end-to-end over the in-memory transport (S2) and is NOT yet wired
into ``service_kernel`` (that is S6). No production behavior changes.

What it owns (runtime = policy; transport = mechanism, plan I6):

1. A runtime-owned, pull-based poll loop over ``ProtocolTransportConsumer`` — the
   load-bearing inversion that lets the runtime own commit timing.
2. The inbound envelope boundary: wire bytes -> ``ModelEventEnvelope`` -> coerce
   ``envelope.payload`` (a dict) into the handler's declared def-B input model via the
   ONE coercion (``_invoke_handle_method``, ``runtime_local_adapter``; plan d.2 — no
   ``event_model``-conditional fork).
3. def-B invoke: ``handler.handle(request: ModelX) -> ModelY`` (or an ordered
   ``Sequence[ModelY]`` fan-out); the handler NEVER sees the envelope.
4. Fan-out routing through the shared ``runtime_fanout_resolver`` (fail-closed,
   injective-at-boot), then the OUTBOUND envelope boundary (``wrap_outbound_envelope``):
   each emitted payload leaves as a ``ModelEventEnvelope`` with a DERIVED + STAMPED
   ``event_type`` (the OMN-14743 durable fix — fail-closed on a null derivation),
   propagated ``correlation_id``, a causation tag
   (``metadata.tags['causation_id'] = inbound.envelope_id``), and a deterministic
   ``uuid5`` envelope id.
5. Error SURFACING (never swallow — replaces the infra swallow boundary): a handler /
   coercion / routing failure is redelivered (bounded retries) then dead-lettered.
6. Delivery POLICY (plan HOLE 1): per ``(topic, partition)`` in a poll batch, process
   strictly in offset order and commit only the contiguous successfully-terminalized
   prefix; the first ``REDELIVER`` stops that partition's prefix and nothing past it is
   committed this round. ONE commit per partition per poll (throughput), correctness by
   the same decision.
"""

from __future__ import annotations

import inspect
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, cast

from pydantic import BaseModel

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_delivery_disposition import EnumDeliveryDisposition
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.runtime.runtime_envelope_router import (
    decode_inbound_envelope,
    wrap_outbound_envelope,
)
from omnibase_core.runtime.runtime_fanout_resolver import (
    assert_published_events_injective,
    is_fanout_sequence,
    resolve_fanout_topics,
)
from omnibase_core.runtime.runtime_local_adapter import _invoke_handle_method

__all__ = ["DispatchRoute", "RuntimeDispatch"]

logger = logging.getLogger(__name__)

# Default poll batch size (max in-flight per poll — the backpressure bound, plan
# OPEN DECISION 1) and poll wait. Overridable per construction.
_DEFAULT_MAX_MESSAGES = 64
_DEFAULT_POLL_TIMEOUT_MS = 1000
# Number of redeliveries a message gets before it is dead-lettered.
_DEFAULT_MAX_RETRIES = 3


# --- structural transport surface (declared here on purpose) ----------------
# These are private STRUCTURAL MIRRORS of the canonical transport protocols in
# ``omnibase_core.protocols.runtime`` (``ProtocolTransportConsumer`` /
# ``ProtocolTransportProducer`` / ``ProtocolTransportMessage``, S1/#1463) and the
# handler-call target (``ProtocolLocalRuntimeCallableTarget``). They are declared
# locally rather than imported so this ``runtime`` src module adds NO new importer
# to the frozen ``protocols`` hub (the OMN-14340 growth ratchet HARD-FAILs a new
# ``* -> protocols`` edge; ``check_import_ratchet.py`` counts even ``TYPE_CHECKING``
# imports). The S2 ``InMemoryTransport`` avoids importing the same protocols for the
# same reason. The canonical protocols remain the single source of truth: each mirror
# is a SUBSET of the canonical surface (only what the runtime calls), so a concrete
# transport that satisfies the canonical protocol also satisfies the mirror — and
# ``tests/unit/runtime/test_runtime_dispatch.py`` binds RuntimeDispatch's injected
# transports to the CANONICAL protocol types, failing if the mirror ever drifts.


class _TransportMessageLike(Protocol):
    """Read-only shape the runtime needs from a polled message (mirror of
    ``ProtocolTransportMessage``)."""

    topic: str
    partition: int
    offset: int
    key: bytes | None
    value: bytes
    headers: Mapping[str, bytes]


class _TransportConsumerLike(Protocol):
    """Pull-based consumer surface (mirror of ``ProtocolTransportConsumer``)."""

    async def start(self) -> None: ...
    async def close(self) -> None: ...
    async def poll(
        self, *, max_messages: int, timeout_ms: int
    ) -> Sequence[_TransportMessageLike]: ...
    async def commit(self, message: _TransportMessageLike) -> None: ...
    async def nack(self, message: _TransportMessageLike) -> None: ...


class _TransportProducerLike(Protocol):
    """Producer surface (mirror of ``ProtocolTransportProducer``)."""

    async def send(
        self, topic: str, key: bytes | None, value: bytes, headers: Mapping[str, bytes]
    ) -> None: ...


class _HandlerLike(Protocol):
    """def-B handler target (mirror of ``ProtocolLocalRuntimeCallableTarget``)."""

    handle: Callable[..., object]


@dataclass(frozen=True)
class DispatchRoute:
    """One resolved subscribe-topic route: how to dispatch a message on a topic.

    Constructed at the composition root (S6) from the contract's ``handler_routing``.
    Holds the live handler plus the routing data the runtime needs; the runtime never
    touches Kafka — only this record and the transport protocols.
    """

    name: str
    """Handler / node name — the ``message_type`` for the fan-out resolver and logs."""

    handler: _HandlerLike
    """def-B handler exposing ``handle(request) -> response`` (sync or awaitable)."""

    published_events: Mapping[str, str]
    """Contract ``published_events`` class-name -> topic map for fan-out routing."""

    input_model_cls: type[BaseModel] | None = None
    """Declared def-B input model for a ``payload_type_match`` route.

    When set, the decoded payload dict is pre-validated into this model before invoke
    (mirrors the proven ``LocalRuntimeBusAdapter`` path). When ``None`` (an
    ``operation_match`` route), the raw dict is passed to the ONE coercion, which
    validates it against the handler's own parameter annotation (OMN-8724).
    """

    node_kind: EnumNodeKind | None = None
    """Node kind (informational in S4; drives projection->publish ordering from S8)."""


class RuntimeDispatch:
    """The single ONEX runtime dispatch loop over a DI-injected transport pair.

    Construction is dependency injection only: a consumer, a producer, and a
    topic -> :class:`DispatchRoute` map (built by the composition root). The runtime
    subscribes nothing itself — assigned topics + group are the consumer's
    construction-time config (plan section (c)). See the module docstring for the full
    policy set.
    """

    def __init__(
        self,
        *,
        consumer: _TransportConsumerLike,
        producer: _TransportProducerLike,
        routing_map: Mapping[str, DispatchRoute],
        default_route: DispatchRoute | None = None,
        max_messages: int = _DEFAULT_MAX_MESSAGES,
        poll_timeout_ms: int = _DEFAULT_POLL_TIMEOUT_MS,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        dlq_topic_resolver: Callable[[str], str] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._consumer = consumer
        self._producer = producer
        self._routing_map: dict[str, DispatchRoute] = dict(routing_map)
        # Extension point (plan section (g), S0 binding schemas): a fallback route so a
        # polled topic absent from ``routing_map`` is NOT silently dropped. The
        # omniclaude ``io_operations`` shell-binding + ``default_handler`` coverage
        # rides this seam; until it is fully wired, an unmapped topic with no
        # default_route fails CLOSED (surfaced + DLQ'd), never silently committed.
        # Full io_operations shell-binding + default_handler routing coverage is
        # tracked for OMN-14717 S8.
        self._default_route = default_route
        self._max_messages = max_messages
        self._poll_timeout_ms = poll_timeout_ms
        self._max_retries = max_retries
        self._dlq_topic_resolver = dlq_topic_resolver or _default_dlq_topic
        self._clock = clock
        self._stopping = False
        # (topic, partition, offset) -> consecutive failure count, for retry budgeting.
        self._attempts: dict[tuple[str, int, int], int] = {}

        # I4 boot check: every route's published_events must be an injective
        # class -> topic map, or wiring fails now (not at event k).
        for topic, route in self._routing_map.items():
            assert_published_events_injective(
                route.published_events, context=f"route[{topic}]::{route.name}"
            )
        if self._default_route is not None:
            assert_published_events_injective(
                self._default_route.published_events,
                context=f"default_route::{self._default_route.name}",
            )

    def stop(self) -> None:
        """Request the :meth:`run` loop to exit after the current poll cycle."""
        self._stopping = True

    async def run(self) -> None:
        """Production-shaped loop: poll -> dispatch -> commit until :meth:`stop`.

        Designed for a blocking transport whose ``poll`` waits up to
        ``poll_timeout_ms``. In-memory tests should use :meth:`drain` / :meth:`run_once`
        (the in-memory ``poll`` never blocks, so ``run`` would busy-loop).
        """
        await self._consumer.start()
        try:
            while not self._stopping:
                await self.run_once()
        finally:
            await self._consumer.close()

    async def drain(self, *, max_cycles: int = 1000) -> int:
        """Poll/dispatch cycles until a cycle processes nothing; return total processed.

        The local / test driver. Ensures the consumer is started, then loops until a
        poll yields an empty batch. A message that redelivers forever would loop
        forever, so this fails CLOSED at ``max_cycles`` (a stuck message is a bug, not a
        silent hang) — in practice a poison message is dead-lettered after
        ``max_retries`` and the loop makes progress.
        """
        await self._consumer.start()
        total = 0
        for _ in range(max_cycles):
            processed = await self.run_once()
            total += processed
            if processed == 0:
                return total
        raise ModelOnexError(
            message=(
                f"RuntimeDispatch.drain exceeded {max_cycles} cycles without draining — "
                "a message is stuck redelivering. Investigate (never silently hang)."
            ),
            error_code=EnumCoreErrorCode.INVALID_STATE,
        )

    async def run_once(self) -> int:
        """Run one poll cycle: group by ``(topic, partition)``, dispatch, prefix-commit.

        Returns the number of messages dispatched this cycle (0 when the poll batch is
        empty). Implements the plan HOLE 1 policy: within each ``(topic, partition)``,
        process strictly in offset order, commit the contiguous
        successfully-terminalized (or DLQ'd) prefix once, and stop the prefix at the
        first ``REDELIVER`` — nothing past it is committed this round.
        """
        batch = await self._consumer.poll(
            max_messages=self._max_messages, timeout_ms=self._poll_timeout_ms
        )
        if not batch:
            return 0

        groups: dict[tuple[str, int], list[_TransportMessageLike]] = defaultdict(list)
        for message in batch:
            groups[(message.topic, message.partition)].append(message)

        processed = 0
        for messages in groups.values():
            ordered = sorted(messages, key=lambda m: m.offset)
            last_committable: _TransportMessageLike | None = None
            redeliver_from: _TransportMessageLike | None = None
            for message in ordered:
                disposition = await self._dispatch_one(message)
                processed += 1
                if disposition is EnumDeliveryDisposition.COMMIT:
                    last_committable = message
                elif disposition is EnumDeliveryDisposition.DLQ:
                    await self._send_to_dlq(message)
                    last_committable = message
                else:  # REDELIVER — stop this partition's prefix HERE (HOLE 1)
                    redeliver_from = message
                    break
            if last_committable is not None:
                await self._consumer.commit(last_committable)
            if redeliver_from is not None:
                # Hold: make this message (and later same-partition offsets)
                # redeliverable. Kafka: seek; in-memory: reset the fetch position.
                await self._consumer.nack(redeliver_from)
        return processed

    async def _dispatch_one(
        self, message: _TransportMessageLike
    ) -> EnumDeliveryDisposition:
        """Dispatch one message end-to-end; NEVER raise — return a disposition.

        Decode -> coerce -> invoke -> resolve fan-out -> wrap outbound (fail-closed on a
        null ``event_type`` BEFORE any send, so the emit is all-or-nothing) -> send.
        Any failure is SURFACED (logged) and turned into a redeliver (within the retry
        budget) or a dead-letter (once exhausted) — the swallow boundary is gone.
        """
        key = (message.topic, message.partition, message.offset)
        try:
            route = self._route_for(message.topic)
            if route is None:
                raise ModelOnexError(
                    message=(
                        f"RuntimeDispatch: no route for topic {message.topic!r} and no "
                        "default_route configured — refusing to silently drop the "
                        "message. Add the topic to routing_map or configure a "
                        "default_route (io_operations shell-binding / default_handler "
                        "coverage: OMN-14717 S8)."
                    ),
                    error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
                )
            envelope = decode_inbound_envelope(message.value)
            request = self._coerce_request(envelope, route)
            result = await self._invoke(route, request)
            pairs = self._resolve_outbound(result, route)

            # Fail-closed BEFORE any producer.send: wrap every to-be-emitted payload
            # first. If ANY would carry a null event_type (or the inbound lacks a
            # correlation_id), this raises and NOTHING is emitted — the OMN-14743
            # guarantee is atomic per message, not per fan-out element.
            outbound: list[tuple[str, ModelEventEnvelope[BaseModel]]] = [
                (
                    topic,
                    wrap_outbound_envelope(
                        payload,
                        inbound_envelope=envelope,
                        idx=idx,
                        topic=topic,
                        clock=self._clock,
                    ),
                )
                for idx, (topic, payload) in enumerate(pairs)
            ]
            for topic, out_envelope in outbound:
                await self._producer.send(
                    topic,
                    key=message.key,
                    value=out_envelope.model_dump_json().encode("utf-8"),
                    headers={},
                )
            self._attempts.pop(key, None)
            return EnumDeliveryDisposition.COMMIT
        except Exception as exc:  # fallback-ok: the failure is SURFACED (logged) and converted to a delivery disposition (redeliver within budget, else DLQ) — the at-least-once contract, NOT a swallow; re-raising would abort the whole poll loop. CancelledError is BaseException and stays uncaught.
            attempts = self._attempts.get(key, 0) + 1
            self._attempts[key] = attempts
            logger.exception(
                "RuntimeDispatch: dispatch failed topic=%s partition=%d offset=%d "
                "attempt=%d (max_retries=%d): %s",
                message.topic,
                message.partition,
                message.offset,
                attempts,
                self._max_retries,
                exc,
            )
            if attempts > self._max_retries:
                return EnumDeliveryDisposition.DLQ
            return EnumDeliveryDisposition.REDELIVER

    def _route_for(self, topic: str) -> DispatchRoute | None:
        return self._routing_map.get(topic, self._default_route)

    def _coerce_request(
        self, envelope: ModelEventEnvelope[object], route: DispatchRoute
    ) -> object:
        """Extract ``envelope.payload`` and prepare it for the ONE coercion.

        ``payload_type_match`` (``input_model_cls`` set): pre-validate the payload dict
        into the declared model. ``operation_match`` (``input_model_cls`` None): pass
        the raw dict; ``_invoke_handle_method`` coerces it against the handler's own
        parameter annotation (the OMN-8724 core fix, the single coercion trigger).
        """
        payload = envelope.payload
        if route.input_model_cls is not None:
            payload_dict = payload if isinstance(payload, dict) else {}
            return route.input_model_cls(**payload_dict)
        return payload

    async def _invoke(self, route: DispatchRoute, request: object) -> object:
        """Invoke the def-B handler via the ONE coercion, awaiting async handlers."""
        maybe_result = _invoke_handle_method(route.handler.handle, request)
        if inspect.isawaitable(maybe_result):
            return await cast("Awaitable[object]", maybe_result)
        return maybe_result

    def _resolve_outbound(
        self, result: object, route: DispatchRoute
    ) -> list[tuple[str, BaseModel]]:
        """Normalize a def-B handler return into ordered ``(topic, payload)`` pairs.

        A ``None`` return emits nothing; a single ``BaseModel`` is a one-element
        fan-out; a ``Sequence[BaseModel]`` is a fan-out batch. Every element routes
        through the shared fail-closed ``runtime_fanout_resolver`` (an unmapped or
        carrier element raises).
        """
        if result is None:
            return []
        elements: list[object]
        if isinstance(result, BaseModel):
            elements = [result]
        elif is_fanout_sequence(result):
            elements = list(cast("Sequence[object]", result))
        else:
            raise ModelOnexError(
                message=(
                    f"RuntimeDispatch: handler {route.name!r} returned unsupported type "
                    f"{type(result).__name__!r}; a def-B handler returns a BaseModel "
                    "(single emit), an ordered Sequence[BaseModel] (fan-out), or None."
                ),
                error_code=EnumCoreErrorCode.HANDLER_EXECUTION_ERROR,
            )
        return resolve_fanout_topics(
            route.published_events, elements, message_type=route.name
        )

    async def _send_to_dlq(self, message: _TransportMessageLike) -> None:
        """Send the ORIGINAL message bytes to its dead-letter topic (durable evidence).

        The DLQ copy is the at-least-once-preserving durable record of a message that
        exhausted its retries; the caller then commits past it so the partition makes
        progress (the message is not silently lost — it is dead-lettered).
        """
        dlq_topic = self._dlq_topic_resolver(message.topic)
        await self._producer.send(
            dlq_topic,
            key=message.key,
            value=message.value,
            headers=dict(message.headers),
        )
        logger.warning(
            "RuntimeDispatch: dead-lettered message topic=%s partition=%d offset=%d -> %s",
            message.topic,
            message.partition,
            message.offset,
            dlq_topic,
        )


def _default_dlq_topic(topic: str) -> str:
    """Default DLQ topic resolver: ``<topic>.dlq``.

    DLQ-topic resolution is a contract concern (``event_bus.dlq_topics``); the
    composition root injects the real resolver. This default keeps the runtime usable
    (and DLQ non-silent) when none is supplied.
    """
    return f"{topic}.dlq"
