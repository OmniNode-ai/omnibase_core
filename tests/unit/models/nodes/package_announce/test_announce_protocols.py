# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The seams the overlay binds are protocols; core's in-memory bus is one binding (OMN-21589, A1 AC10)."""

from importlib.metadata import Distribution
from pathlib import Path

import pytest

from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
from omnibase_core.models.event_bus.model_event_message import ModelEventMessage
from omnibase_core.models.nodes.package_announce.model_announce_inventory import (
    ModelAnnounceInventory,
)
from omnibase_core.protocols.services.protocol_announce_bus import ProtocolAnnounceBus
from omnibase_core.protocols.services.protocol_announce_distribution_source import (
    ProtocolAnnounceDistributionSource,
)
from omnibase_core.protocols.services.protocol_announce_inventory_store import (
    ProtocolAnnounceInventoryStore,
)


class _MemoryInventoryStore:
    def __init__(self) -> None:
        self.saved: dict[str, str] = {}

    async def load(self, announcer_id: str) -> str | None:
        return self.saved.get(announcer_id)

    async def save(self, announcer_id: str, inventory_json: str) -> None:
        self.saved[announcer_id] = inventory_json


class _EmptyDistributionSource:
    def distributions(self) -> tuple[Distribution, ...]:
        return ()

    def search_roots(self) -> tuple[Path, ...]:
        return ()


class _NotABus:
    async def start(self) -> None:
        return None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_the_in_memory_bus_is_a_binding_of_the_bus_protocol() -> None:
    bus: ProtocolAnnounceBus[ModelEventMessage] = EventBusInmemory(
        environment="test", group="announce"
    )
    assert isinstance(bus, ProtocolAnnounceBus)
    seen: list[bytes] = []

    async def on_message(message: ModelEventMessage) -> None:
        seen.append(message.value)

    await bus.start()
    unsubscribe = await bus.subscribe(
        "onex.evt.fixture.x.v1", on_message=on_message, group_id="g"
    )
    await bus.publish("onex.evt.fixture.x.v1", b"k", b"payload")
    await unsubscribe()
    await bus.publish("onex.evt.fixture.x.v1", b"k", b"after-unsubscribe")
    assert seen == [b"payload"]


@pytest.mark.unit
def test_a_class_missing_the_bus_operations_is_not_a_binding() -> None:
    """Planted violation: a bus that cannot publish or subscribe must not satisfy the protocol."""
    assert not isinstance(_NotABus(), ProtocolAnnounceBus)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inventory_store_and_distribution_source_are_bindable_by_shape() -> None:
    store = _MemoryInventoryStore()
    assert isinstance(store, ProtocolAnnounceInventoryStore)
    assert isinstance(_EmptyDistributionSource(), ProtocolAnnounceDistributionSource)
    assert await store.load("a") is None
    await store.save(
        "a", ModelAnnounceInventory(generations={"alpha-pkg": 2}).model_dump_json()
    )
    loaded = await store.load("a")
    assert loaded is not None
    assert ModelAnnounceInventory.model_validate_json(loaded).generations == {
        "alpha-pkg": 2
    }
