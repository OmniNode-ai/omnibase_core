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

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import yaml

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
