# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for the core-resident infra-free local runtime harness (OMN-13420).

These tests exercise the full in-process command -> terminal -> projection chain
using ONLY core + spi-protocol surfaces. They must NOT import ``omnibase_infra``,
``aiokafka``, ``asyncpg`` or any LAN transport — the harness is infra-free by
contract, and ``test_harness_modules_carry_no_infra_or_transport_imports`` asserts
the modules carry no such imports.

Async chains are driven via ``asyncio.run`` in sync test bodies to match the
repo's existing ``tests/unit/runtime/test_runtime_local.py`` convention.
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest

from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.runtime.harness.model_harness_command import (
    ModelHarnessCommand,
)
from omnibase_core.models.runtime.harness.model_inference_request import (
    ModelInferenceRequest,
)
from omnibase_core.protocols.runtime.protocol_harness_inference_adapter import (
    ProtocolHarnessInferenceAdapter,
)
from omnibase_core.protocols.runtime.protocol_harness_projection_store import (
    ProtocolHarnessProjectionStore,
)
from omnibase_core.protocols.runtime.protocol_message_handler import (
    ProtocolMessageHandler,
)
from omnibase_core.runtime.harness import (
    CurlSubprocessInferenceAdapter,
    HarnessEffectHandler,
    HarnessOrchestratorHandler,
    HarnessProjectionReducer,
    InProcessHarness,
    RecordedFixtureInferenceAdapter,
    SqliteProjectionStore,
    build_workflow,
)
from omnibase_core.runtime.harness.harness_cli import (
    build_evidence_packet,
    run_workflow,
)


@pytest.mark.unit
@pytest.mark.parametrize("workflow", ["delegation", "sea"])
def test_workflow_reaches_terminal_and_projection(workflow: str) -> None:
    """Each workflow runs command -> terminal -> SQLite projection, exit 0."""
    correlation_id = uuid4()
    adapter = RecordedFixtureInferenceAdapter(completion="DONE")
    store = SqliteProjectionStore(path=":memory:")
    result, projection = asyncio.run(
        run_workflow(
            workflow=workflow,
            prompt="prove the inner loop",
            correlation_id=correlation_id,
            task_type="harness",
            max_tokens=256,
            adapter=adapter,
            store=store,
        )
    )

    assert result.reached_terminal
    assert result.status == "success"
    assert result.exit_code == 0
    assert result.terminal_topic is not None
    assert result.terminal_payload is not None
    assert result.terminal_payload["completion"] == "DONE"

    assert projection is not None
    assert projection.correlation_id == correlation_id
    assert projection.workflow == workflow
    assert projection.status == "success"
    assert projection.payload["completion"] == "DONE"
    assert store.row_count() == 1
    store.close()


@pytest.mark.unit
def test_emitted_topics_follow_command_infer_completed_order() -> None:
    """The bus records every hop: command -> infer -> completed."""
    store = SqliteProjectionStore()
    result, _ = asyncio.run(
        run_workflow(
            workflow="delegation",
            prompt="hi",
            correlation_id=uuid4(),
            task_type="harness",
            max_tokens=16,
            adapter=RecordedFixtureInferenceAdapter(),
            store=store,
        )
    )
    assert result.emitted_topics[0].startswith("onex.cmd.")
    assert "infer" in result.emitted_topics[1]
    assert result.emitted_topics[-1].endswith("completed.v1")
    store.close()


@pytest.mark.unit
def test_projection_readback_matches_written_row() -> None:
    """SQLite store round-trips the projection row; unknown IDs read None."""
    correlation_id = uuid4()
    store = SqliteProjectionStore()
    asyncio.run(
        run_workflow(
            workflow="sea",
            prompt="x",
            correlation_id=correlation_id,
            task_type="harness",
            max_tokens=8,
            adapter=RecordedFixtureInferenceAdapter(completion="ROW"),
            store=store,
        )
    )
    row = store.read(correlation_id)
    assert row is not None
    assert row.payload["completion"] == "ROW"
    assert store.read(uuid4()) is None
    store.close()


@pytest.mark.unit
def test_handlers_satisfy_protocol_message_handler() -> None:
    """All three harness handlers structurally satisfy ProtocolMessageHandler."""
    adapter = RecordedFixtureInferenceAdapter()
    store = SqliteProjectionStore()
    handlers = (
        HarnessOrchestratorHandler("delegation"),
        HarnessEffectHandler("delegation", adapter),
        HarnessProjectionReducer("delegation", store),
    )
    for handler in handlers:
        assert isinstance(handler, ProtocolMessageHandler)
    store.close()


@pytest.mark.unit
def test_adapters_satisfy_protocols() -> None:
    """Inference + projection adapters satisfy their structural protocols."""
    assert isinstance(
        RecordedFixtureInferenceAdapter(), ProtocolHarnessInferenceAdapter
    )
    assert isinstance(
        CurlSubprocessInferenceAdapter(endpoint="http://x/v1", model="m"),
        ProtocolHarnessInferenceAdapter,
    )
    store = SqliteProjectionStore()
    assert isinstance(store, ProtocolHarnessProjectionStore)
    store.close()


@pytest.mark.unit
def test_bus_is_core_in_memory_impl() -> None:
    """The harness bus is the core EventBusInmemory — never an infra bus."""
    harness, _ = build_workflow(
        workflow="delegation",
        adapter=RecordedFixtureInferenceAdapter(),
        store=SqliteProjectionStore(),
    )
    assert isinstance(harness.bus, EventBusInmemory)
    assert harness.bus_impl == "EventBusInmemory"


@pytest.mark.unit
def test_recorded_fixture_adapter_echoes_prompt_by_default() -> None:
    """The default fixture adapter is deterministic and offline."""
    adapter = RecordedFixtureInferenceAdapter()
    out = adapter.infer(ModelInferenceRequest(prompt="echo me"))
    assert out.completion == "[recorded] echo me"
    assert out.adapter == "fixture"


@pytest.mark.unit
def test_no_terminal_when_orchestrator_unregistered() -> None:
    """With no handler for the command topic, no terminal is reached (exit 2)."""
    harness = InProcessHarness(terminal_topics=frozenset({"onex.evt.never.v1"}))
    command = ModelHarnessCommand(
        correlation_id=uuid4(), workflow="delegation", prompt="x"
    )
    envelope: ModelEventEnvelope[ModelHarnessCommand] = ModelEventEnvelope(
        payload=command,
        correlation_id=command.correlation_id,
        event_type="onex.cmd.unrouted.v1",
    )
    result = asyncio.run(
        harness.run(command_topic="onex.cmd.unrouted.v1", command_envelope=envelope)
    )
    assert not result.reached_terminal
    assert result.status == "no_terminal"
    assert result.exit_code == 2


@pytest.mark.unit
def test_build_evidence_packet_is_infra_free_and_complete() -> None:
    """The evidence packet carries the infra-free proof fields."""
    correlation_id = uuid4()
    store = SqliteProjectionStore()
    adapter = RecordedFixtureInferenceAdapter()
    result, projection = asyncio.run(
        run_workflow(
            workflow="delegation",
            prompt="evidence",
            correlation_id=correlation_id,
            task_type="harness",
            max_tokens=32,
            adapter=adapter,
            store=store,
        )
    )
    packet = build_evidence_packet(
        workflow="delegation",
        result=result,
        projection=projection,
        adapter=adapter,
        store=store,
        bus_impl="EventBusInmemory",
        runtime_sha="db7f341",
    )
    assert packet["infra_free"] is True
    assert packet["bus_impl"] == "EventBusInmemory"
    assert packet["inference_adapter"] == "fixture"
    assert str(packet["projection_backend"]).startswith("sqlite:")
    assert packet["exit_code"] == 0
    assert packet["terminal_status"] == "success"
    assert packet["correlation_id"] == str(correlation_id)
    assert packet["projection_row"] is not None
    store.close()


@pytest.mark.unit
def test_harness_modules_carry_no_infra_or_transport_imports() -> None:
    """Static guard: harness source must not import infra/Kafka/LAN transports."""
    src_root = Path(__file__).parents[4] / "src" / "omnibase_core"
    harness_dirs = (
        src_root / "runtime" / "harness",
        src_root / "models" / "runtime" / "harness",
    )
    forbidden = (
        "omnibase_infra",
        "aiokafka",
        "kafka",
        "asyncpg",
        "psycopg",
        "httpx",
        "aiohttp",
        "requests",
    )
    offenders: list[str] = []
    for harness_dir in harness_dirs:
        for py_file in harness_dir.glob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            for token in forbidden:
                if f"import {token}" in text or f"from {token}" in text:
                    offenders.append(f"{py_file.name}: {token}")
    assert not offenders, f"harness imports forbidden transport/infra: {offenders}"


@pytest.mark.unit
def test_infra_not_importable_in_core_environment() -> None:
    """The core venv must not have omnibase_infra installed (infra-free proof)."""
    assert importlib.util.find_spec("omnibase_infra") is None
    assert importlib.util.find_spec("aiokafka") is None
    assert importlib.util.find_spec("asyncpg") is None
