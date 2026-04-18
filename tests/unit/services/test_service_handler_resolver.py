# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for HandlerResolver (OMN-9199 Task 3).

Each test exercises one precedence branch in isolation plus the negative
cases described in the plan:

    Step 1 - ownership skip
    Step 2 - explicit deps win over container
    Step 3 - container hit
    Step 3 - container miss (ServiceResolutionError) -> fallthrough
    Step 3 - container internal bug propagates (non-miss)
    Step 4 - event_bus injection
    Step 5 - zero-arg
    Step 6 - unresolvable raises TypeError
    Step 2 - incomplete explicit deps surface missing key in TypeError
    Conflict overlap logs at DEBUG
    Ownership query without is_owned_here attr is ignored (duck-typed)
"""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import MagicMock

import pytest

from omnibase_core.enums.enum_handler_resolution_outcome import (
    EnumHandlerResolutionOutcome,
)
from omnibase_core.errors.error_service_resolution import ServiceResolutionError
from omnibase_core.models.resolver.model_handler_resolver_context import (
    ModelHandlerResolverContext,
)
from omnibase_core.services.service_handler_resolver import HandlerResolver


class _HandlerNoDeps:
    async def handle(self, envelope: object) -> None:
        return None


class _HandlerEventBusOnly:
    def __init__(self, event_bus: object) -> None:
        self.event_bus = event_bus

    async def handle(self, envelope: object) -> None:
        return None


class _HandlerWithDeps:
    def __init__(self, projection_reader: object, reducer: object) -> None:
        self.projection_reader = projection_reader
        self.reducer = reducer

    async def handle(self, envelope: object) -> None:
        return None


@pytest.mark.unit
def test_step_1_local_ownership_skip_when_not_owned_here() -> None:
    ownership = MagicMock()
    ownership.is_owned_here.return_value = False
    ctx = ModelHandlerResolverContext(
        handler_cls=_HandlerNoDeps,
        handler_module="x",
        handler_name="H",
        contract_name="node_foo",
        node_name="node_foo",
        ownership_query=ownership,
    )

    result = HandlerResolver().resolve(ctx)

    assert (
        result.outcome == EnumHandlerResolutionOutcome.RESOLVED_VIA_LOCAL_OWNERSHIP_SKIP
    )
    assert result.handler_instance is None
    assert result.skipped_handler == "H"
    assert "not hosted here" in result.skipped_reason
    ownership.is_owned_here.assert_called_once_with("node_foo")


@pytest.mark.unit
def test_step_1_local_ownership_owned_here_falls_through() -> None:
    """If ownership_query says owned, resolver proceeds to later steps."""
    ownership = MagicMock()
    ownership.is_owned_here.return_value = True
    ctx = ModelHandlerResolverContext(
        handler_cls=_HandlerNoDeps,
        handler_module="x",
        handler_name="H",
        contract_name="node_foo",
        node_name="node_foo",
        ownership_query=ownership,
    )

    result = HandlerResolver().resolve(ctx)

    assert result.outcome == EnumHandlerResolutionOutcome.RESOLVED_VIA_ZERO_ARG
    assert isinstance(result.handler_instance, _HandlerNoDeps)


@pytest.mark.unit
def test_step_1_duck_typed_ownership_query_without_method_ignored() -> None:
    """An ownership_query without is_owned_here is ignored (duck-typed)."""

    class _NotAnOwnershipQuery:
        # No `is_owned_here` attr at all.
        pass

    ctx = ModelHandlerResolverContext(
        handler_cls=_HandlerNoDeps,
        handler_module="x",
        handler_name="H",
        contract_name="node_foo",
        node_name="node_foo",
        ownership_query=_NotAnOwnershipQuery(),
    )

    # Should skip Step 1 and fall through to Step 5 (zero-arg).
    result = HandlerResolver().resolve(ctx)
    assert result.outcome == EnumHandlerResolutionOutcome.RESOLVED_VIA_ZERO_ARG


@pytest.mark.unit
def test_step_2_explicit_dep_map_wins_over_container() -> None:
    proj = object()
    reducer = object()
    container = MagicMock()
    container.get_service.return_value = _HandlerWithDeps(proj, reducer)
    ctx = ModelHandlerResolverContext(
        handler_cls=_HandlerWithDeps,
        handler_module="x",
        handler_name="H",
        contract_name="node_foo",
        node_name="node_foo",
        materialized_explicit_dependencies={
            "H": {"projection_reader": proj, "reducer": reducer},
        },
        container=container,
    )

    result = HandlerResolver().resolve(ctx)

    assert result.outcome == EnumHandlerResolutionOutcome.RESOLVED_VIA_NODE_REGISTRY
    assert isinstance(result.handler_instance, _HandlerWithDeps)
    container.get_service.assert_not_called()


@pytest.mark.unit
def test_step_3_container_used_when_no_explicit_deps() -> None:
    expected = _HandlerNoDeps()
    container = MagicMock()
    container.get_service.return_value = expected
    ctx = ModelHandlerResolverContext(
        handler_cls=_HandlerNoDeps,
        handler_module="x",
        handler_name="H",
        contract_name="node_foo",
        node_name="node_foo",
        container=container,
    )

    result = HandlerResolver().resolve(ctx)

    assert result.outcome == EnumHandlerResolutionOutcome.RESOLVED_VIA_CONTAINER
    assert result.handler_instance is expected
    container.get_service.assert_called_once_with(_HandlerNoDeps)


@pytest.mark.unit
def test_step_3_container_miss_falls_through_to_zero_arg() -> None:
    """Container raises ServiceResolutionError; resolver falls through to Step 5."""
    container = MagicMock()
    container.get_service.side_effect = ServiceResolutionError("not registered")
    ctx = ModelHandlerResolverContext(
        handler_cls=_HandlerNoDeps,
        handler_module="x",
        handler_name="H",
        contract_name="node_foo",
        node_name="node_foo",
        container=container,
    )

    result = HandlerResolver().resolve(ctx)

    assert result.outcome == EnumHandlerResolutionOutcome.RESOLVED_VIA_ZERO_ARG
    assert isinstance(result.handler_instance, _HandlerNoDeps)


@pytest.mark.unit
def test_step_3_container_internal_bug_propagates() -> None:
    """Non-miss exception from container (e.g. KeyError) must NOT be swallowed."""
    container = MagicMock()
    container.get_service.side_effect = KeyError("container corruption")
    ctx = ModelHandlerResolverContext(
        handler_cls=_HandlerNoDeps,
        handler_module="x",
        handler_name="H",
        contract_name="node_foo",
        node_name="node_foo",
        container=container,
    )

    with pytest.raises(KeyError):
        HandlerResolver().resolve(ctx)


@pytest.mark.unit
def test_step_3_container_without_get_service_skipped() -> None:
    """Container present but missing get_service attr — safely skipped."""

    class _NoGetServiceContainer:
        pass

    ctx = ModelHandlerResolverContext(
        handler_cls=_HandlerNoDeps,
        handler_module="x",
        handler_name="H",
        contract_name="node_foo",
        node_name="node_foo",
        container=_NoGetServiceContainer(),
    )

    # Should not raise AttributeError; falls through to zero-arg.
    result = HandlerResolver().resolve(ctx)
    assert result.outcome == EnumHandlerResolutionOutcome.RESOLVED_VIA_ZERO_ARG


@pytest.mark.unit
def test_step_4_event_bus_injection() -> None:
    event_bus = object()
    ctx = ModelHandlerResolverContext(
        handler_cls=_HandlerEventBusOnly,
        handler_module="x",
        handler_name="H",
        contract_name="node_foo",
        node_name="node_foo",
        event_bus=event_bus,
    )

    result = HandlerResolver().resolve(ctx)

    assert result.outcome == EnumHandlerResolutionOutcome.RESOLVED_VIA_EVENT_BUS
    assert isinstance(result.handler_instance, _HandlerEventBusOnly)
    assert result.handler_instance.event_bus is event_bus


@pytest.mark.unit
def test_step_5_zero_arg_construction() -> None:
    ctx = ModelHandlerResolverContext(
        handler_cls=_HandlerNoDeps,
        handler_module="x",
        handler_name="H",
        contract_name="node_foo",
        node_name="node_foo",
    )

    result = HandlerResolver().resolve(ctx)

    assert result.outcome == EnumHandlerResolutionOutcome.RESOLVED_VIA_ZERO_ARG
    assert isinstance(result.handler_instance, _HandlerNoDeps)


@pytest.mark.unit
def test_step_6_type_error_when_unresolvable() -> None:
    ctx = ModelHandlerResolverContext(
        handler_cls=_HandlerWithDeps,
        handler_module="x",
        # In production handler_name == class name; the TypeError message
        # surfaces handler_module.handler_name so the operator can find it.
        handler_name="_HandlerWithDeps",
        contract_name="node_foo",
        node_name="node_foo",
    )

    with pytest.raises(TypeError) as exc:
        HandlerResolver().resolve(ctx)

    msg = str(exc.value)
    assert "_HandlerWithDeps" in msg
    assert "projection_reader" in msg
    assert "reducer" in msg


@pytest.mark.unit
def test_explicit_dep_type_error_surfaces_missing_key() -> None:
    """Explicit materialized map incomplete -> resolver raises TypeError naming missing key."""
    proj = object()
    ctx = ModelHandlerResolverContext(
        handler_cls=_HandlerWithDeps,
        handler_module="x",
        handler_name="H",
        contract_name="node_foo",
        node_name="node_foo",
        # `reducer` missing intentionally.
        materialized_explicit_dependencies={"H": {"projection_reader": proj}},
    )

    with pytest.raises(TypeError) as exc:
        HandlerResolver().resolve(ctx)

    assert "reducer" in str(exc.value)


@pytest.mark.unit
def test_conflict_overlap_logs_debug(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Step 2 resolves but container also present -> DEBUG log names shadowed path."""
    proj = object()
    reducer = object()
    container = MagicMock()
    container.get_service.return_value = _HandlerWithDeps(proj, reducer)
    ctx = ModelHandlerResolverContext(
        handler_cls=_HandlerWithDeps,
        handler_module="x",
        handler_name="H",
        contract_name="node_foo",
        node_name="node_foo",
        materialized_explicit_dependencies={
            "H": {"projection_reader": proj, "reducer": reducer},
        },
        container=container,
    )

    with caplog.at_level(
        logging.DEBUG,
        logger="omnibase_core.services.service_handler_resolver",
    ):
        HandlerResolver().resolve(ctx)

    assert any(
        "shadowed" in rec.message.lower() or "overlap" in rec.message.lower()
        for rec in caplog.records
    )


@pytest.mark.unit
def test_resolver_is_pure_in_context() -> None:
    """Repeated resolve() calls with the same context yield the same outcome.

    Demonstrates the service holds no state that leaks across calls.
    """
    ctx = ModelHandlerResolverContext(
        handler_cls=_HandlerNoDeps,
        handler_module="x",
        handler_name="H",
        contract_name="node_foo",
        node_name="node_foo",
    )
    resolver = HandlerResolver()

    first = resolver.resolve(ctx)
    second = resolver.resolve(ctx)

    assert (
        first.outcome
        == second.outcome
        == (EnumHandlerResolutionOutcome.RESOLVED_VIA_ZERO_ARG)
    )
    # Different instances (each resolve() constructs a fresh handler).
    assert first.handler_instance is not second.handler_instance


@pytest.mark.unit
def test_skip_precedes_node_registry() -> None:
    """Ownership skip beats node_registry when not-owned-here."""
    ownership = MagicMock()
    ownership.is_owned_here.return_value = False
    proj: Any = object()
    reducer: Any = object()
    ctx = ModelHandlerResolverContext(
        handler_cls=_HandlerWithDeps,
        handler_module="x",
        handler_name="H",
        contract_name="node_foo",
        node_name="node_foo",
        ownership_query=ownership,
        materialized_explicit_dependencies={
            "H": {"projection_reader": proj, "reducer": reducer},
        },
    )

    result = HandlerResolver().resolve(ctx)

    assert (
        result.outcome == EnumHandlerResolutionOutcome.RESOLVED_VIA_LOCAL_OWNERSHIP_SKIP
    )
    assert result.handler_instance is None
