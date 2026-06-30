# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""In-process dispatch harness for the core-resident local runtime (OMN-13420).

A minimal command -> terminal -> projection chain that runs entirely in-process:

* register a node's handlers (anything satisfying
  ``omnibase_core.protocols.runtime.protocol_message_handler.ProtocolMessageHandler``),
* publish a typed command envelope on the core
  ``omnibase_core.event_bus.event_bus_inmemory.EventBusInmemory``,
* pump every emitted event back through the registered handlers until a declared
  terminal topic is reached.

It uses ONLY the spi ``ProtocolMessageHandler.handle(envelope) -> ModelHandlerOutput``
contract, core envelope models, and the core in-memory bus. There is **no** infra
``MessageDispatchEngine``, DI container, topic provisioning, or consumer groups —
that machinery is exactly what forces an ``omnibase_infra`` install today, and it
is deliberately absent.

Scope (be honest): this proves HANDLER LOGIC and the in-process chain. It does NOT
exercise Kafka semantics (consumer groups, partitioning, DLQ, ordering,
idempotency-across-restart) or the image build. The infra-backed broker proof
remains the pre-merge gate; this is the inner loop only.
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from pydantic import BaseModel

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.runtime.harness.model_harness_result import ModelHarnessResult
from omnibase_core.protocols.runtime.protocol_message_handler import (
    ProtocolMessageHandler,
)


class InProcessHarness:
    """Register handlers, publish a command, pump events to the terminal event.

    Handlers are registered against the topic(s) they consume. When a handler emits
    events (via ``ModelHandlerOutput.events``), each emitted envelope is republished
    on the bus under its ``event_type`` topic and re-dispatched, until an event
    lands on one of the declared ``terminal_topics``.
    """

    def __init__(
        self,
        *,
        terminal_topics: frozenset[str],
        environment: str = "local",
        max_steps: int = 64,
    ) -> None:
        if not terminal_topics:
            raise ModelOnexError(
                message="terminal_topics must be non-empty",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        self._terminal_topics = terminal_topics
        self._max_steps = max_steps
        self._bus = EventBusInmemory(environment=environment, group="harness")
        self._handlers: dict[str, list[ProtocolMessageHandler]] = defaultdict(list)

    @property
    def bus(self) -> EventBusInmemory:
        """Return the in-memory bus (for inspection in tests/evidence)."""
        return self._bus

    @property
    def bus_impl(self) -> str:
        """Return the bus implementation name for evidence packets."""
        return type(self._bus).__name__

    def register(self, topic: str, handler: ProtocolMessageHandler) -> None:
        """Register ``handler`` to consume events published on ``topic``."""
        self._handlers[topic].append(handler)

    async def run(
        self,
        *,
        command_topic: str,
        command_envelope: ModelEventEnvelope[Any],
    ) -> ModelHarnessResult:
        """Publish the command envelope and pump events to a terminal event."""
        correlation_id = command_envelope.correlation_id
        if correlation_id is None:
            raise ModelOnexError(
                message="command_envelope.correlation_id is required",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        emitted_topics: list[str] = []
        terminal_topic: str | None = None
        terminal_payload: dict[str, object] | None = None

        await self._bus.start()

        # The work queue holds (topic, envelope) pairs to dispatch. We seed it with
        # the command and drain it breadth-first, re-enqueuing every emitted event.
        queue: list[tuple[str, ModelEventEnvelope[Any]]] = [
            (command_topic, command_envelope)
        ]
        steps = 0
        try:
            while queue:
                if steps >= self._max_steps:
                    raise ModelOnexError(
                        message=(
                            f"harness exceeded max_steps={self._max_steps} without "
                            "reaching a terminal event (possible handler cycle)"
                        ),
                        error_code=EnumCoreErrorCode.HANDLER_EXECUTION_ERROR,
                    )
                steps += 1
                topic, envelope = queue.pop(0)

                # Mirror the bus-transit contract: publish so the in-memory bus
                # history records every hop.
                await self._bus.publish_envelope(envelope, topic, key=None)
                emitted_topics.append(topic)

                is_terminal = topic in self._terminal_topics
                if is_terminal:
                    terminal_topic = topic
                    terminal_payload = self._decode_payload(envelope)

                # Dispatch all handlers registered on this topic. Terminal-topic
                # handlers (e.g. the projection REDUCER) still run so the projection
                # row is materialized; REDUCERs emit no events, so the queue stays
                # drained on the terminal hop.
                for handler in self._handlers.get(topic, []):
                    output = await handler.handle(envelope)
                    for emitted in output.events:
                        emitted_envelope = self._as_envelope(emitted)
                        next_topic = emitted_envelope.event_type
                        if not next_topic:
                            raise ModelOnexError(
                                message=(
                                    "emitted event envelope has no event_type; "
                                    "the harness routes by event_type"
                                ),
                                error_code=EnumCoreErrorCode.CONTRACT_VIOLATION,
                            )
                        queue.append((next_topic, emitted_envelope))

                if is_terminal:
                    break
        finally:
            await self._bus.close()

        if terminal_topic is None:
            return ModelHarnessResult(
                correlation_id=correlation_id,
                terminal_topic=None,
                terminal_payload=None,
                status="no_terminal",
                emitted_topics=tuple(emitted_topics),
                exit_code=2,
            )

        status = self._classify(terminal_topic, terminal_payload)
        return ModelHarnessResult(
            correlation_id=correlation_id,
            terminal_topic=terminal_topic,
            terminal_payload=terminal_payload,
            status=status,
            emitted_topics=tuple(emitted_topics),
            exit_code=0 if status == "success" else 3,
        )

    @staticmethod
    def _classify(terminal_topic: str, payload: dict[str, object] | None) -> str:
        """Classify the terminal as success/failure from payload or topic name."""
        if payload is not None:
            status = payload.get("status")
            if isinstance(status, str):
                return "success" if status == "success" else "failure"
        lowered = terminal_topic.lower()
        if "failed" in lowered or "failure" in lowered:
            return "failure"
        return "success"

    @staticmethod
    def _as_envelope(emitted: object) -> ModelEventEnvelope[Any]:
        """Narrow an emitted output element to a typed envelope."""
        if isinstance(emitted, ModelEventEnvelope):
            return emitted
        raise ModelOnexError(
            message=(
                "handler emitted a non-envelope output element; the harness "
                "requires ModelEventEnvelope instances in ModelHandlerOutput.events"
            ),
            error_code=EnumCoreErrorCode.CONTRACT_VIOLATION,
        )

    @staticmethod
    def _decode_payload(envelope: ModelEventEnvelope[Any]) -> dict[str, object]:
        """Decode an envelope payload to a JSON-safe dict for projection/evidence."""
        payload: object = envelope.payload
        if isinstance(payload, BaseModel):
            decoded: object = json.loads(payload.model_dump_json())
            return decoded if isinstance(decoded, dict) else {"value": decoded}
        if isinstance(payload, dict):
            return payload
        return {"value": payload}


__all__ = ["InProcessHarness"]
