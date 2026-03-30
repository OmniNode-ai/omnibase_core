# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""In-Memory Event Bus implementation for local development and testing.

Implements ProtocolEventBus interface using deque-based event history with
direct subscriber callback invocation. This implementation is designed for
local development and testing scenarios where a full message broker (Kafka)
is not needed.

Extracted from omnibase_infra to omnibase_core as part of OMN-7062 so that
the zero-infrastructure local runtime can use an event bus without pulling
in the full infra package.

Protocol Compatibility:
    ProtocolEventBus from omnibase_core using duck typing
    (no explicit inheritance required per ONEX patterns).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from omnibase_core.enums.enum_consumer_group_purpose import EnumConsumerGroupPurpose
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.event_bus.model_event_bus_readiness import (
    ModelEventBusReadiness,
)
from omnibase_core.models.event_bus.model_event_headers import ModelEventHeaders
from omnibase_core.models.event_bus.model_event_message import ModelEventMessage
from omnibase_core.types.typed_dict.typed_dict_event_bus_health import (
    TypedDictEventBusHealth,
)

if TYPE_CHECKING:
    from omnibase_core.protocols.event_bus.protocol_node_identity import (
        ProtocolNodeIdentity,
    )

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Consumer group ID helpers (inlined from omnibase_infra to avoid dep)
# ---------------------------------------------------------------------------

_INVALID_CHAR_PATTERN = re.compile(r"[^a-z0-9._-]")
_CONSECUTIVE_SEPARATOR_PATTERN = re.compile(r"[._-]{2,}")
_EDGE_SEPARATOR_PATTERN = re.compile(r"^[._-]+|[._-]+$")
_KAFKA_CONSUMER_GROUP_MAX_LENGTH = 255


def _normalize_kafka_identifier(value: str) -> str:
    """Normalize a string for use as a consumer group ID component."""
    if not value:
        raise ValueError(  # error-ok: pure validation helper
            "Consumer group component cannot be empty"
        )
    result = value.lower()
    result = _INVALID_CHAR_PATTERN.sub("_", result)
    result = _CONSECUTIVE_SEPARATOR_PATTERN.sub(lambda m: m.group(0)[0], result)
    result = _EDGE_SEPARATOR_PATTERN.sub("", result)
    if not result:
        raise ValueError(  # error-ok: pure validation helper
            f"Input {value!r} results in empty string after normalization"
        )
    if len(result) > _KAFKA_CONSUMER_GROUP_MAX_LENGTH:
        hash_suffix = hashlib.sha256(value.encode()).hexdigest()[:8]
        max_prefix = _KAFKA_CONSUMER_GROUP_MAX_LENGTH - 9
        result = f"{result[:max_prefix]}_{hash_suffix}"
    return result


def _compute_consumer_group_id(
    identity: ProtocolNodeIdentity,
    purpose: EnumConsumerGroupPurpose = EnumConsumerGroupPurpose.CONSUME,
) -> str:
    """Compute canonical consumer group ID from node identity."""
    parts = [
        _normalize_kafka_identifier(identity.env),
        _normalize_kafka_identifier(identity.service),
        _normalize_kafka_identifier(identity.node_name),
        _normalize_kafka_identifier(purpose.value),
        _normalize_kafka_identifier(identity.version),
    ]
    group_id = ".".join(parts)
    if len(group_id) > _KAFKA_CONSUMER_GROUP_MAX_LENGTH:
        hash_input = (
            f"{identity.env}|{identity.service}|{identity.node_name}|"
            f"{purpose.value}|{identity.version}"
        )
        hash_suffix = hashlib.sha256(hash_input.encode()).hexdigest()[:8]
        max_prefix = _KAFKA_CONSUMER_GROUP_MAX_LENGTH - 9
        group_id = f"{group_id[:max_prefix]}_{hash_suffix}"
    return group_id


# ---------------------------------------------------------------------------
# EventBusInmemory
# ---------------------------------------------------------------------------


class EventBusInmemory:
    """In-memory event bus for local development and testing.

    Implements ProtocolEventBus interface using deque-based event history
    with direct subscriber callback invocation. Async-safe operations are
    ensured via asyncio.Lock.
    """

    def __init__(
        self,
        environment: str = "local",
        group: str = "default",
        max_history: int = 1000,
        circuit_breaker_threshold: int = 5,
    ) -> None:
        if circuit_breaker_threshold < 1:
            raise ModelOnexError(
                f"circuit_breaker_threshold must be a positive integer, "
                f"got {circuit_breaker_threshold}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        self._environment = environment
        self._group = group
        self._max_history = max_history

        self._subscribers: dict[
            str, list[tuple[str, Callable[[ModelEventMessage], Awaitable[None]]]]
        ] = defaultdict(list)

        self._event_history: deque[ModelEventMessage] = deque(maxlen=max_history)
        self._topic_offsets: dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()
        self._started = False
        self._shutdown = False

        self._subscriber_failures: dict[tuple[str, str], int] = {}
        self._max_consecutive_failures: int = circuit_breaker_threshold

    @property
    def adapter(self) -> EventBusInmemory:
        """No adapter for in-memory -- returns self."""
        return self

    @property
    def environment(self) -> str:
        """Get the environment identifier."""
        return self._environment

    @property
    def group(self) -> str:
        """Get the consumer group identifier."""
        return self._group

    async def start(self) -> None:
        """Start the event bus."""
        async with self._lock:
            self._started = True
            self._shutdown = False
        logger.info(
            "EventBusInmemory started",
            extra={"environment": self._environment, "group": self._group},
        )

    async def initialize(
        self, config: dict[str, object]
    ) -> None:  # dict-str-any-ok: protocol compat
        """Initialize with configuration and start."""
        async with self._lock:
            if "environment" in config:
                self._environment = str(config["environment"])
            if "group" in config:
                self._group = str(config["group"])
            if "max_history" in config:
                self._max_history = int(str(config["max_history"]))
                self._event_history = deque(
                    self._event_history, maxlen=self._max_history
                )
        await self.start()

    async def shutdown(self) -> None:
        """Gracefully shutdown the event bus."""
        await self.close()

    async def publish(
        self,
        topic: str,
        key: bytes | None,
        value: bytes,
        headers: ModelEventHeaders | None = None,
    ) -> None:
        """Publish message to topic."""
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
            self._event_history.append(message)
            subscribers = list(self._subscribers.get(topic, []))

        for group_id, callback in subscribers:
            failure_key = (topic, group_id)

            async with self._lock:
                failure_count = self._subscriber_failures.get(failure_key, 0)

            if failure_count >= self._max_consecutive_failures:
                logger.warning(
                    "Subscriber circuit breaker open - skipping callback",
                    extra={
                        "topic": topic,
                        "group_id": group_id,
                        "consecutive_failures": failure_count,
                        "correlation_id": str(headers.correlation_id),
                    },
                )
                continue

            try:
                await callback(message)
                async with self._lock:
                    if failure_key in self._subscriber_failures:
                        del self._subscriber_failures[failure_key]
            except Exception as e:
                async with self._lock:
                    self._subscriber_failures[failure_key] = (
                        self._subscriber_failures.get(failure_key, 0) + 1
                    )
                    current_failure_count = self._subscriber_failures[failure_key]
                logger.exception(
                    "Subscriber callback failed",
                    extra={
                        "topic": topic,
                        "group_id": group_id,
                        "error": str(e),
                        "consecutive_failures": current_failure_count,
                        "correlation_id": str(headers.correlation_id),
                    },
                )

    async def publish_envelope(
        self,
        envelope: object,
        topic: str,
        *,
        key: bytes | None = None,
    ) -> None:
        """Publish an event envelope to a topic."""
        envelope_dict: object
        if hasattr(envelope, "model_dump"):
            model_dump_method = envelope.model_dump
            envelope_dict = model_dump_method(mode="json")
        elif hasattr(envelope, "dict"):
            dict_method = envelope.dict
            envelope_dict = dict_method()
        elif isinstance(envelope, dict):
            envelope_dict = envelope
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
        node_identity: ProtocolNodeIdentity | None = None,
        on_message: Callable[[ModelEventMessage], Awaitable[None]] | None = None,
        *,
        group_id: str | None = None,
        purpose: EnumConsumerGroupPurpose = EnumConsumerGroupPurpose.CONSUME,
        required_for_readiness: bool = False,
    ) -> Callable[[], Awaitable[None]]:
        """Subscribe to topic with callback handler."""
        if on_message is None:
            raise ModelOnexError(
                "on_message callback is required",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        if group_id is not None:
            effective_group_id = group_id
        elif node_identity is not None:
            effective_group_id = _compute_consumer_group_id(node_identity, purpose)
        else:
            raise ModelOnexError(
                "subscribe() requires either node_identity or group_id",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        async with self._lock:
            self._subscribers[topic].append((effective_group_id, on_message))
            logger.debug(
                "Subscriber added",
                extra={"topic": topic, "group_id": effective_group_id},
            )

        async def unsubscribe() -> None:
            async with self._lock:
                try:
                    self._subscribers[topic].remove((effective_group_id, on_message))
                except ValueError:
                    pass

        return unsubscribe

    async def start_consuming(self) -> None:
        """Start the consumer loop (blocks until shutdown)."""
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
        """Broadcast command to environment."""
        env = target_environment or self._environment
        topic = f"{env}.broadcast"
        value_dict = {"command": command, "payload": payload}
        value = json.dumps(value_dict).encode("utf-8")

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
        """Send command to specific group."""
        topic = f"{self._environment}.{target_group}"
        value_dict = {"command": command, "payload": payload}
        value = json.dumps(value_dict).encode("utf-8")

        headers = ModelEventHeaders(
            source=f"{self._environment}.{self._group}",
            event_type="group_command",
            content_type="application/json",
            timestamp=datetime.now(UTC),
        )
        await self.publish(topic, None, value, headers)

    async def close(self) -> None:
        """Close the event bus and release resources."""
        async with self._lock:
            self._subscribers.clear()
            self._subscriber_failures.clear()
            self._started = False
            self._shutdown = True
        logger.info(
            "EventBusInmemory closed",
            extra={"environment": self._environment, "group": self._group},
        )

    async def health_check(self) -> TypedDictEventBusHealth:
        """Check event bus health."""
        async with self._lock:
            subscriber_count = sum(len(subs) for subs in self._subscribers.values())
            topic_count = len(self._subscribers)
            history_size = len(self._event_history)

        return TypedDictEventBusHealth(
            healthy=self._started,
            connected=self._started,
            status=f"subscribers={subscriber_count} topics={topic_count} history={history_size}",
        )

    async def get_readiness_status(self) -> ModelEventBusReadiness:
        """Check event bus readiness for serving traffic."""
        started = self._started
        return ModelEventBusReadiness(
            is_ready=started,
            consumers_started=started,
            required_topics=(),
            required_topics_ready=started,
        )

    # ----- Debugging/Observability -----

    async def get_event_history(
        self,
        limit: int = 100,
        topic: str | None = None,
    ) -> list[ModelEventMessage]:
        """Get recent events for debugging."""
        async with self._lock:
            history_list = list(self._event_history)
            if topic:
                history_list = [msg for msg in history_list if msg.topic == topic]
            history = (
                history_list[-limit:] if limit < len(history_list) else history_list
            )
            return list(history)

    async def clear_event_history(self) -> None:
        """Clear event history."""
        async with self._lock:
            self._event_history.clear()

    async def get_subscriber_count(self, topic: str | None = None) -> int:
        """Get subscriber count, optionally filtered by topic."""
        async with self._lock:
            if topic:
                return len(self._subscribers.get(topic, []))
            return sum(len(subs) for subs in self._subscribers.values())

    async def get_topics(self) -> list[str]:
        """Get list of topics with active subscribers."""
        async with self._lock:
            return [topic for topic, subs in self._subscribers.items() if subs]

    async def get_topic_offset(self, topic: str) -> int:
        """Get current offset for a topic."""
        async with self._lock:
            return self._topic_offsets.get(topic, 0)

    # ----- Circuit Breaker -----

    async def reset_subscriber_circuit(self, topic: str, group_id: str) -> bool:
        """Reset the circuit breaker for a specific subscriber."""
        failure_key = (topic, group_id)
        async with self._lock:
            if failure_key in self._subscriber_failures:
                del self._subscriber_failures[failure_key]
                return True
            return False

    async def get_circuit_breaker_status(
        self,
    ) -> dict[str, object]:  # dict-str-any-ok: diagnostic
        """Get circuit breaker status for all subscribers."""
        async with self._lock:
            open_circuits = [
                {"topic": topic, "group_id": group_id}
                for (topic, group_id), count in self._subscriber_failures.items()
                if count >= self._max_consecutive_failures
            ]
            return {
                "open_circuits": open_circuits,
                "failure_counts": {
                    f"{topic}:{group_id}": count
                    for (topic, group_id), count in self._subscriber_failures.items()
                },
            }


__all__: list[str] = ["EventBusInmemory"]
