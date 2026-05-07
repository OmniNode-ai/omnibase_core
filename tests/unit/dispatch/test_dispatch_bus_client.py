# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from omnibase_core.dispatch.dispatch_bus_client import (
    DispatchBusClient,
    load_dispatch_bus_route,
)
from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
from omnibase_core.models.dispatch import (
    ModelDispatchBusCommand,
    ModelDispatchBusTerminalResult,
)
from omnibase_core.models.event_bus.model_event_headers import ModelEventHeaders
from omnibase_core.models.event_bus.model_event_message import ModelEventMessage
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope


def _write_contract(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                'name: "pattern-b-broker"',
                "publish_topics:",
                "  - onex.cmd.pattern-b.dispatch.v1",
                "terminal_event: onex.evt.pattern-b.dispatch-completed.v1",
            ]
        ),
        encoding="utf-8",
    )


@pytest.mark.unit
def test_load_dispatch_bus_route_uses_contract_topics(tmp_path: Path) -> None:
    contract_path = tmp_path / "contract.yaml"
    _write_contract(contract_path)

    route = load_dispatch_bus_route(contract_path)

    assert route.command_topic == "onex.cmd.pattern-b.dispatch.v1"
    assert route.terminal_topic == "onex.evt.pattern-b.dispatch-completed.v1"
    assert route.contract_path == contract_path.resolve()


@pytest.mark.unit
def test_dispatch_bus_command_accepts_target_runtime_address() -> None:
    command = ModelDispatchBusCommand(
        command_name="session_bootstrap",
        requester="codex",
        payload={"dry_run": True},
        response_topic="onex.evt.omnimarket.pattern-b-dispatch-completed.v1",
        target_runtime_address="runtime://omninode-pc/main",
    )

    assert command.target_runtime_address == "runtime://omninode-pc/main"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dispatch_bus_client_request_round_trips_on_inmemory_bus(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "contract.yaml"
    _write_contract(contract_path)
    route = load_dispatch_bus_route(contract_path)

    bus = EventBusInmemory(environment="test", group="pattern-b")
    await bus.start()
    try:

        async def broker(message: ModelEventMessage) -> None:
            command_envelope = ModelEventEnvelope[
                ModelDispatchBusCommand
            ].model_validate_json(message.value)
            terminal_payload = ModelDispatchBusTerminalResult(
                correlation_id=command_envelope.payload.correlation_id,
                status="completed",
                payload={
                    "accepted": True,
                    "command_name": command_envelope.payload.command_name,
                },
            )
            terminal_envelope = ModelEventEnvelope[ModelDispatchBusTerminalResult](
                payload=terminal_payload,
                correlation_id=command_envelope.payload.correlation_id,
                event_type=route.terminal_topic,
                payload_type=ModelDispatchBusTerminalResult.__name__,
                source_tool="pattern-b-broker",
            )
            headers = ModelEventHeaders(
                source="pattern-b-broker",
                event_type=route.terminal_topic,
                timestamp=datetime.now(UTC),
                correlation_id=command_envelope.payload.correlation_id,
            )
            await bus.publish(
                route.terminal_topic,
                None,
                terminal_envelope.model_dump_json().encode("utf-8"),
                headers,
            )

        await bus.subscribe(
            route.command_topic, group_id="pattern-b-broker", on_message=broker
        )

        client = DispatchBusClient(bus, source="codex")
        result = await client.request(
            route,
            command_name="delegate-task",
            payload={"prompt": "test prompt"},
            timeout_seconds=1,
        )

        assert result.status == "completed"
        assert result.payload == {"accepted": True, "command_name": "delegate-task"}
    finally:
        await bus.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dispatch_bus_client_returns_timeout_result(tmp_path: Path) -> None:
    contract_path = tmp_path / "contract.yaml"
    _write_contract(contract_path)
    route = load_dispatch_bus_route(contract_path)

    bus = EventBusInmemory(environment="test", group="pattern-b")
    await bus.start()
    try:
        client = DispatchBusClient(bus, source="codex")
        result = await client.request(
            route,
            command_name="delegate-task",
            payload={"prompt": "test prompt"},
            timeout_seconds=1,
        )

        assert result.status == "timeout"
        assert result.error_message is not None
        assert "Timed out" in result.error_message
    finally:
        await bus.close()
