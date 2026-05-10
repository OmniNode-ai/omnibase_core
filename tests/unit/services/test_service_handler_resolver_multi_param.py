# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for multi-param known injection in ServiceHandlerResolver (OMN-10278).

Verifies the extended Step 4 that resolves handlers requiring any combination
of the known injectable params: event_bus, container, ownership_query.
"""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_handler_resolution_outcome import (
    EnumHandlerResolutionOutcome,
)
from omnibase_core.models.resolver.model_handler_resolver_context import (
    ModelHandlerResolverContext,
)
from omnibase_core.services.service_handler_resolver import ServiceHandlerResolver


class _FakeEventBus:
    pass


class _FakeContainer:
    pass


@pytest.mark.unit
def test_resolves_handler_with_event_bus_and_container() -> None:
    """Handler requiring both event_bus and container is resolved via known params."""

    class HandlerMultiParam:
        def __init__(self, event_bus: _FakeEventBus, container: _FakeContainer) -> None:
            self.event_bus = event_bus
            self.container = container

    ctx = ModelHandlerResolverContext(
        handler_cls=HandlerMultiParam,
        handler_module="test",
        handler_name="HandlerMultiParam",
        contract_name="test_contract",
        node_name="test_node",
        event_bus=_FakeEventBus(),
        container=_FakeContainer(),
    )
    resolution = ServiceHandlerResolver().resolve(ctx)
    assert resolution.outcome == EnumHandlerResolutionOutcome.RESOLVED_VIA_KNOWN_PARAMS
    assert isinstance(resolution.handler_instance, HandlerMultiParam)


@pytest.mark.unit
def test_resolves_handler_with_single_container_param() -> None:
    """Handler requiring only container is resolved via known params."""

    class HandlerContainerOnly:
        def __init__(self, container: _FakeContainer) -> None:
            self.container = container

    ctx = ModelHandlerResolverContext(
        handler_cls=HandlerContainerOnly,
        handler_module="test",
        handler_name="HandlerContainerOnly",
        contract_name="test_contract",
        node_name="test_node",
        container=_FakeContainer(),
    )
    resolution = ServiceHandlerResolver().resolve(ctx)
    assert resolution.outcome == EnumHandlerResolutionOutcome.RESOLVED_VIA_KNOWN_PARAMS
    assert isinstance(resolution.handler_instance, HandlerContainerOnly)


@pytest.mark.unit
def test_raises_when_required_known_param_is_none_in_context() -> None:
    """Handler requires container but context.container is None — must fail at Step 6."""

    class HandlerContainerOnly:
        def __init__(self, container: object) -> None:
            self.container = container

    ctx = ModelHandlerResolverContext(
        handler_cls=HandlerContainerOnly,
        handler_module="test",
        handler_name="HandlerContainerOnly",
        contract_name="test_contract",
        node_name="test_node",
        event_bus=_FakeEventBus(),
        container=None,
    )
    with pytest.raises(TypeError, match="HandlerContainerOnly"):
        ServiceHandlerResolver().resolve(ctx)


@pytest.mark.unit
def test_existing_single_event_bus_still_resolves() -> None:
    """Existing single-event_bus handlers still resolve (regression test)."""

    class HandlerSingleBus:
        def __init__(self, event_bus: _FakeEventBus) -> None:
            self.event_bus = event_bus

    ctx = ModelHandlerResolverContext(
        handler_cls=HandlerSingleBus,
        handler_module="test",
        handler_name="HandlerSingleBus",
        contract_name="test_contract",
        node_name="test_node",
        event_bus=_FakeEventBus(),
    )
    resolution = ServiceHandlerResolver().resolve(ctx)
    # RESOLVED_VIA_KNOWN_PARAMS subsumes the old RESOLVED_VIA_EVENT_BUS path.
    assert resolution.outcome in {
        EnumHandlerResolutionOutcome.RESOLVED_VIA_KNOWN_PARAMS,
        EnumHandlerResolutionOutcome.RESOLVED_VIA_EVENT_BUS,
    }
    assert resolution.handler_instance is not None


@pytest.mark.unit
def test_known_param_missing_from_context_falls_through_to_type_error() -> None:
    """Handler has unknown required param — not satisfiable, raises TypeError."""

    class HandlerUnknownDep:
        def __init__(self, unknown_service: object) -> None:
            self.unknown_service = unknown_service

    ctx = ModelHandlerResolverContext(
        handler_cls=HandlerUnknownDep,
        handler_module="test",
        handler_name="HandlerUnknownDep",
        contract_name="test_contract",
        node_name="test_node",
        event_bus=_FakeEventBus(),
        container=_FakeContainer(),
    )
    with pytest.raises(TypeError, match="HandlerUnknownDep"):
        ServiceHandlerResolver().resolve(ctx)
