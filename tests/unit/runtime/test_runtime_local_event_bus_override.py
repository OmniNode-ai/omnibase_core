# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for RuntimeLocal backend_overrides['event_bus'] dispatch (OMN-9776).

Covers ``RuntimeLocal._create_event_bus`` selection logic:
- default (no override) returns ``EventBusInmemory``
- ``event_bus=kafka`` discovers the entry point under ``onex.backends`` and
  instantiates the registered class via its ``default()`` factory
- unsupported ``event_bus`` values are rejected up-front (no silent fallback,
  per CodeRabbit MAJOR finding on PR #919)
- missing entry point raises ``ModelOnexError`` (fail-fast, no silent fallback)
- ``kafka_bootstrap`` override is surfaced via ``KAFKA_BOOTSTRAP_SERVERS`` env
  for the duration of construction and restored afterward
- ``parse_backend_overrides`` accepts the ``kafka_bootstrap`` key
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.event_bus.event_bus_inmemory import EventBusInmemory
from omnibase_core.models.errors.model_onex_error import ModelOnexError
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
# parse_backend_overrides accepts kafka_bootstrap
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_known_backend_keys_includes_kafka_bootstrap() -> None:
    assert "kafka_bootstrap" in KNOWN_BACKEND_KEYS
    assert "event_bus" in KNOWN_BACKEND_KEYS


@pytest.mark.unit
def test_parse_backend_overrides_accepts_kafka_bootstrap() -> None:
    overrides = parse_backend_overrides(
        ("event_bus=kafka", "kafka_bootstrap=192.168.86.201:19092")
    )
    assert overrides == {
        "event_bus": "kafka",
        "kafka_bootstrap": "192.168.86.201:19092",
    }


@pytest.mark.unit
def test_parse_backend_overrides_rejects_unknown_key() -> None:
    with pytest.raises(ModelOnexError) as exc_info:
        parse_backend_overrides(("nonsense=value",))
    assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_INPUT


# ---------------------------------------------------------------------------
# Default behavior unchanged: in-memory bus
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


# ---------------------------------------------------------------------------
# Unsupported event_bus values are rejected (no silent fallback) — CR MAJOR
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_supported_event_bus_values_set() -> None:
    """Whitelist matches the documented contract."""
    assert frozenset({"inmemory", "kafka"}) == SUPPORTED_EVENT_BUS_VALUES


@pytest.mark.unit
@pytest.mark.parametrize(
    "bad_value",
    ["kafak", "redis", "rabbitmq", "Kafka", "KAFKA", "in-memory", "", " "],
)
def test_create_event_bus_rejects_unsupported_value(
    workflow_path: Path, bad_value: str
) -> None:
    """Typo or unsupported backend name fails fast — does NOT silently fall through to in-memory."""
    runtime = RuntimeLocal(
        workflow_path=workflow_path,
        backend_overrides={"event_bus": bad_value},
    )

    with pytest.raises(ModelOnexError) as exc_info:
        runtime._create_event_bus()

    assert exc_info.value.error_code == EnumCoreErrorCode.CONFIGURATION_ERROR
    # Error message must name the offending value AND list the supported set
    # so operators can fix the typo without grepping the source.
    assert repr(bad_value) in str(exc_info.value) or bad_value in str(exc_info.value)
    assert "inmemory" in str(exc_info.value)
    assert "kafka" in str(exc_info.value)


@pytest.mark.unit
def test_create_event_bus_rejection_does_not_invoke_kafka_path(
    workflow_path: Path,
) -> None:
    """Bad value must be caught BEFORE entry-point lookup runs."""
    runtime = RuntimeLocal(
        workflow_path=workflow_path,
        backend_overrides={"event_bus": "kafak"},  # typo for kafka
    )

    fake_eps = MagicMock()
    fake_eps.select = MagicMock(return_value=[])

    with patch(
        "omnibase_core.runtime.runtime_local.importlib.metadata.entry_points",
        return_value=fake_eps,
    ):
        with pytest.raises(ModelOnexError):
            runtime._create_event_bus()

    # If the rejection short-circuits correctly, entry-point lookup is never
    # invoked (proves the validation runs before the kafka dispatcher).
    fake_eps.select.assert_not_called()


# ---------------------------------------------------------------------------
# event_bus=kafka — entry-point dispatch
# ---------------------------------------------------------------------------


class _StubKafkaBus:
    """Stand-in for omnibase_infra.EventBusKafka for unit-test isolation."""

    def __init__(self) -> None:
        self.bootstrap_seen: str | None = os.environ.get("KAFKA_BOOTSTRAP_SERVERS")

    @classmethod
    def default(cls) -> _StubKafkaBus:
        return cls()


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
    """Entry point loads to a class without a ``default()`` factory."""

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
# kafka_bootstrap override surfaces via KAFKA_BOOTSTRAP_SERVERS env
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_kafka_bootstrap_override_sets_env_for_default_factory(
    workflow_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("KAFKA_BOOTSTRAP_SERVERS", raising=False)

    runtime = RuntimeLocal(
        workflow_path=workflow_path,
        backend_overrides={
            "event_bus": "kafka",
            "kafka_bootstrap": "192.168.86.201:19092",
        },
    )
    fake_eps = _stub_entry_points_with_kafka(_StubKafkaBus)

    with patch(
        "omnibase_core.runtime.runtime_local.importlib.metadata.entry_points",
        return_value=fake_eps,
    ):
        bus = runtime._create_event_bus()

    assert isinstance(bus, _StubKafkaBus)
    # _StubKafkaBus.__init__ snapshots os.environ during default() — proves the
    # override was set when the bus was constructed.
    assert bus.bootstrap_seen == "192.168.86.201:19092"
    # Restored afterward (was unset before the call).
    assert "KAFKA_BOOTSTRAP_SERVERS" not in os.environ


@pytest.mark.unit
def test_kafka_bootstrap_override_restores_prior_env_value(
    workflow_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "prior:9092")

    runtime = RuntimeLocal(
        workflow_path=workflow_path,
        backend_overrides={
            "event_bus": "kafka",
            "kafka_bootstrap": "override:19092",
        },
    )
    fake_eps = _stub_entry_points_with_kafka(_StubKafkaBus)

    with patch(
        "omnibase_core.runtime.runtime_local.importlib.metadata.entry_points",
        return_value=fake_eps,
    ):
        bus = runtime._create_event_bus()

    assert bus.bootstrap_seen == "override:19092"
    # Prior env value restored after construction.
    assert os.environ["KAFKA_BOOTSTRAP_SERVERS"] == "prior:9092"


@pytest.mark.unit
def test_kafka_default_path_does_not_touch_env(
    workflow_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No ``kafka_bootstrap`` override → env left exactly as-is."""
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "from-env:9092")

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

    assert bus.bootstrap_seen == "from-env:9092"
    assert os.environ["KAFKA_BOOTSTRAP_SERVERS"] == "from-env:9092"
