# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the core-resident RuntimeLocal (OMN-13444, local-first re-convergence).

RuntimeLocal + LocalRuntimeBusAdapter were relocated from omnibase_infra into
omnibase_core.runtime so the local runtime installs/runs from core alone, with
no omnibase_infra dependency on any path. These tests cover the parts that are
infra-free and therefore must pass core-resident:

- ``parse_backend_overrides`` validation
- ``RuntimeLocal._create_event_bus`` selection logic (inmemory default,
  unsupported rejection, kafka entry-point dispatch, kafka_bootstrap routed
  through the provider ``from_bootstrap`` factory — never an infra symbol)
- structural conformance of core ``EventBusInmemory`` to ``ProtocolLocalRuntimeBus``
"""

from __future__ import annotations

import json
import uuid as _uuid_module
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import yaml
from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_workflow_result import EnumWorkflowResult
from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.protocols.runtime.protocol_local_runtime_bus import (
    ProtocolLocalRuntimeBus,
)
from omnibase_core.runtime.runtime_local import (
    KNOWN_BACKEND_KEYS,
    SUPPORTED_EVENT_BUS_VALUES,
    RuntimeLocal,
    parse_backend_overrides,
)


@pytest.fixture
def workflow_path(tmp_path: Path) -> Path:
    """A throwaway workflow contract path; never read by these tests."""
    target = tmp_path / "workflow.yaml"
    target.write_text("workflow_id: test\n", encoding="utf-8")
    return target


# ---------------------------------------------------------------------------
# parse_backend_overrides
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_known_backend_keys_includes_kafka_bootstrap() -> None:
    assert "kafka_bootstrap" in KNOWN_BACKEND_KEYS
    assert "event_bus" in KNOWN_BACKEND_KEYS


@pytest.mark.unit
def test_parse_backend_overrides_accepts_kafka_bootstrap() -> None:
    overrides = parse_backend_overrides(
        ("event_bus=kafka", "kafka_bootstrap=kafka.example.invalid:19092")
    )
    assert overrides == {
        "event_bus": "kafka",
        "kafka_bootstrap": "kafka.example.invalid:19092",
    }


@pytest.mark.unit
def test_parse_backend_overrides_rejects_unknown_key() -> None:
    with pytest.raises(ModelOnexError) as exc_info:
        parse_backend_overrides(("nonsense=value",))
    assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_INPUT


@pytest.mark.unit
def test_parse_backend_overrides_rejects_missing_equals() -> None:
    with pytest.raises(ModelOnexError) as exc_info:
        parse_backend_overrides(("event_bus",))
    assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_INPUT


# ---------------------------------------------------------------------------
# Default behavior: in-memory bus (core-native, no infra)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_create_event_bus_default_is_inmemory(workflow_path: Path) -> None:
    runtime = RuntimeLocal(workflow_path=workflow_path)
    bus = runtime._create_event_bus()
    assert isinstance(bus, EventBusInmemory)


@pytest.mark.unit
def test_create_event_bus_explicit_inmemory(workflow_path: Path) -> None:
    runtime = RuntimeLocal(
        workflow_path=workflow_path,
        backend_overrides={"event_bus": "inmemory"},
    )
    bus = runtime._create_event_bus()
    assert isinstance(bus, EventBusInmemory)


@pytest.mark.unit
def test_core_inmemory_bus_satisfies_local_runtime_bus_protocol(
    workflow_path: Path,
) -> None:
    """Core EventBusInmemory structurally satisfies ProtocolLocalRuntimeBus.

    This is the key invariant for the relocation: the default in-memory path
    needs no adapter because the core bus already conforms to the protocol the
    relocated runtime depends on.
    """
    bus = EventBusInmemory(environment="local", group="runtime-local")
    assert isinstance(bus, ProtocolLocalRuntimeBus)


# ---------------------------------------------------------------------------
# Unsupported event_bus values are rejected (no silent fallback)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_supported_event_bus_values_set() -> None:
    assert frozenset({"inmemory", "kafka"}) == SUPPORTED_EVENT_BUS_VALUES


@pytest.mark.unit
@pytest.mark.parametrize(
    "bad_value",
    ["kafak", "redis", "rabbitmq", "Kafka", "KAFKA", "in-memory", "", " "],
)
def test_create_event_bus_rejects_unsupported_value(
    workflow_path: Path, bad_value: str
) -> None:
    runtime = RuntimeLocal(
        workflow_path=workflow_path,
        backend_overrides={"event_bus": bad_value},
    )

    with pytest.raises(ModelOnexError) as exc_info:
        runtime._create_event_bus()

    assert exc_info.value.error_code == EnumCoreErrorCode.CONFIGURATION_ERROR
    assert repr(bad_value) in str(exc_info.value) or bad_value in str(exc_info.value)
    assert "inmemory" in str(exc_info.value)
    assert "kafka" in str(exc_info.value)


# ---------------------------------------------------------------------------
# event_bus=kafka — entry-point dispatch (no infra symbol named in core)
# ---------------------------------------------------------------------------


class _StubKafkaBus:
    """Stand-in for the onex.backends Kafka provider for unit-test isolation."""

    def __init__(self, bootstrap_seen: str | None = None) -> None:
        self.bootstrap_seen = bootstrap_seen

    @classmethod
    def default(cls) -> _StubKafkaBus:
        return cls()

    @classmethod
    def from_bootstrap(cls, bootstrap: str) -> _StubKafkaBus:
        return cls(bootstrap_seen=bootstrap)


def _stub_entry_points_with_kafka(stub_cls: type) -> Any:
    """Build a fake importlib.metadata.entry_points() result returning *stub_cls*."""
    fake_ep = MagicMock()
    fake_ep.name = "event_bus_kafka"
    fake_ep.load = MagicMock(return_value=stub_cls)

    container = MagicMock()
    container.select = MagicMock(return_value=[fake_ep])
    return container


@pytest.mark.unit
def test_create_event_bus_kafka_uses_entry_point(workflow_path: Path) -> None:
    runtime = RuntimeLocal(
        workflow_path=workflow_path,
        backend_overrides={"event_bus": "kafka"},
    )
    fake_eps = _stub_entry_points_with_kafka(_StubKafkaBus)

    with patch(
        "omnibase_core.runtime.runtime_local.importlib.metadata.entry_points",
        return_value=fake_eps,
    ):
        bus = runtime._create_event_bus()

    assert isinstance(bus, _StubKafkaBus)
    fake_eps.select.assert_called_once_with(group="onex.backends")


@pytest.mark.unit
def test_create_event_bus_kafka_missing_entry_point_raises(
    workflow_path: Path,
) -> None:
    runtime = RuntimeLocal(
        workflow_path=workflow_path,
        backend_overrides={"event_bus": "kafka"},
    )
    empty_container = MagicMock()
    empty_container.select = MagicMock(return_value=[])

    with patch(
        "omnibase_core.runtime.runtime_local.importlib.metadata.entry_points",
        return_value=empty_container,
    ):
        with pytest.raises(ModelOnexError) as exc_info:
            runtime._create_event_bus()

    assert exc_info.value.error_code == EnumCoreErrorCode.CONFIGURATION_ERROR


@pytest.mark.unit
def test_create_event_bus_kafka_load_failure_raises(workflow_path: Path) -> None:
    runtime = RuntimeLocal(
        workflow_path=workflow_path,
        backend_overrides={"event_bus": "kafka"},
    )
    bad_ep = MagicMock()
    bad_ep.name = "event_bus_kafka"
    bad_ep.load = MagicMock(side_effect=ImportError("no kafka here"))

    container = MagicMock()
    container.select = MagicMock(return_value=[bad_ep])

    with patch(
        "omnibase_core.runtime.runtime_local.importlib.metadata.entry_points",
        return_value=container,
    ):
        with pytest.raises(ModelOnexError) as exc_info:
            runtime._create_event_bus()

    assert exc_info.value.error_code == EnumCoreErrorCode.CONFIGURATION_ERROR


@pytest.mark.unit
def test_create_event_bus_kafka_no_default_factory_raises(
    workflow_path: Path,
) -> None:
    class _BogusBus:
        pass

    runtime = RuntimeLocal(
        workflow_path=workflow_path,
        backend_overrides={"event_bus": "kafka"},
    )
    fake_eps = _stub_entry_points_with_kafka(_BogusBus)

    with patch(
        "omnibase_core.runtime.runtime_local.importlib.metadata.entry_points",
        return_value=fake_eps,
    ):
        with pytest.raises(ModelOnexError) as exc_info:
            runtime._create_event_bus()

    assert exc_info.value.error_code == EnumCoreErrorCode.CONFIGURATION_ERROR


# ---------------------------------------------------------------------------
# kafka_bootstrap override routes through the provider from_bootstrap factory
# (core never names an omnibase_infra symbol — OMN-13444 AC#2)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_kafka_bootstrap_override_uses_from_bootstrap_factory(
    workflow_path: Path,
) -> None:
    runtime = RuntimeLocal(
        workflow_path=workflow_path,
        backend_overrides={
            "event_bus": "kafka",
            "kafka_bootstrap": "kafka.example.invalid:19092",
        },
    )
    fake_eps = _stub_entry_points_with_kafka(_StubKafkaBus)

    with patch(
        "omnibase_core.runtime.runtime_local.importlib.metadata.entry_points",
        return_value=fake_eps,
    ):
        bus = runtime._create_event_bus()

    assert isinstance(bus, _StubKafkaBus)
    assert bus.bootstrap_seen == "kafka.example.invalid:19092"


@pytest.mark.unit
def test_kafka_bootstrap_override_missing_factory_raises(
    workflow_path: Path,
) -> None:
    """Provider exposes default() but not from_bootstrap() → fail fast."""

    class _DefaultOnlyBus:
        @classmethod
        def default(cls) -> _DefaultOnlyBus:
            return cls()

    runtime = RuntimeLocal(
        workflow_path=workflow_path,
        backend_overrides={
            "event_bus": "kafka",
            "kafka_bootstrap": "kafka.example.invalid:19092",
        },
    )
    fake_eps = _stub_entry_points_with_kafka(_DefaultOnlyBus)

    with patch(
        "omnibase_core.runtime.runtime_local.importlib.metadata.entry_points",
        return_value=fake_eps,
    ):
        with pytest.raises(ModelOnexError) as exc_info:
            runtime._create_event_bus()

    assert exc_info.value.error_code == EnumCoreErrorCode.CONFIGURATION_ERROR
    assert "from_bootstrap" in str(exc_info.value)


@pytest.mark.unit
def test_kafka_default_path_uses_default_factory(workflow_path: Path) -> None:
    """No kafka_bootstrap override → provider default() factory is used."""
    runtime = RuntimeLocal(
        workflow_path=workflow_path,
        backend_overrides={"event_bus": "kafka"},
    )
    fake_eps = _stub_entry_points_with_kafka(_StubKafkaBus)

    with patch(
        "omnibase_core.runtime.runtime_local.importlib.metadata.entry_points",
        return_value=fake_eps,
    ):
        bus = runtime._create_event_bus()

    assert isinstance(bus, _StubKafkaBus)
    assert bus.bootstrap_seen is None


# ---------------------------------------------------------------------------
# _instantiate_handler — runtime-owned dependency injection (OMN-13515)
#
# Regression guard: handlers that declare a mandatory ``event_bus`` positional
# arg (8 omnimarket sweep/orchestrator handlers) must instantiate via the
# runtime path. Before OMN-13515 the runtime injected only ``state_root`` and
# never ``event_bus``, so every such handler crashed with
# ``__init__() missing 1 required positional argument: 'event_bus'``.
# ---------------------------------------------------------------------------


class _HandlerRequiresEventBus:
    """Mirror of the 8 omnimarket handlers: ``event_bus`` is mandatory."""

    def __init__(self, event_bus: ProtocolLocalRuntimeBus) -> None:
        self.event_bus = event_bus


class _HandlerRequiresBusAndState:
    """Handler that takes both runtime-owned deps by name."""

    def __init__(self, event_bus: ProtocolLocalRuntimeBus, state_root: Path) -> None:
        self.event_bus = event_bus
        self.state_root = state_root


class _HandlerTolerantBus:
    """Reference for the already-working ``event_bus=... | None = None`` shape."""

    def __init__(self, event_bus: ProtocolLocalRuntimeBus | None = None) -> None:
        self.event_bus = event_bus


class _HandlerNoDeps:
    """Handler that advertises no runtime-owned params."""

    def __init__(self) -> None:
        self.created = True


_THIS_MODULE = "tests.unit.runtime.test_runtime_local"


@pytest.mark.unit
def test_instantiate_handler_injects_event_bus(workflow_path: Path) -> None:
    """A handler with a mandatory ``event_bus`` param instantiates and receives
    the in-scope runtime bus."""
    runtime = RuntimeLocal(workflow_path=workflow_path)
    bus = EventBusInmemory(environment="local", group="runtime-local")

    instance = runtime._instantiate_handler(
        _THIS_MODULE, "_HandlerRequiresEventBus", bus=bus
    )

    assert isinstance(instance, _HandlerRequiresEventBus)
    assert instance.event_bus is bus


@pytest.mark.unit
def test_instantiate_handler_injects_event_bus_and_state_root(
    workflow_path: Path, tmp_path: Path
) -> None:
    """Both runtime-owned deps are injected by name; neither clobbers the other."""
    state_root = tmp_path / "state"
    runtime = RuntimeLocal(workflow_path=workflow_path, state_root=state_root)
    bus = EventBusInmemory(environment="local", group="runtime-local")

    instance = runtime._instantiate_handler(
        _THIS_MODULE, "_HandlerRequiresBusAndState", bus=bus
    )

    assert isinstance(instance, _HandlerRequiresBusAndState)
    assert instance.event_bus is bus
    assert instance.state_root == state_root


@pytest.mark.unit
def test_instantiate_handler_tolerant_bus_handler_still_works(
    workflow_path: Path,
) -> None:
    """Handlers using ``event_bus: ... | None = None`` still instantiate and now
    receive the real bus rather than ``None``."""
    runtime = RuntimeLocal(workflow_path=workflow_path)
    bus = EventBusInmemory(environment="local", group="runtime-local")

    instance = runtime._instantiate_handler(
        _THIS_MODULE, "_HandlerTolerantBus", bus=bus
    )

    assert isinstance(instance, _HandlerTolerantBus)
    assert instance.event_bus is bus


@pytest.mark.unit
def test_instantiate_handler_no_deps_handler_unaffected(
    workflow_path: Path,
) -> None:
    """A handler that advertises no runtime-owned params still instantiates with
    no kwargs even when a bus is in scope."""
    runtime = RuntimeLocal(workflow_path=workflow_path)
    bus = EventBusInmemory(environment="local", group="runtime-local")

    instance = runtime._instantiate_handler(_THIS_MODULE, "_HandlerNoDeps", bus=bus)

    assert isinstance(instance, _HandlerNoDeps)
    assert instance.created is True


@pytest.mark.unit
def test_instantiate_handler_event_bus_optional_when_no_bus(
    workflow_path: Path,
) -> None:
    """When no bus is threaded (e.g. compute path with bus=None), a handler that
    declares ``event_bus`` is not injected — preserving prior behavior for paths
    that do not own a bus."""
    runtime = RuntimeLocal(workflow_path=workflow_path)

    # A no-dep handler must still work when bus is None.
    instance = runtime._instantiate_handler(_THIS_MODULE, "_HandlerNoDeps", bus=None)
    assert isinstance(instance, _HandlerNoDeps)


# ---------------------------------------------------------------------------
# End-to-end runtime path (OMN-13515) — DoD: load a contract whose handler
# declares a mandatory ``event_bus`` and run the real RuntimeLocal execution
# path; assert zero instantiation failures and a terminal completed result.
# ---------------------------------------------------------------------------

# Captured by the integration test handler so the test can assert the bus was
# actually threaded through the runtime (not merely that instantiation passed).
_EVENT_BUS_HANDLER_CAPTURE: dict[str, object] = {}


class _IntegrationHandlerRequiresEventBus:
    """Mirror of the 8 omnimarket handlers exercised via the real runtime path.

    Declares ``event_bus`` as a mandatory positional arg (the exact shape that
    crashed before OMN-13515) and a sync ``handle()`` that returns a non-failure
    result object so the single-handler path classifies the workflow COMPLETED
    and synthesizes a terminal event.
    """

    def __init__(self, event_bus: ProtocolLocalRuntimeBus) -> None:
        self._event_bus = event_bus
        _EVENT_BUS_HANDLER_CAPTURE["event_bus"] = event_bus

    async def handle(self, payload: object) -> object:
        _EVENT_BUS_HANDLER_CAPTURE["handled"] = True
        # A non-None, non-failure result classifies COMPLETED and triggers the
        # runtime-synthesized terminal event (OMN-8940).
        return {"status": "success"}


def _write_event_bus_handler_contract(target: Path, terminal_topic: str) -> None:
    """Write a single-handler contract pointing at the event-bus-requiring handler."""
    contract = {
        "workflow_id": "omn-13515-event-bus-injection",
        "terminal_event": terminal_topic,
        "event_bus": {"publish_topics": [terminal_topic]},
        "handler": {
            "module": _THIS_MODULE,
            "class": "_IntegrationHandlerRequiresEventBus",
        },
    }
    target.write_text(yaml.safe_dump(contract), encoding="utf-8")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_runtime_local_instantiates_event_bus_handler_end_to_end(
    tmp_path: Path,
) -> None:
    """The real runtime path instantiates a handler with a mandatory ``event_bus``,
    threads the in-memory bus into it, and reaches a COMPLETED terminal result.

    This is the OMN-13515 regression gate: before the fix this run crashed with
    ``__init__() missing 1 required positional argument: 'event_bus'`` and the
    runtime recorded result=FAILED.
    """
    _EVENT_BUS_HANDLER_CAPTURE.clear()
    terminal_topic = "onex.evt.omn13515.completed.v1"
    contract_path = tmp_path / "contract.yaml"
    _write_event_bus_handler_contract(contract_path, terminal_topic)

    runtime = RuntimeLocal(
        workflow_path=contract_path,
        state_root=tmp_path / "state",
        timeout=5,
    )

    result = await runtime.run_async()

    assert result == EnumWorkflowResult.COMPLETED
    # The handler was instantiated (no missing-arg crash) and invoked.
    assert _EVENT_BUS_HANDLER_CAPTURE.get("handled") is True
    # The runtime threaded a real bus into the handler's mandatory event_bus arg.
    captured_bus = _EVENT_BUS_HANDLER_CAPTURE.get("event_bus")
    assert captured_bus is not None
    assert isinstance(captured_bus, ProtocolLocalRuntimeBus)
    assert isinstance(captured_bus, EventBusInmemory)


# ---------------------------------------------------------------------------
# OMN-13591 regression: _build_initial_payload input-file branch must inject
# runtime-owned run-identity (correlation_id, run_id) for required fields that
# are absent from the caller-supplied input file — mirroring the no-input-file
# auto-fill path so ALL dispatch paths are consistent.
# ---------------------------------------------------------------------------

import re


class _ModelRequiresRunIdentity(BaseModel):
    """Minimal stand-in for any start-model that requires run-identity fields.

    Mirrors the critical constraints on ModelPrLifecycleStartCommand:
    - correlation_id: required UUID
    - run_id: required str with min_length=1 and alphanum pattern
    - repos: optional str with default
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    correlation_id: _uuid_module.UUID = Field(..., description="Unique run ID.")
    run_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9._-]+$",
        description="Timestamped run identifier.",
    )
    repos: str = Field(default="", description="Optional repo filter.")


class _ModelRequiresOnlyCorrelationId(BaseModel):
    """Start-model that only requires correlation_id (UUID), not run_id.

    Verifies the fix is targeted — only fields that are both required AND absent
    from the input file get injected.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    correlation_id: _uuid_module.UUID = Field(..., description="Unique run ID.")
    task_name: str = Field(default="default-task")


_THIS_MODULE_FOR_IDENTITY = "tests.unit.runtime.test_runtime_local"

_PROGRESS_TOPIC = "onex.evt.omn13865.progress.v1"
_COMPLETED_TOPIC = "onex.evt.omn13865.completed.v1"


class _ProgressBeforeCompletionHandler:
    """Publishes a non-terminal progress event before returning the final result."""

    def __init__(self, event_bus: ProtocolLocalRuntimeBus) -> None:
        self._event_bus = event_bus

    async def handle(self, payload: _ModelRequiresOnlyCorrelationId) -> dict[str, str]:
        await self._event_bus.publish(
            _PROGRESS_TOPIC,
            None,
            json.dumps(
                {
                    "status": "success",
                    "kind": "progress",
                    "correlation_id": str(payload.correlation_id),
                }
            ).encode("utf-8"),
        )
        return {
            "status": "success",
            "kind": "completed",
            "correlation_id": str(payload.correlation_id),
        }


def _write_event_driven_progress_contract(target: Path) -> None:
    contract: dict[str, Any] = {
        "workflow_id": "omn-13865-progress-is-not-terminal",
        "terminal_event": _COMPLETED_TOPIC,
        "event_bus": {
            "subscribe_topics": ["onex.cmd.omn13865.start.v1"],
            "publish_topics": [_PROGRESS_TOPIC, _COMPLETED_TOPIC],
        },
        "handler_routing": {
            "routing_strategy": "operation_match",
            "handlers": [
                {
                    "operation": "start",
                    "handler": {
                        "module": _THIS_MODULE_FOR_IDENTITY,
                        "name": "_ProgressBeforeCompletionHandler",
                    },
                    "event_model": {
                        "module": _THIS_MODULE_FOR_IDENTITY,
                        "name": "_ModelRequiresOnlyCorrelationId",
                    },
                }
            ],
        },
    }
    target.write_text(yaml.safe_dump(contract), encoding="utf-8")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_event_driven_runtime_waits_for_declared_terminal_event(
    tmp_path: Path,
) -> None:
    """Progress publish_topics must not complete receipt-mode runs.

    The merge_sweep/pr_lifecycle orchestrator publishes phase-transition events
    before its final completed event. RuntimeLocal must subscribe the terminal
    callback only to ``terminal_event``; otherwise the first progress event wins
    and ``workflow_result.json`` loses the final handler result.
    """
    contract_path = tmp_path / "contract.yaml"
    state_root = tmp_path / "state"
    _write_event_driven_progress_contract(contract_path)

    runtime = RuntimeLocal(
        workflow_path=contract_path,
        state_root=state_root,
        timeout=5,
    )

    result = await runtime.run_async()

    assert result == EnumWorkflowResult.COMPLETED
    workflow_data = json.loads((state_root / "workflow_result.json").read_text())
    assert workflow_data["terminal_payload"]["kind"] == "completed"
    assert workflow_data["handler_result"]["kind"] == "completed"


def _write_contract_for_model(
    target: Path, model_class_name: str, terminal_topic: str
) -> None:
    """Write a single-handler contract referencing a model in this test module."""
    contract: dict[str, Any] = {
        "workflow_id": "omn-13591-run-identity-test",
        "terminal_event": terminal_topic,
        "event_bus": {"publish_topics": [terminal_topic]},
        "handler": {
            "module": _THIS_MODULE_FOR_IDENTITY,
            "class": "_HandlerNoDeps",
            "input_model": {
                "module": _THIS_MODULE_FOR_IDENTITY,
                "class": model_class_name,
            },
        },
    }
    target.write_text(yaml.safe_dump(contract), encoding="utf-8")


@pytest.mark.unit
def test_build_initial_payload_input_file_injects_correlation_id_and_run_id(
    tmp_path: Path,
    workflow_path: Path,
) -> None:
    """Regression: input-file branch must inject required run-identity fields.

    BEFORE the fix (OMN-13591):
        _build_initial_payload called cls(**raw) directly → ValidationError:
        correlation_id and run_id are required but absent → ModelOnexError raised.

    AFTER the fix:
        Runtime injects a fresh uuid4 for correlation_id and a timestamped slug
        for run_id when those required fields are absent from the input file,
        then validates successfully. The caller-supplied optional field (repos)
        is preserved unchanged.
    """
    # Caller writes a partial input file — has repos but NOT the required
    # run-identity fields. This is exactly what cli_skill.py produces for
    # args-taking skills like merge_sweep.
    input_file = tmp_path / "merge_sweep_input.json"
    caller_repos = "omnimarket,onex_change_control"
    input_file.write_text(json.dumps({"repos": caller_repos}), encoding="utf-8")

    runtime = RuntimeLocal(
        workflow_path=workflow_path,
        input_path=input_file,
    )

    input_spec = {
        "module": _THIS_MODULE_FOR_IDENTITY,
        "class": "_ModelRequiresRunIdentity",
    }

    # This must NOT raise ModelOnexError — the pre-fix behavior.
    payload = runtime._build_initial_payload(input_spec)

    assert payload is not None, "Expected a valid payload object, got None"
    assert isinstance(payload, _ModelRequiresRunIdentity)

    # Runtime-injected: correlation_id must be a valid UUID (not null/empty).
    assert isinstance(payload.correlation_id, _uuid_module.UUID)

    # Runtime-injected: run_id must satisfy the model's constraints.
    assert len(payload.run_id) >= 1
    assert re.match(r"^[A-Za-z0-9._-]+$", payload.run_id), (
        f"run_id {payload.run_id!r} does not match expected pattern"
    )

    # Caller-supplied: repos must be preserved unchanged.
    assert payload.repos == caller_repos


@pytest.mark.unit
def test_build_initial_payload_input_file_preserves_caller_provided_correlation_id(
    tmp_path: Path,
    workflow_path: Path,
) -> None:
    """When the caller's input file already includes correlation_id, the runtime
    must NOT overwrite it — caller-supplied values take precedence.

    This prevents a race condition where a caller deliberately sets a specific
    correlation_id for cross-system tracing and the runtime silently replaces it.
    """
    caller_correlation_id = _uuid_module.uuid4()
    input_file = tmp_path / "input_with_correlation.json"
    input_file.write_text(
        json.dumps(
            {
                "correlation_id": str(caller_correlation_id),
                "run_id": "20260625-120000-abc123",
            }
        ),
        encoding="utf-8",
    )

    runtime = RuntimeLocal(
        workflow_path=workflow_path,
        input_path=input_file,
    )

    input_spec = {
        "module": _THIS_MODULE_FOR_IDENTITY,
        "class": "_ModelRequiresRunIdentity",
    }

    payload = runtime._build_initial_payload(input_spec)

    assert payload is not None
    assert isinstance(payload, _ModelRequiresRunIdentity)
    # Caller's correlation_id must be preserved exactly.
    assert payload.correlation_id == caller_correlation_id
    assert payload.run_id == "20260625-120000-abc123"


@pytest.mark.unit
def test_build_initial_payload_input_file_injects_only_missing_required_fields(
    tmp_path: Path,
    workflow_path: Path,
) -> None:
    """Only required fields absent from the input file receive injected defaults.

    A model that only requires correlation_id (not run_id) must have only
    correlation_id injected — no extra keys are synthesized.
    """
    input_file = tmp_path / "input_partial.json"
    input_file.write_text(json.dumps({}), encoding="utf-8")

    runtime = RuntimeLocal(
        workflow_path=workflow_path,
        input_path=input_file,
    )

    input_spec = {
        "module": _THIS_MODULE_FOR_IDENTITY,
        "class": "_ModelRequiresOnlyCorrelationId",
    }

    payload = runtime._build_initial_payload(input_spec)

    assert payload is not None
    assert isinstance(payload, _ModelRequiresOnlyCorrelationId)
    assert isinstance(payload.correlation_id, _uuid_module.UUID)
    # task_name has a default — not injected, just uses the model default.
    assert payload.task_name == "default-task"


# ---------------------------------------------------------------------------
# OMN-14298 regression: RuntimeLocal must (1) call ``initialize()`` before the
# fallback ``execute()`` for ONEX init/execute handlers, and (2) NOT surface a
# false-green COMPLETED / exit 0 when a handler returns an error-shaped envelope
# (``status="error"`` / "Handler not initialized"). These two defects together
# produced ``onex node <name>`` runs that reported exit_code 0 over a broken run.
# ---------------------------------------------------------------------------


class _LifecycleResponse(BaseModel):
    """Minimal stand-in for the effect/reducer response envelopes.

    Mirrors ModelArchitectureGraphQueryResponseEvent / ModelNavigationHistoryResponse:
    a ``status`` string (``"success"`` | ``"error"`` | ``"no_results"``) plus an
    optional ``error_message`` populated on the error path.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: str
    error_message: str | None = None


class _InitExecuteLifecycleHandler:
    """Mirrors the ONEX init/execute lifecycle with a zero-arg ``initialize()``.

    ``execute()`` returns a ``status="error"`` envelope until ``initialize()`` has
    run — exactly like HandlerArchitectureGraphQuery and
    HandlerNavigationHistoryReducer. ``initialize()`` takes no required args, so
    RuntimeLocal can and must call it before ``execute()``.
    """

    def __init__(self) -> None:
        self._initialized = False
        self.initialize_calls = 0

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    async def initialize(self) -> None:
        # Idempotent, matching the real handlers' guarded initialize().
        self.initialize_calls += 1
        self._initialized = True

    async def execute(self, request: object) -> _LifecycleResponse:
        if not self._initialized:
            return _LifecycleResponse(
                status="error", error_message="Handler not initialized"
            )
        return _LifecycleResponse(status="success")


class _RequiresArgInitHandler:
    """Lifecycle handler whose ``initialize()`` needs an arg the runtime can't give.

    Mirrors HandlerIntentQuery.initialize(connection_uri: str). RuntimeLocal must
    skip ``initialize()`` (it cannot bind the required parameter) WITHOUT crashing,
    and the resulting not-initialized error envelope must surface FAILED — never a
    false-green COMPLETED.
    """

    def __init__(self) -> None:
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    async def initialize(self, connection_uri: str) -> None:
        self._initialized = True

    async def execute(self, request: object) -> _LifecycleResponse:
        if not self._initialized:
            return _LifecycleResponse(
                status="error", error_message="Handler not initialized"
            )
        return _LifecycleResponse(status="success")


class _AlwaysErrorExecuteHandler:
    """Handler with no ``initialize()`` whose ``execute()`` always returns an error.

    Stands in for a genuinely-failing handler (e.g. a downstream connection
    failure returned in-band). Proves the false-green fix independently of the
    initialize lifecycle: an error-shaped return must map to FAILED / exit 1.
    """

    async def execute(self, request: object) -> _LifecycleResponse:
        return _LifecycleResponse(status="error", error_message="downstream boom")


def _write_compute_handler_contract(target: Path, handler_class_name: str) -> None:
    """Write a terminal-event-less compute contract → the ``_run_compute`` path.

    This is the shape of the affected nodes (effect/reducer contracts declare a
    top-level ``handler`` and no top-level ``terminal_event``), so RuntimeLocal
    resolves the handler, falls back to ``execute()``, and classifies its return.
    """
    contract = {
        "workflow_id": "omn-14298-init-lifecycle",
        "handler": {
            "module": _THIS_MODULE,
            "class": handler_class_name,
        },
    }
    target.write_text(yaml.safe_dump(contract), encoding="utf-8")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_runtime_local_initializes_handler_before_execute(
    tmp_path: Path,
) -> None:
    """Proof (a): an init/execute handler now runs through initialize()→execute().

    BEFORE OMN-14298: RuntimeLocal invoked the fallback ``execute()`` without
    ``initialize()``, so ``execute()`` returned the "Handler not initialized"
    envelope. AFTER: the runtime calls the zero-arg ``initialize()`` first, so
    ``execute()`` runs its real body and returns ``status="success"`` → COMPLETED.
    """
    contract_path = tmp_path / "contract.yaml"
    state_root = tmp_path / "state"
    _write_compute_handler_contract(contract_path, "_InitExecuteLifecycleHandler")

    runtime = RuntimeLocal(
        workflow_path=contract_path,
        state_root=state_root,
        timeout=5,
    )

    result = await runtime.run_async()

    assert result == EnumWorkflowResult.COMPLETED
    assert runtime.exit_code == 0
    # initialize() ran before execute() — proven by the success status, since the
    # handler returns "Handler not initialized" whenever the flag is unset.
    handler_result = runtime.handler_result
    assert isinstance(handler_result, _LifecycleResponse)
    assert handler_result.status == "success"
    assert handler_result.error_message is None

    workflow_data = json.loads((state_root / "workflow_result.json").read_text())
    assert workflow_data["result"] == "completed"
    assert workflow_data["exit_code"] == 0
    assert workflow_data["handler_result"]["status"] == "success"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_runtime_local_error_envelope_surfaces_failed_not_false_green(
    tmp_path: Path,
) -> None:
    """Proof (b): an error-shaped handler return must NOT be a false-green COMPLETED.

    A handler whose ``execute()`` returns ``status="error"`` (the exact shape of
    the "Handler not initialized" / downstream-failure envelope) must terminate
    the workflow FAILED with exit_code 1. Before OMN-14298 the classifier only
    recognised ``status == "failure"``, so this run reported exit_code 0.
    """
    contract_path = tmp_path / "contract.yaml"
    state_root = tmp_path / "state"
    _write_compute_handler_contract(contract_path, "_AlwaysErrorExecuteHandler")

    runtime = RuntimeLocal(
        workflow_path=contract_path,
        state_root=state_root,
        timeout=5,
    )

    result = await runtime.run_async()

    assert result == EnumWorkflowResult.FAILED
    assert runtime.exit_code == 1
    workflow_data = json.loads((state_root / "workflow_result.json").read_text())
    assert workflow_data["result"] == "failed"
    assert workflow_data["exit_code"] == 1
    assert workflow_data["handler_result"]["status"] == "error"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_runtime_local_skips_required_arg_initialize_and_fails_closed(
    tmp_path: Path,
) -> None:
    """A handler whose initialize() needs an unsatisfiable arg fails closed, not green.

    RuntimeLocal cannot supply ``connection_uri`` for the intent-query-shaped
    handler, so it skips ``initialize()`` (without crashing). ``execute()`` then
    returns the not-initialized error envelope, which must surface FAILED — never
    a false COMPLETED.
    """
    contract_path = tmp_path / "contract.yaml"
    state_root = tmp_path / "state"
    _write_compute_handler_contract(contract_path, "_RequiresArgInitHandler")

    runtime = RuntimeLocal(
        workflow_path=contract_path,
        state_root=state_root,
        timeout=5,
    )

    result = await runtime.run_async()

    assert result == EnumWorkflowResult.FAILED
    assert runtime.exit_code == 1
    handler_result = runtime.handler_result
    assert isinstance(handler_result, _LifecycleResponse)
    assert handler_result.status == "error"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ensure_handler_initialized_is_idempotent_and_guarded(
    workflow_path: Path,
) -> None:
    """``_ensure_handler_initialized`` calls initialize() once and is a no-op after.

    Also verifies the two safe no-op branches: an already-initialized handler is
    not re-initialized, and a handler with no ``initialize()`` is left untouched.
    """
    runtime = RuntimeLocal(workflow_path=workflow_path)

    handler = _InitExecuteLifecycleHandler()
    await runtime._ensure_handler_initialized(handler)
    assert handler.is_initialized is True
    assert handler.initialize_calls == 1

    # Second call is a no-op — the handler already reports initialized.
    await runtime._ensure_handler_initialized(handler)
    assert handler.initialize_calls == 1

    # A handler exposing no initialize() must not raise.
    await runtime._ensure_handler_initialized(_AlwaysErrorExecuteHandler())

    # A handler with a required-arg initialize() is skipped, not called/crashed.
    requires_arg = _RequiresArgInitHandler()
    await runtime._ensure_handler_initialized(requires_arg)
    assert requires_arg.is_initialized is False


@pytest.mark.unit
@pytest.mark.parametrize(
    ("status", "error_message", "expected"),
    [
        ("error", "Handler not initialized", EnumWorkflowResult.FAILED),
        ("failure", None, EnumWorkflowResult.FAILED),
        ("failed", None, EnumWorkflowResult.FAILED),
        ("ERROR", None, EnumWorkflowResult.FAILED),
        ("success", None, EnumWorkflowResult.COMPLETED),
        # A successful query that matched nothing must NOT be classified FAILED.
        ("no_results", None, EnumWorkflowResult.COMPLETED),
        # Explicit success wins even if an error_message field lingers.
        ("success", "stale error from prior attempt", EnumWorkflowResult.COMPLETED),
    ],
)
def test_classify_result_status_values(
    status: str, error_message: str | None, expected: EnumWorkflowResult
) -> None:
    """``_classify_result`` maps error-ish statuses to FAILED and success to COMPLETED."""
    result = _LifecycleResponse(status=status, error_message=error_message)
    assert RuntimeLocal._classify_result(result) == expected


@pytest.mark.unit
def test_classify_result_none_is_completed() -> None:
    """A ``None`` return (compute handler that returns nothing) is COMPLETED."""
    assert RuntimeLocal._classify_result(None) == EnumWorkflowResult.COMPLETED


@pytest.mark.unit
@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"status": "error"}, EnumWorkflowResult.FAILED),
        ({"status": "failed"}, EnumWorkflowResult.FAILED),
        ({"status": "success", "error": "stale error"}, EnumWorkflowResult.COMPLETED),
        ({"error_message": "boom"}, EnumWorkflowResult.FAILED),
        ({"cycles_failed": 1}, EnumWorkflowResult.FAILED),
    ],
)
def test_classify_result_mapping_envelopes(
    payload: dict[str, object], expected: EnumWorkflowResult
) -> None:
    """Dict-style response envelopes use the same status/error rules as objects."""
    assert RuntimeLocal._classify_result(payload) == expected


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["failure", "failed", "error", "ERROR"])
async def test_terminal_event_uses_result_classifier(
    tmp_path: Path, status: str
) -> None:
    """Terminal events classify every failure-ish status as FAILED."""
    runtime = RuntimeLocal(
        workflow_path=tmp_path / "contract.yaml",
        state_root=tmp_path / "state",
    )

    runtime._on_terminal_event({"status": status})

    assert runtime._result == EnumWorkflowResult.FAILED


@pytest.mark.unit
def test_classify_result_populated_error_message_without_status_is_failed() -> None:
    """A populated ``error_message`` is a failure signal even with no status field."""

    class _ErrOnly(BaseModel):
        model_config = ConfigDict(frozen=True, extra="forbid")

        error_message: str

    assert (
        RuntimeLocal._classify_result(_ErrOnly(error_message="boom"))
        == EnumWorkflowResult.FAILED
    )


@pytest.mark.unit
def test_classify_result_plain_object_without_failure_markers_is_completed() -> None:
    """An object with neither failure status nor error markers stays COMPLETED."""

    class _Ok(BaseModel):
        model_config = ConfigDict(frozen=True, extra="forbid")

        value: int = 1

    assert RuntimeLocal._classify_result(_Ok()) == EnumWorkflowResult.COMPLETED
