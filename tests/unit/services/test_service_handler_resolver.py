# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ServiceHandlerResolver (OMN-9199 Task 3).

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
from typing import Any, Protocol, runtime_checkable
from unittest.mock import MagicMock

import pytest

from omnibase_core.enums.enum_handler_resolution_outcome import (
    EnumHandlerResolutionOutcome,
)
from omnibase_core.errors.error_service_resolution import ServiceResolutionError
from omnibase_core.models.resolver.model_handler_resolver_context import (
    ModelHandlerResolverContext,
)
from omnibase_core.services.service_handler_resolver import ServiceHandlerResolver


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


class _ProtocolHandler(Protocol):
    """A typing.Protocol used as a (mis-declared) handler routing target.

    Mirrors the real-world OMN-12961 defect: a contract's handler_routing
    points at an interface Protocol (e.g. EvidenceEvaluator) rather than a
    concrete implementation. Protocol's synthetic
    `__init__(*args, **kwargs)` exposes only VAR_POSITIONAL/VAR_KEYWORD
    params, so the resolver's required-param scan sees zero required
    params and (pre-fix) attempts a zero-arg instantiation that dies inside
    typing internals with the anonymous "Protocols cannot be instantiated".
    """

    async def handle(self, envelope: object) -> None: ...


@runtime_checkable
class _RuntimeCheckableProtocolHandler(Protocol):
    """A runtime_checkable Protocol handler target.

    Same defect class as `_ProtocolHandler`; included to prove the guard
    keys off `_is_protocol` (set by typing for any Protocol subclass)
    rather than any runtime_checkable-specific marker.
    """

    async def handle(self, envelope: object) -> None: ...


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

    result = ServiceHandlerResolver().resolve(ctx)

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

    result = ServiceHandlerResolver().resolve(ctx)

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
    result = ServiceHandlerResolver().resolve(ctx)
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

    result = ServiceHandlerResolver().resolve(ctx)

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

    result = ServiceHandlerResolver().resolve(ctx)

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

    result = ServiceHandlerResolver().resolve(ctx)

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
        ServiceHandlerResolver().resolve(ctx)


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
    result = ServiceHandlerResolver().resolve(ctx)
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

    result = ServiceHandlerResolver().resolve(ctx)

    # OMN-10278: RESOLVED_VIA_KNOWN_PARAMS subsumes RESOLVED_VIA_EVENT_BUS.
    assert result.outcome == EnumHandlerResolutionOutcome.RESOLVED_VIA_KNOWN_PARAMS
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

    result = ServiceHandlerResolver().resolve(ctx)

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
        ServiceHandlerResolver().resolve(ctx)

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
        ServiceHandlerResolver().resolve(ctx)

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
        ServiceHandlerResolver().resolve(ctx)

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
    resolver = ServiceHandlerResolver()

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

    result = ServiceHandlerResolver().resolve(ctx)

    assert (
        result.outcome == EnumHandlerResolutionOutcome.RESOLVED_VIA_LOCAL_OWNERSHIP_SKIP
    )
    assert result.handler_instance is None


# ---------------------------------------------------------------------------
# OMN-12961 — Protocol handler rejection.
#
# A typing.Protocol used as a handler_routing target is non-instantiable by
# design. Pre-fix, the resolver's required-param scan treated Protocol's
# synthetic `__init__(*args, **kwargs)` as zero-arg and called `handler_cls()`,
# letting typing's anonymous `TypeError("Protocols cannot be instantiated")`
# escape from typing.py — taking down runtime bootstrap with no attribution to
# the offending contract/handler. The resolver must fail fast BEFORE any
# instantiation path with an identifying TypeError naming the handler and its
# contract, so the infra OMN-12501 quarantine guard (and any other caller) gets
# an attributable error instead of typing's anonymous one.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_protocol_handler_rejected_with_identifying_type_error() -> None:
    """Protocol handler_cls raises a TypeError naming handler + contract."""
    ctx = ModelHandlerResolverContext(
        handler_cls=_ProtocolHandler,
        handler_module="omnimarket.nodes.node_overseer_observer.handlers",
        handler_name="_ProtocolHandler",
        contract_name="node_overseer_observer",
        node_name="node_overseer_observer",
    )

    with pytest.raises(TypeError) as exc:
        ServiceHandlerResolver().resolve(ctx)

    msg = str(exc.value)
    # Attributable: names the handler module.name and the owning contract.
    assert "_ProtocolHandler" in msg
    assert "omnimarket.nodes.node_overseer_observer.handlers" in msg
    assert "node_overseer_observer" in msg
    assert "Protocol" in msg
    # NOT typing's anonymous internal message.
    assert msg != "Protocols cannot be instantiated"


@pytest.mark.unit
def test_runtime_checkable_protocol_handler_rejected() -> None:
    """A runtime_checkable Protocol handler is rejected the same way."""
    ctx = ModelHandlerResolverContext(
        handler_cls=_RuntimeCheckableProtocolHandler,
        handler_module="x",
        handler_name="_RuntimeCheckableProtocolHandler",
        contract_name="node_foo",
        node_name="node_foo",
    )

    with pytest.raises(TypeError) as exc:
        ServiceHandlerResolver().resolve(ctx)

    assert "_RuntimeCheckableProtocolHandler" in str(exc.value)
    assert "Protocol" in str(exc.value)


@pytest.mark.unit
def test_protocol_handler_rejected_even_with_container_present() -> None:
    """Protocol rejection precedes container DI — the container is never probed."""
    container = MagicMock()
    ctx = ModelHandlerResolverContext(
        handler_cls=_ProtocolHandler,
        handler_module="x",
        handler_name="_ProtocolHandler",
        contract_name="node_foo",
        node_name="node_foo",
        container=container,
    )

    with pytest.raises(TypeError) as exc:
        ServiceHandlerResolver().resolve(ctx)

    assert "Protocol" in str(exc.value)
    # Guard runs before Step 3; the container must never be consulted for a
    # non-instantiable Protocol target.
    container.get_service.assert_not_called()


@pytest.mark.unit
def test_protocol_handler_rejected_even_with_event_bus_present() -> None:
    """Protocol rejection precedes known-param injection (Step 4)."""
    ctx = ModelHandlerResolverContext(
        handler_cls=_ProtocolHandler,
        handler_module="x",
        handler_name="_ProtocolHandler",
        contract_name="node_foo",
        node_name="node_foo",
        event_bus=object(),
    )

    with pytest.raises(TypeError) as exc:
        ServiceHandlerResolver().resolve(ctx)

    assert "Protocol" in str(exc.value)


@pytest.mark.unit
def test_protocol_handler_rejected_when_owned_here() -> None:
    """When ownership says owned-here, the Protocol handler is rejected."""
    ownership = MagicMock()
    ownership.is_owned_here.return_value = True
    ctx = ModelHandlerResolverContext(
        handler_cls=_ProtocolHandler,
        handler_module="x",
        handler_name="_ProtocolHandler",
        contract_name="node_foo",
        node_name="node_foo",
        ownership_query=ownership,
    )

    with pytest.raises(TypeError) as exc:
        ServiceHandlerResolver().resolve(ctx)

    assert "Protocol" in str(exc.value)


@pytest.mark.unit
def test_protocol_handler_not_owned_here_still_skips_cleanly() -> None:
    """Protocol rejection must NOT fire for a node not hosted here.

    Ownership skip (Step 1) is a deliberate non-error path; a Protocol-typed
    handler on a node this runtime does not host must skip cleanly rather than
    raise, mirroring infra: only handlers this runtime would actually wire are
    rejected/quarantined.
    """
    ownership = MagicMock()
    ownership.is_owned_here.return_value = False
    ctx = ModelHandlerResolverContext(
        handler_cls=_ProtocolHandler,
        handler_module="x",
        handler_name="_ProtocolHandler",
        contract_name="node_foo",
        node_name="node_foo",
        ownership_query=ownership,
    )

    result = ServiceHandlerResolver().resolve(ctx)

    assert (
        result.outcome == EnumHandlerResolutionOutcome.RESOLVED_VIA_LOCAL_OWNERSHIP_SKIP
    )
    assert result.handler_instance is None
