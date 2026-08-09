# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The ``event_bus_substrate`` dual-substrate fixture (OMN-15789).

Provides ``CORE_EVENT_BUS_SUBSTRATE_PARAMS`` and ``build_core_event_bus_substrate``
so that a ``CoreEventBusSubstrate``-conforming instance can be built from a plain
param name, plus a ready-to-import ``event_bus_substrate`` pytest fixture
parameterized over the two core-resident substrates: ``"inmemory"`` (the
existing ``EventBusInmemory``) and ``"semantic_fake"`` (the new
``EventBusSemanticFake``, see ``event_bus_semantic_fake.py``).

This module has zero Kafka dependency, per compat -> core -> spi -> infra
layering (core must stay dependency-minimal). ``omnibase_infra`` extends this
same fixture NAME with a third ``"real_broker"`` param in its own
``tests/conftest.py``, reusing :func:`build_core_event_bus_substrate` for the
two shared legs and adding a real ``EventBusKafka``-backed leg gated on the
existing ``KAFKA_BOOTSTRAP_SERVERS`` + ``KAFKA_INTEGRATION_TESTS=1`` opt-in
(matching ``omnibase_infra/tests/integration/event_bus/test_kafka_event_bus_integration.py``).

Usage (any test module, in either repo)::

    from omnibase_core.event_bus.testing.fixture_event_bus_substrate import (
        event_bus_substrate,
    )

    async def test_something(event_bus_substrate: CoreEventBusSubstrate) -> None:
        ...

Importing the fixture function by name into a ``conftest.py`` (or directly
into a test module) is what registers it with pytest -- the standard pattern
for a fixture shipped from a library rather than defined locally.

.. versionadded:: OMN-15789
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

import pytest_asyncio

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
from omnibase_core.event_bus.event_bus_semantic_fake import EventBusSemanticFake

if TYPE_CHECKING:
    import pytest

#: The core-resident concrete substrate types this module builds. Typed as a
#: Union of the CONCRETE classes, not the abstract ``ProtocolEventBus``:
#: neither ``EventBusInmemory`` nor ``EventBusSemanticFake`` statically
#: satisfies that protocol under mypy --strict today (pre-existing drift
#: between the protocol's declared shape -- e.g. ``adapter ->
#: ProtocolKafkaEventBusAdapter``, ``broadcast_to_environment`` payload typed
#: ``dict[str, ProtocolContextValue]`` -- and every concrete implementation's
#: actual signature; nothing in this repo declares a ``-> ProtocolEventBus``
#: return type today). Both classes are ``ProtocolEventBus``-conformant by
#: DUCK TYPING per ONEX convention (see each class's own docstring) and are
#: used as such by every caller; re-litigating that pre-existing static/duck
#: typing gap is out of OMN-15789's scope. omnibase_infra's fixture override
#: widens this same alias to include ``EventBusKafka``.
CoreEventBusSubstrate = EventBusInmemory | EventBusSemanticFake

#: The two substrate params buildable with zero infrastructure. Kept as a
#: plain tuple (not a pytest.param list) so omnibase_infra can splice its own
#: marked "real_broker" pytest.param onto the end without re-deriving this
#: list.
CORE_EVENT_BUS_SUBSTRATE_PARAMS: tuple[str, ...] = ("inmemory", "semantic_fake")

#: The substrate params REQUIRED to hold the full broker-fidelity contract
#: (join/leave gating, auto_offset_reset, commit-offset resume, rebalance
#: window). Deliberately excludes "inmemory": EventBusInmemory predates this
#: ticket and has no group/offset/rebalance concept at all -- that gap is
#: this ticket's premise, not a regression to fix here. omnibase_infra's
#: override adds "real_broker" to this list too.
CORE_FIDELITY_SUBSTRATE_PARAMS: tuple[str, ...] = ("semantic_fake",)

#: Shared test topic/environment/group constants so a caller can build a
#: substrate identically to how the fixture itself builds one.
DEFAULT_SUBSTRATE_ENVIRONMENT: str = "test"
DEFAULT_SUBSTRATE_GROUP: str = "event-bus-substrate-fixture"


def build_core_event_bus_substrate_instance(param: str) -> CoreEventBusSubstrate:
    """Construct (but do not start) a core-resident substrate for ``param``.

    Args:
        param: ``"inmemory"`` or ``"semantic_fake"``.

    Returns:
        An unstarted ``CoreEventBusSubstrate``-conforming instance.

    Raises:
        ValueError: If ``param`` is not a recognized core-resident substrate
            name. (``"real_broker"`` is infra-only -- see module docstring.)
    """
    if param == "inmemory":
        return EventBusInmemory(
            environment=DEFAULT_SUBSTRATE_ENVIRONMENT,
            group=DEFAULT_SUBSTRATE_GROUP,
        )
    if param == "semantic_fake":
        return EventBusSemanticFake(
            environment=DEFAULT_SUBSTRATE_ENVIRONMENT,
            group=DEFAULT_SUBSTRATE_GROUP,
        )
    raise ModelOnexError(
        f"Unrecognized core event_bus_substrate param: {param!r}. "
        f"Expected one of {CORE_EVENT_BUS_SUBSTRATE_PARAMS!r} "
        f"('real_broker' is infra-only, see omnibase_infra's own "
        f"event_bus_substrate fixture override).",
        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
    )


async def build_core_event_bus_substrate(
    param: str,
) -> AsyncIterator[CoreEventBusSubstrate]:
    """Build, start, yield, and close a core-resident substrate for ``param``.

    An async generator so it composes directly as the body of a pytest
    fixture (``yield``-based) in either this module's own fixture or a
    caller's extended one.
    """
    bus = build_core_event_bus_substrate_instance(param)
    await bus.start()
    try:
        yield bus
    finally:
        await bus.close()


@pytest_asyncio.fixture(params=CORE_EVENT_BUS_SUBSTRATE_PARAMS)
async def event_bus_substrate(
    request: pytest.FixtureRequest,
) -> AsyncIterator[CoreEventBusSubstrate]:
    """Yield one started ``CoreEventBusSubstrate`` instance per param.

    Core-resident params: ``"inmemory"``, ``"semantic_fake"``. Import this
    fixture into a ``conftest.py`` to use it directly (no Kafka needed).
    ``omnibase_infra`` defines its own same-named fixture with a third
    ``"real_broker"`` param -- see the module docstring.
    """
    async for bus in build_core_event_bus_substrate(request.param):
        yield bus


@pytest_asyncio.fixture(params=CORE_FIDELITY_SUBSTRATE_PARAMS)
async def fidelity_event_bus_substrate(
    request: pytest.FixtureRequest,
) -> AsyncIterator[CoreEventBusSubstrate]:
    """Yield one started substrate per fidelity-contract-required param.

    Core-resident: ``"semantic_fake"`` only. ``omnibase_infra`` overrides
    this fixture to add ``"real_broker"``. See
    ``CORE_FIDELITY_SUBSTRATE_PARAMS`` for why ``"inmemory"`` is excluded.
    """
    async for bus in build_core_event_bus_substrate(request.param):
        yield bus


__all__: list[str] = [
    "CORE_EVENT_BUS_SUBSTRATE_PARAMS",
    "CORE_FIDELITY_SUBSTRATE_PARAMS",
    "DEFAULT_SUBSTRATE_ENVIRONMENT",
    "DEFAULT_SUBSTRATE_GROUP",
    "build_core_event_bus_substrate",
    "build_core_event_bus_substrate_instance",
    "event_bus_substrate",
    "fidelity_event_bus_substrate",
]
