# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""T-C3: the container registers the authoritative override and honours a pin.

The registry under test is the real ``ServiceRegistry``; the backends are
fakes served through patched entry points, and the pin is passed as data.
"""

from __future__ import annotations

import ast
import asyncio
import itertools
from collections.abc import Sequence
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from omnibase_core.container import container_auto_config
from omnibase_core.container.container_auto_config import auto_configure_registry
from omnibase_core.container.container_service_registry import ServiceRegistry
from omnibase_core.enums.enum_backend_finding_reason import EnumBackendFindingReason
from omnibase_core.enums.enum_probe_state import EnumProbeState
from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
from omnibase_core.models.container.model_auto_config_result import (
    ModelAutoConfigResult,
)
from omnibase_core.models.container.model_probe_result import ModelProbeResult
from omnibase_core.models.container.model_registry_config import (
    create_default_registry_config,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.protocols.event_bus.protocol_event_bus import ProtocolEventBus
from omnibase_core.protocols.storage.protocol_state_store import ProtocolStateStore

_PROTOCOL = "ProtocolEventBus"


class _FakeLabBus:
    """Authoritative fake backend for the event bus."""

    @classmethod
    def probe(cls) -> ModelProbeResult:
        return ModelProbeResult(
            state=EnumProbeState.AUTHORITATIVE,
            protocol_name=_PROTOCOL,
            backend_name="lab",
            package="fake_pkg",
        )


class _FakeCloudBus:
    """Second authoritative fake backend for the event bus."""

    @classmethod
    def probe(cls) -> ModelProbeResult:
        return ModelProbeResult(
            state=EnumProbeState.AUTHORITATIVE,
            protocol_name=_PROTOCOL,
            backend_name="cloud",
            package="fake_pkg",
        )


class _FakeReachableBus:
    """Reachable but not authoritative fake backend."""

    @classmethod
    def probe(cls) -> ModelProbeResult:
        return ModelProbeResult(
            state=EnumProbeState.REACHABLE,
            protocol_name=_PROTOCOL,
            backend_name="reachable",
            package="fake_pkg",
        )


class _FakeStateBackend:
    """Authoritative fake backend for the state store."""

    @classmethod
    def probe(cls) -> ModelProbeResult:
        return ModelProbeResult(
            state=EnumProbeState.AUTHORITATIVE,
            protocol_name="ProtocolStateStore",
            backend_name="pg",
            package="fake_pkg",
        )


class _NoProbeBackend:
    """Entry point class with no probe()."""


class _RaisingProbeBackend:
    @classmethod
    def probe(cls) -> ModelProbeResult:
        raise OSError("connection refused")


def _entry_point(name: str, backend: object) -> MagicMock:
    ep = MagicMock()
    ep.name = name
    ep.value = f"fake_pkg:{name}"
    ep.load.return_value = backend
    return ep


def _container() -> SimpleNamespace:
    return SimpleNamespace(
        service_registry=ServiceRegistry(create_default_registry_config())
    )


def _configure(
    entry_points: Sequence[MagicMock],
    tmp_path: Path,
    pins: dict[str, str] | None = None,
) -> tuple[SimpleNamespace, ModelAutoConfigResult]:
    container = _container()
    with patch(
        "omnibase_core.container.container_auto_config.importlib.metadata.entry_points",
        return_value=SimpleNamespace(select=lambda group: list(entry_points)),
    ):
        result = asyncio.run(
            auto_configure_registry(container, state_root=tmp_path, pins=pins)
        )
    return container, result


def _resolve(container: SimpleNamespace, interface: type) -> object:
    return asyncio.run(container.service_registry.resolve_service(interface))


@pytest.mark.unit
def test_authoritative_backend_replaces_local_default(tmp_path: Path) -> None:
    """AC1: an authoritative fake backend is served after the call."""
    container, result = _configure([_entry_point("lab", _FakeLabBus)], tmp_path)

    served = _resolve(container, ProtocolEventBus)

    assert isinstance(served, _FakeLabBus)
    assert not isinstance(served, EventBusInmemory)
    assert result.overrides == {_PROTOCOL: "lab"}


@pytest.mark.unit
def test_override_leaves_other_protocols_on_local_default(tmp_path: Path) -> None:
    container, _ = _configure([_entry_point("lab", _FakeLabBus)], tmp_path)

    assert not isinstance(_resolve(container, ProtocolStateStore), _FakeLabBus)


@pytest.mark.unit
def test_no_entry_points_serves_local_defaults(tmp_path: Path) -> None:
    container, result = _configure([], tmp_path)

    assert isinstance(_resolve(container, ProtocolEventBus), EventBusInmemory)
    assert result.overrides == {}
    assert result.findings == ()


@pytest.mark.unit
def test_pin_to_local_default_ignores_authoritative_backend(tmp_path: Path) -> None:
    """AC2: a pin to the local default keeps it despite a reachable lab backend."""
    container, result = _configure(
        [_entry_point("lab", _FakeLabBus)],
        tmp_path,
        pins={_PROTOCOL: "inmemory"},
    )

    assert isinstance(_resolve(container, ProtocolEventBus), EventBusInmemory)
    assert result.overrides == {}


@pytest.mark.unit
def test_pin_selects_one_of_two_authoritative_backends(tmp_path: Path) -> None:
    """A pin removes the ambiguity that raises without one."""
    container, _ = _configure(
        [_entry_point("lab", _FakeLabBus), _entry_point("cloud", _FakeCloudBus)],
        tmp_path,
        pins={_PROTOCOL: "cloud"},
    )

    assert isinstance(_resolve(container, ProtocolEventBus), _FakeCloudBus)


@pytest.mark.unit
def test_two_authoritative_backends_without_pin_still_refuse(tmp_path: Path) -> None:
    with pytest.raises(ModelOnexError, match="Multiple authoritative backends"):
        _configure(
            [_entry_point("lab", _FakeLabBus), _entry_point("cloud", _FakeCloudBus)],
            tmp_path,
        )


@pytest.mark.unit
def test_pin_naming_absent_backend_refuses_naming_protocol_and_backend(
    tmp_path: Path,
) -> None:
    """AC3 (absent): the refusal names the protocol and the backend."""
    with pytest.raises(ModelOnexError) as excinfo:
        _configure(
            [_entry_point("lab", _FakeLabBus)],
            tmp_path,
            pins={_PROTOCOL: "missing"},
        )

    assert _PROTOCOL in excinfo.value.message
    assert "missing" in excinfo.value.message


@pytest.mark.unit
def test_pin_naming_non_authoritative_backend_refuses(tmp_path: Path) -> None:
    """AC3 (non-authoritative): the refusal names the protocol and the backend."""
    with pytest.raises(ModelOnexError) as excinfo:
        _configure(
            [_entry_point("reachable", _FakeReachableBus)],
            tmp_path,
            pins={_PROTOCOL: "reachable"},
        )

    assert _PROTOCOL in excinfo.value.message
    assert "reachable" in excinfo.value.message


@pytest.mark.unit
def test_pin_for_unknown_protocol_refuses(tmp_path: Path) -> None:
    with pytest.raises(ModelOnexError, match="ProtocolNoSuch"):
        _configure([], tmp_path, pins={"ProtocolNoSuch": "x"})


class _FakeUnknownProtocolBackend:
    @classmethod
    def probe(cls) -> ModelProbeResult:
        return ModelProbeResult(
            state=EnumProbeState.AUTHORITATIVE,
            protocol_name="ProtocolNoLocalDefault",
            backend_name="odd",
            package="fake_pkg",
        )


@pytest.mark.unit
def test_unknown_protocol_backend_is_a_finding_unless_pinned(tmp_path: Path) -> None:
    ep = _entry_point("odd", _FakeUnknownProtocolBackend)

    _, result = _configure([ep], tmp_path)
    reasons = [f.reason for f in result.findings]
    assert reasons == [EnumBackendFindingReason.UNKNOWN_PROTOCOL]

    with pytest.raises(ModelOnexError, match="ProtocolNoLocalDefault"):
        _configure([ep], tmp_path, pins={"ProtocolNoLocalDefault": "odd"})


@pytest.mark.unit
def test_skipped_entry_points_are_returned_as_findings(tmp_path: Path) -> None:
    """AC4: a backend without probe() and a probe that raised are findings."""
    broken_load = MagicMock()
    broken_load.name = "broken"
    broken_load.value = "fake_pkg:broken"
    broken_load.load.side_effect = ImportError("no module")

    _, result = _configure(
        [
            _entry_point("noprobe", _NoProbeBackend),
            _entry_point("raiser", _RaisingProbeBackend),
            broken_load,
            _entry_point("lab", _FakeLabBus),
        ],
        tmp_path,
    )

    by_name = {f.entry_point: f for f in result.findings}
    assert set(by_name) == {"noprobe", "raiser", "broken"}
    assert by_name["noprobe"].reason is EnumBackendFindingReason.NO_PROBE
    assert by_name["raiser"].reason is EnumBackendFindingReason.PROBE_RAISED
    assert "connection refused" in by_name["raiser"].detail
    assert by_name["broken"].reason is EnumBackendFindingReason.LOAD_FAILED
    assert by_name["noprobe"].value == "fake_pkg:noprobe"


@pytest.mark.unit
def test_uninstantiable_authoritative_backend_is_a_finding(tmp_path: Path) -> None:
    class NeedsArgs(_FakeLabBus):
        def __init__(self, required: str) -> None:
            self.required = required

    container, result = _configure([_entry_point("lab", NeedsArgs)], tmp_path)

    assert isinstance(_resolve(container, ProtocolEventBus), EventBusInmemory)
    reasons = [f.reason for f in result.findings]
    assert reasons == [EnumBackendFindingReason.NOT_INSTANTIABLE]


@pytest.mark.unit
def test_pinned_uninstantiable_backend_refuses(tmp_path: Path) -> None:
    class NeedsArgs(_FakeLabBus):
        def __init__(self, required: str) -> None:
            self.required = required

    with pytest.raises(ModelOnexError, match="lab"):
        _configure([_entry_point("lab", NeedsArgs)], tmp_path, pins={_PROTOCOL: "lab"})


@pytest.mark.unit
@pytest.mark.parametrize("pins", [None, {_PROTOCOL: "lab"}, {_PROTOCOL: "inmemory"}])
def test_resolution_is_independent_of_entry_point_order(
    tmp_path: Path, pins: dict[str, str] | None
) -> None:
    """Bindings: the same registrations in any order give the same resolution."""
    eps = [
        ("lab", _FakeLabBus),
        ("state", _FakeStateBackend),
        ("noprobe", _NoProbeBackend),
    ]
    seen: set[tuple[str, str]] = set()
    for ordering in itertools.permutations(eps):
        container, _ = _configure(
            [_entry_point(name, cls) for name, cls in ordering], tmp_path, pins=pins
        )
        seen.add(
            (
                type(_resolve(container, ProtocolEventBus)).__name__,
                type(_resolve(container, ProtocolStateStore)).__name__,
            )
        )

    assert len(seen) == 1


@pytest.mark.unit
def test_module_reads_no_environment_variable() -> None:
    """Configuration: the pin is an argument; the module reads no environment."""
    source = Path(container_auto_config.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    names |= {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}

    assert not names & {"environ", "getenv", "putenv"}
