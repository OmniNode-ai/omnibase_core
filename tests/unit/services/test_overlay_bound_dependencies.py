# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Handler dependencies are declared in contracts and bound by overlay (OMN-21595, A7 core half).

The same test bodies run against an overlay that binds core's in-memory bus and
against one that binds a durable-shaped bus (an append-only log with offsets); the
two overlays differ in data only.
"""

import ast
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from typing import Protocol, cast

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_dependency_binding_refusal_reason import (
    EnumDependencyBindingRefusalReason,
)
from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
from omnibase_core.models.contracts.model_contract_base import ModelContractBase
from omnibase_core.models.nodes.handler_dependencies.model_dependency_binding import (
    ModelDependencyBinding,
)
from omnibase_core.models.nodes.handler_dependencies.model_overlay_bindings import (
    ModelOverlayBindings,
)
from omnibase_core.protocols.services.protocol_announce_bus import ProtocolAnnounceBus
from omnibase_core.protocols.services.protocol_announce_inventory_store import (
    ProtocolAnnounceInventoryStore,
)
from omnibase_core.protocols.services.protocol_dependency_factory import (
    ProtocolDependencyFactory,
)

BUS = "ProtocolAnnounceBus"
STORE = "ProtocolAnnounceInventoryStore"


class _LoggedMessage:
    def __init__(self, value: bytes) -> None:
        self.value = value


class _DurableShapedBus:
    """An append-only log with offsets: the shape of a durable bus, with no broker."""

    def __init__(self, partition_count: int) -> None:
        self.partition_count = partition_count
        self.log: dict[str, list[bytes]] = {}
        self.subscriptions: list[str] = []
        self._listeners: dict[
            str, list[Callable[[_LoggedMessage], Awaitable[None]]]
        ] = {}

    async def start(self) -> None:
        return None

    async def publish(self, topic: str, key: bytes | None, value: bytes) -> None:
        self.log.setdefault(topic, []).append(value)
        for listener in self._listeners.get(topic, []):
            await listener(_LoggedMessage(value))

    async def subscribe(
        self,
        topic: str,
        *,
        on_message: Callable[[_LoggedMessage], Awaitable[None]],
        group_id: str,
    ) -> Callable[[], Awaitable[None]]:
        self.subscriptions.append(topic)
        self._listeners.setdefault(topic, []).append(on_message)

        async def cancel() -> None:
            self._listeners[topic].remove(on_message)

        return cancel


class _MemoryStore:
    def __init__(self, label: str) -> None:
        self.label = label
        self.saved: dict[str, str] = {}

    async def load(self, announcer_id: str) -> str | None:
        return self.saved.get(announcer_id)

    async def save(self, announcer_id: str, inventory_json: str) -> None:
        self.saved[announcer_id] = inventory_json


def _factories() -> dict[str, ProtocolDependencyFactory]:
    def in_memory_bus(config: Mapping[str, str]) -> object:
        return EventBusInmemory(
            environment=config["environment"], group=config["group"]
        )

    def durable_bus(config: Mapping[str, str]) -> object:
        return _DurableShapedBus(partition_count=int(config["partitions"]))

    def store(config: Mapping[str, str]) -> object:
        return _MemoryStore(config["label"])

    return {"in_memory_bus": in_memory_bus, "durable_bus": durable_bus, "store": store}


def _overlay(
    implementation: str,
    config: dict[str, str],
    *,
    budget: float = 5.0,
    interval: float | None = 3.0,
    bind_store: bool = True,
) -> ModelOverlayBindings:
    bus = ModelDependencyBinding(
        protocol=BUS, implementation=implementation, config=config
    )
    store = ModelDependencyBinding(
        protocol=STORE, implementation="store", config={"label": "a"}
    )
    return ModelOverlayBindings(
        dependencies=(bus, store) if bind_store else (bus,),
        announcer_bus=bus,
        catalog_store=store,
        lazy_start_budget_seconds=budget,
        reaper_flag_to_delete_days=interval,
    )


OVERLAYS = {
    "in_memory": ("in_memory_bus", {"environment": "test", "group": "g"}),
    "durable": ("durable_bus", {"partitions": "3"}),
}


class _HasValue(Protocol):
    value: bytes


class _AnnounceHandler:
    """A handler that takes its dependencies as constructor arguments and nothing else."""

    def __init__(
        self,
        bus: ProtocolAnnounceBus[_HasValue],
        store: ProtocolAnnounceInventoryStore,
    ) -> None:
        self.bus = bus
        self.store = store

    async def run(self, topic: str, payload: bytes) -> list[bytes]:
        seen: list[bytes] = []

        async def on_message(message: _HasValue) -> None:
            seen.append(message.value)

        await self.bus.start()
        cancel = await self.bus.subscribe(topic, on_message=on_message, group_id="g")
        await self.bus.publish(topic, None, payload)
        await cancel()
        await self.store.save("announcer", payload.decode())
        return seen


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("kind", sorted(OVERLAYS))
async def test_the_same_handler_test_passes_under_each_overlay(kind: str) -> None:
    implementation, config = OVERLAYS[kind]
    overlay = _overlay(implementation, config)
    built = overlay.build([BUS, STORE], _factories())
    assert built.refusal_reason is None
    handler = _AnnounceHandler(
        cast(ProtocolAnnounceBus[_HasValue], built.dependencies[BUS]),
        cast(ProtocolAnnounceInventoryStore, built.dependencies[STORE]),
    )
    assert await handler.run("onex.evt.platform.sample.v1", b"hello") == [b"hello"]
    assert await handler.store.load("announcer") == "hello"


@pytest.mark.unit
def test_overlays_differ_in_data_and_the_handler_does_not() -> None:
    kinds = {kind: _overlay(*OVERLAYS[kind]) for kind in OVERLAYS}
    built = {kind: o.build([BUS, STORE], _factories()) for kind, o in kinds.items()}
    assert type(built["in_memory"].dependencies[BUS]) is EventBusInmemory
    assert type(built["durable"].dependencies[BUS]) is _DurableShapedBus
    assert isinstance(built["in_memory"].dependencies[BUS], ProtocolAnnounceBus)
    assert isinstance(built["durable"].dependencies[BUS], ProtocolAnnounceBus)


@pytest.mark.unit
@pytest.mark.parametrize("kind", sorted(OVERLAYS))
def test_an_unbound_dependency_is_refused_before_any_factory_runs(kind: str) -> None:
    implementation, config = OVERLAYS[kind]
    overlay = _overlay(implementation, config, bind_store=False)
    built_so_far: list[str] = []
    factories = {
        name: _recording(name, factory, built_so_far)
        for name, factory in _factories().items()
    }
    built = overlay.build([BUS, STORE], factories)
    assert built.refusal_reason is EnumDependencyBindingRefusalReason.DEPENDENCY_UNBOUND
    assert built.unbound == (STORE,)
    assert built.dependencies == {}
    assert built_so_far == [], (
        "a refused contract built nothing, so it subscribed to nothing"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_a_refused_contract_leaves_the_bus_with_no_subscription() -> None:
    overlay = _overlay("durable_bus", {"partitions": "3"}, bind_store=False)
    bus = overlay.build_announcer_bus(_factories()).dependencies[BUS]
    assert isinstance(bus, _DurableShapedBus)
    built = overlay.build([BUS, STORE], _factories())
    assert built.refusal_reason is EnumDependencyBindingRefusalReason.DEPENDENCY_UNBOUND
    assert bus.subscriptions == []
    # control: the same bus does record a subscription when one is made
    await bus.subscribe("t", on_message=_ignore, group_id="g")
    assert bus.subscriptions == ["t"]


async def _ignore(message: _LoggedMessage) -> None:
    return None


def _recording(
    name: str, factory: ProtocolDependencyFactory, built: list[str]
) -> ProtocolDependencyFactory:
    def record(config: Mapping[str, str]) -> object:
        built.append(name)
        return factory(config)

    return record


@pytest.mark.unit
def test_an_implementation_without_a_factory_is_refused_and_builds_nothing() -> None:
    overlay = _overlay("durable_bus", {"partitions": "3"})
    built_so_far: list[str] = []
    factories = {
        name: _recording(name, factory, built_so_far)
        for name, factory in _factories().items()
        if name != "store"
    }
    built = overlay.build([BUS, STORE], factories)
    assert (
        built.refusal_reason
        is EnumDependencyBindingRefusalReason.IMPLEMENTATION_NOT_REGISTERED
    )
    assert built.unregistered == ("store",)
    assert built_so_far == []


@pytest.mark.unit
def test_a_contract_with_nothing_declared_builds_nothing_and_is_not_refused() -> None:
    built = _overlay("durable_bus", {"partitions": "3"}).build([], _factories())
    assert built.refusal_reason is None
    assert built.dependencies == {}


@pytest.mark.unit
def test_a_protocol_bound_twice_is_rejected() -> None:
    binding = ModelDependencyBinding(
        protocol=BUS, implementation="durable_bus", config={}
    )
    with pytest.raises(ValidationError, match="more than once"):
        ModelOverlayBindings(
            dependencies=(binding, binding),
            announcer_bus=binding,
            catalog_store=binding,
            lazy_start_budget_seconds=1.0,
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("budget", "interval"), [(5.0, 3.0), (0.5, 30.0), (120.0, None)]
)
def test_budget_and_interval_follow_the_overlay(
    budget: float, interval: float | None
) -> None:
    overlay = _overlay(
        "durable_bus", {"partitions": "3"}, budget=budget, interval=interval
    )
    assert overlay.lazy_start_budget_seconds == budget
    assert overlay.reaper_flag_to_delete_days == interval


@pytest.mark.unit
@pytest.mark.parametrize("kind", sorted(OVERLAYS))
def test_the_announcer_bus_and_catalog_store_follow_the_overlay(kind: str) -> None:
    implementation, config = OVERLAYS[kind]
    overlay = _overlay(implementation, config)
    bus = overlay.build_announcer_bus(_factories()).dependencies[BUS]
    assert type(bus) is (EventBusInmemory if kind == "in_memory" else _DurableShapedBus)
    store = overlay.build_catalog_store(_factories()).dependencies[STORE]
    assert isinstance(store, _MemoryStore)


@pytest.mark.unit
@pytest.mark.parametrize(
    "omitted", ["announcer_bus", "catalog_store", "lazy_start_budget_seconds"]
)
def test_the_overlay_has_no_default_for_the_bus_the_store_or_the_budget(
    omitted: str,
) -> None:
    binding = {"protocol": BUS, "implementation": "durable_bus", "config": {}}
    fields: dict[str, object] = {
        "dependencies": [],
        "announcer_bus": binding,
        "catalog_store": binding,
        "lazy_start_budget_seconds": 1.0,
    }
    ModelOverlayBindings.model_validate(fields)  # control: all present is valid
    del fields[omitted]
    with pytest.raises(ValidationError, match=omitted):
        ModelOverlayBindings.model_validate(fields)
    assert (
        ModelOverlayBindings.model_fields["reaper_flag_to_delete_days"].default is None
    )


_PACKAGE = (
    Path(__file__).resolve().parents[3]
    / "src/omnibase_core/models/nodes/handler_dependencies"
)


def _numeric_defaults(source: str) -> list[int]:
    tree = ast.parse(source)
    found: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and isinstance(node.value, ast.Constant):
            if isinstance(node.value.value, (int, float)) and not isinstance(
                node.value.value, bool
            ):
                found.append(node.lineno)
    return found


@pytest.mark.unit
def test_no_module_of_the_binding_package_holds_a_numeric_default_or_reads_the_environment() -> (
    None
):
    sources = sorted(_PACKAGE.glob("*.py"))
    assert len(sources) >= 4, "the scan found the package"
    for path in sources:
        tree = ast.parse(path.read_text())
        assert _numeric_defaults(path.read_text()) == [], path.name
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                assert not (
                    isinstance(node.value, ast.Name) and node.value.id == "os"
                ), path.name


@pytest.mark.unit
def test_the_numeric_default_scan_catches_a_planted_constant() -> None:
    assert _numeric_defaults("class M:\n    budget: float = 5.0\n") == [2]
    assert _numeric_defaults("class M:\n    budget: float\n") == []


@pytest.mark.unit
def test_the_contract_block_accepts_unique_protocols_and_rejects_the_rest() -> None:
    assert "handler_dependencies" in ModelContractBase.model_fields
    assert (
        ModelContractBase.model_fields["handler_dependencies"].default_factory is list
    )
    assert ModelContractBase.validate_handler_dependencies([BUS, STORE]) == [BUS, STORE]
    with pytest.raises(ValueError, match="repeat"):
        ModelContractBase.validate_handler_dependencies([BUS, BUS])
    with pytest.raises(ValueError, match="non-empty"):
        ModelContractBase.validate_handler_dependencies([" "])
