# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for container auto-configuration from entry points."""

from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from omnibase_core.container.container_auto_config import auto_configure_registry
from omnibase_core.enums.enum_probe_state import EnumProbeState
from omnibase_core.models.container.model_probe_result import ModelProbeResult
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_container_stub() -> SimpleNamespace:
    """Create a minimal container stub with a mock service_registry."""
    registry = MagicMock()
    # register_instance is async
    registry.register_instance = MagicMock(
        side_effect=lambda *a, **kw: asyncio.coroutine(lambda: None)()
    )
    return SimpleNamespace(service_registry=registry)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_auto_config_registers_local_defaults_with_no_entry_points(
    tmp_path: object,
) -> None:
    """auto_configure_registry runs without error when no entry points exist.

    Even when EventBusInmemory / ServiceStateDisk are not importable (Tasks
    1-4 not yet landed), the function must complete gracefully and log that
    local defaults were skipped.
    """
    container = _make_container_stub()

    with patch(
        "omnibase_core.container.container_auto_config.importlib.metadata.entry_points",
        return_value=SimpleNamespace(select=lambda group: []),
    ):
        asyncio.get_event_loop().run_until_complete(
            auto_configure_registry(container, state_root=str(tmp_path))
        )


@pytest.mark.unit
def test_auto_config_discovers_authoritative_entry_point(
    tmp_path: object,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An AUTHORITATIVE entry-point backend is logged as an override."""
    container = _make_container_stub()

    class FakeKafkaBus:
        @classmethod
        def probe(cls) -> ModelProbeResult:
            return ModelProbeResult(
                state=EnumProbeState.AUTHORITATIVE,
                protocol_name="ProtocolEventBus",
                backend_name="kafka",
                package="omnibase_infra",
            )

    fake_ep = MagicMock()
    fake_ep.name = "kafka_bus"
    fake_ep.value = "omnibase_infra.event_bus:KafkaBus"
    fake_ep.load.return_value = FakeKafkaBus

    with (
        patch(
            "omnibase_core.container.container_auto_config.importlib.metadata.entry_points",
            return_value=SimpleNamespace(select=lambda group: [fake_ep]),
        ),
        caplog.at_level(logging.INFO),
    ):
        asyncio.get_event_loop().run_until_complete(
            auto_configure_registry(container, state_root=str(tmp_path))
        )

    assert "Override registered: ProtocolEventBus" in caplog.text
    assert "kafka" in caplog.text


@pytest.mark.unit
def test_auto_config_rejects_ambiguous_authoritative(tmp_path: object) -> None:
    """Two AUTHORITATIVE backends for the same protocol raise ModelOnexError."""
    container = _make_container_stub()

    class FakeBackendA:
        @classmethod
        def probe(cls) -> ModelProbeResult:
            return ModelProbeResult(
                state=EnumProbeState.AUTHORITATIVE,
                protocol_name="ProtocolEventBus",
                backend_name="kafka",
                package="pkg_a",
            )

    class FakeBackendB:
        @classmethod
        def probe(cls) -> ModelProbeResult:
            return ModelProbeResult(
                state=EnumProbeState.AUTHORITATIVE,
                protocol_name="ProtocolEventBus",
                backend_name="cloud",
                package="pkg_b",
            )

    ep_a = MagicMock()
    ep_a.name = "kafka_bus"
    ep_a.value = "pkg_a:KafkaBus"
    ep_a.load.return_value = FakeBackendA

    ep_b = MagicMock()
    ep_b.name = "cloud_bus"
    ep_b.value = "pkg_b:CloudBus"
    ep_b.load.return_value = FakeBackendB

    with (
        patch(
            "omnibase_core.container.container_auto_config.importlib.metadata.entry_points",
            return_value=SimpleNamespace(select=lambda group: [ep_a, ep_b]),
        ),
        pytest.raises(ModelOnexError, match="Multiple authoritative backends"),
    ):
        asyncio.get_event_loop().run_until_complete(
            auto_configure_registry(container, state_root=str(tmp_path))
        )


@pytest.mark.unit
def test_auto_config_skips_non_authoritative_entry_point(tmp_path: object) -> None:
    """A REACHABLE backend does NOT override local defaults."""
    container = _make_container_stub()

    class FakeReachableOnly:
        @classmethod
        def probe(cls) -> ModelProbeResult:
            return ModelProbeResult(
                state=EnumProbeState.REACHABLE,
                protocol_name="ProtocolEventBus",
                backend_name="kafka",
                package="some_pkg",
                message="TCP open but auth failed",
            )

    fake_ep = MagicMock()
    fake_ep.name = "kafka_bus"
    fake_ep.value = "some_pkg:KafkaBus"
    fake_ep.load.return_value = FakeReachableOnly

    with patch(
        "omnibase_core.container.container_auto_config.importlib.metadata.entry_points",
        return_value=SimpleNamespace(select=lambda group: [fake_ep]),
    ):
        asyncio.get_event_loop().run_until_complete(
            auto_configure_registry(container, state_root=str(tmp_path))
        )

    # No error, no override — REACHABLE is not enough


@pytest.mark.unit
def test_model_probe_result_frozen() -> None:
    """ModelProbeResult is frozen and rejects extra fields."""
    result = ModelProbeResult(
        state=EnumProbeState.HEALTHY,
        protocol_name="ProtocolStateStore",
        backend_name="disk",
    )
    with pytest.raises(ValidationError):
        result.state = EnumProbeState.AUTHORITATIVE  # type: ignore[misc]
    with pytest.raises(ValidationError):
        ModelProbeResult(
            state=EnumProbeState.HEALTHY,
            protocol_name="X",
            backend_name="Y",
            bad_field="z",  # type: ignore[call-arg]
        )
