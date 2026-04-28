# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed Pattern B broker client over ProtocolEventBus."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.core.model_generic_yaml import ModelGenericYaml
from omnibase_core.models.dispatch.model_dispatch_bus_command import (
    ModelDispatchBusCommand,
)
from omnibase_core.models.dispatch.model_dispatch_bus_route import ModelDispatchBusRoute
from omnibase_core.models.dispatch.model_dispatch_bus_terminal_result import (
    ModelDispatchBusTerminalResult,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.event_bus.model_event_message import ModelEventMessage
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.protocols.event_bus.protocol_dispatch_bus_client_transport import (
    ProtocolDispatchBusClientTransport,
)
from omnibase_core.protocols.event_bus.protocol_node_identity import (
    ProtocolNodeIdentity,
)
from omnibase_core.types.type_json import JsonType
from omnibase_core.utils.util_safe_yaml_loader import load_and_validate_yaml_model


def _as_mapping(raw: ModelGenericYaml) -> dict[str, object]:
    """Return a plain mapping from a validated generic YAML model."""
    data = raw.model_dump(mode="json", exclude_none=True)
    if not isinstance(data, dict):
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="Broker contract YAML must decode to a mapping.",
        )
    return data


def _resolve_command_topic(raw: dict[str, object]) -> str:
    publish_topics = raw.get("publish_topics")
    if isinstance(publish_topics, list) and publish_topics:
        first = publish_topics[0]
        if isinstance(first, str) and first:
            return first

    event_bus = raw.get("event_bus")
    if isinstance(event_bus, dict):
        nested_publish = event_bus.get("publish_topics")
        if isinstance(nested_publish, list) and nested_publish:
            first_nested = nested_publish[0]
            if isinstance(first_nested, str) and first_nested:
                return first_nested

    raise ModelOnexError(
        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        message="Broker contract must declare a publish topic for the command path.",
    )


def _resolve_terminal_topic(raw: dict[str, object]) -> str:
    terminal_event = raw.get("terminal_event")
    if isinstance(terminal_event, str) and terminal_event:
        return terminal_event
    if isinstance(terminal_event, dict):
        topic = terminal_event.get("topic")
        if isinstance(topic, str) and topic:
            return topic

    raise ModelOnexError(
        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        message="Broker contract must declare a terminal_event topic.",
    )


def load_dispatch_bus_route(contract_path: Path) -> ModelDispatchBusRoute:
    """Load broker command and terminal topics from a contract YAML file."""
    raw = load_and_validate_yaml_model(contract_path, ModelGenericYaml)
    data = _as_mapping(raw)
    return ModelDispatchBusRoute(
        contract_path=contract_path.resolve(),
        command_topic=_resolve_command_topic(data),
        terminal_topic=_resolve_terminal_topic(data),
    )


def command_uuid(raw: str) -> UUID:
    """Parse a correlation id string into the UUID type used by the models."""
    return UUID(raw)


class DispatchBusClient:
    """Thin typed client for the Pattern B broker request/result path."""

    def __init__(
        self, event_bus: ProtocolDispatchBusClientTransport, *, source: str
    ) -> None:
        self._event_bus = event_bus
        self._source = source

    async def publish_command(
        self,
        route: ModelDispatchBusRoute,
        command: ModelDispatchBusCommand,
    ) -> None:
        """Publish a broker command envelope to the route command topic."""
        envelope = ModelEventEnvelope[ModelDispatchBusCommand](
            payload=command,
            correlation_id=command.correlation_id,
            source_tool=self._source,
            target_tool="pattern-b-broker",
            event_type=route.command_topic,
            payload_type=ModelDispatchBusCommand.__name__,
            timeout_seconds=command.timeout_seconds,
        )
        await self._event_bus.publish(
            route.command_topic,
            None,
            envelope.model_dump_json().encode("utf-8"),
            None,
        )

    async def wait_for_result(
        self,
        route: ModelDispatchBusRoute,
        *,
        correlation_id: str,
    ) -> tuple[
        Callable[[], Awaitable[None]], asyncio.Queue[ModelDispatchBusTerminalResult]
    ]:
        """Subscribe to the terminal topic and return its queue plus unsubscribe."""
        result_queue: asyncio.Queue[ModelDispatchBusTerminalResult] = asyncio.Queue(
            maxsize=1
        )
        subscriber_identity = cast(
            ProtocolNodeIdentity,
            SimpleNamespace(
                env="local",
                service="pattern-b-client",
                node_name=f"terminal-wait-{correlation_id}",
                version="v1",
            ),
        )

        async def on_message(message: ModelEventMessage) -> None:
            envelope = ModelEventEnvelope[
                ModelDispatchBusTerminalResult
            ].model_validate_json(message.value)
            if str(envelope.payload.correlation_id) != correlation_id:
                return
            if result_queue.empty():
                await result_queue.put(envelope.payload)

        unsubscribe = await self._event_bus.subscribe(
            route.terminal_topic,
            subscriber_identity,
            on_message=on_message,
        )
        return unsubscribe, result_queue

    async def await_result(
        self,
        route: ModelDispatchBusRoute,
        *,
        correlation_id: str,
        timeout_seconds: int,
    ) -> ModelDispatchBusTerminalResult:
        """Wait for the correlated terminal result on the broker route."""
        parsed_correlation_id = command_uuid(correlation_id)
        unsubscribe, result_queue = await self.wait_for_result(
            route,
            correlation_id=correlation_id,
        )
        try:
            return await asyncio.wait_for(result_queue.get(), timeout=timeout_seconds)
        except TimeoutError:
            return ModelDispatchBusTerminalResult(
                correlation_id=parsed_correlation_id,
                status="timeout",
                error_message=(
                    "Timed out waiting for Pattern B broker terminal result."
                ),
            )
        finally:
            await unsubscribe()

    async def request(
        self,
        route: ModelDispatchBusRoute,
        *,
        command_name: str,
        payload: JsonType,
        timeout_seconds: int = 120,
    ) -> ModelDispatchBusTerminalResult:
        """Publish a broker command and wait for the correlated terminal result."""
        command = ModelDispatchBusCommand(
            command_name=command_name,
            requester=self._source,
            payload=payload,
            response_topic=route.terminal_topic,
            timeout_seconds=timeout_seconds,
        )
        unsubscribe, result_queue = await self.wait_for_result(
            route,
            correlation_id=str(command.correlation_id),
        )
        try:
            await self.publish_command(route, command)
            return await asyncio.wait_for(result_queue.get(), timeout=timeout_seconds)
        except TimeoutError:
            return ModelDispatchBusTerminalResult(
                correlation_id=command.correlation_id,
                status="timeout",
                error_message=(
                    "Timed out waiting for Pattern B broker terminal result."
                ),
            )
        finally:
            await unsubscribe()


__all__ = [
    "DispatchBusClient",
    "load_dispatch_bus_route",
]
