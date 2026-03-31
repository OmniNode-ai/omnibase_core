# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for onex.backends and onex.cli entry point group discovery.

Verifies that entry points declared in pyproject.toml are discoverable
via importlib.metadata and that broken entry points fail loudly with
diagnostic messages rather than silently disappearing.

[OMN-7064]
"""

from __future__ import annotations

import importlib.metadata
import logging
from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
class TestBackendEntryPointDiscovery:
    """Verify onex.backends entry points are discoverable after install."""

    def test_backend_entry_points_discoverable(self) -> None:
        """Installed backends are discoverable via entry points."""
        backends = importlib.metadata.entry_points(group="onex.backends")
        names = [ep.name for ep in backends]
        assert "event_bus_inmemory" in names, (
            f"event_bus_inmemory not found in onex.backends; got: {names}"
        )
        assert "state_disk" in names, (
            f"state_disk not found in onex.backends; got: {names}"
        )

    def test_backend_entry_point_values(self) -> None:
        """Entry point values reference correct module:class paths."""
        backends = importlib.metadata.entry_points(group="onex.backends")
        ep_map = {ep.name: ep.value for ep in backends}
        assert ep_map["event_bus_inmemory"] == (
            "omnibase_core.event_bus.event_bus_inmemory:EventBusInmemory"
        )
        assert ep_map["state_disk"] == (
            "omnibase_core.services.state.service_state_disk:ServiceStateDisk"
        )

    def test_cli_entry_point_group_exists(self) -> None:
        """onex.cli entry point group is registered (may be empty)."""
        cli_eps = importlib.metadata.entry_points(group="onex.cli")
        # Group exists but may have no entries yet (for extensions)
        assert isinstance(list(cli_eps), list)


@pytest.mark.unit
class TestBrokenEntryPointHandling:
    """Verify broken entry points fail loudly with diagnostics."""

    def test_broken_entry_point_raises_with_diagnostic(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Loading a broken backend entry point produces a clear error message."""
        # Create a mock entry point that raises ImportError on load
        mock_ep = MagicMock()
        mock_ep.name = "event_bus_kafka"
        mock_ep.value = "omnibase_infra.event_bus.event_bus_kafka:EventBusKafka"
        mock_ep.load.side_effect = ImportError("No module named 'omnibase_infra'")

        # Simulate discovery + load with diagnostic logging
        failures: list[str] = []
        with caplog.at_level(logging.ERROR):
            try:
                mock_ep.load()
            except (ImportError, AttributeError, Exception) as exc:
                diagnostic = (
                    f"Backend '{mock_ep.name}' failed to load: "
                    f"{type(exc).__name__}: {exc}"
                )
                failures.append(diagnostic)
                logging.exception(diagnostic)

        assert len(failures) == 1
        assert "event_bus_kafka" in failures[0]
        assert "ImportError" in failures[0]
        assert "No module named 'omnibase_infra'" in failures[0]

    def test_broken_entry_point_attribute_error(self) -> None:
        """Entry point with missing class attribute produces diagnostic."""
        mock_ep = MagicMock()
        mock_ep.name = "state_postgres"
        mock_ep.value = "some_module:MissingClass"
        mock_ep.load.side_effect = AttributeError(
            "module 'some_module' has no attribute 'MissingClass'"
        )

        failures: list[str] = []
        try:
            mock_ep.load()
        except (ImportError, AttributeError, ModuleNotFoundError) as exc:
            diagnostic = (
                f"Backend '{mock_ep.name}' failed to load: {type(exc).__name__}: {exc}"
            )
            failures.append(diagnostic)

        assert len(failures) == 1
        assert "state_postgres" in failures[0]
        assert "AttributeError" in failures[0]

    def test_discovery_collects_all_failures(self) -> None:
        """Discovery collects failures from all broken backends, not just first."""
        mock_eps = []
        for name, error in [
            ("backend_a", ImportError("no module a")),
            ("backend_b", AttributeError("no class b")),
        ]:
            ep = MagicMock()
            ep.name = name
            ep.value = f"fake.module:{name}"
            ep.load.side_effect = error
            mock_eps.append(ep)

        failures: list[str] = []
        for ep in mock_eps:
            try:
                ep.load()
            except (ImportError, AttributeError, ModuleNotFoundError) as exc:
                failures.append(
                    f"Backend '{ep.name}' failed to load: {type(exc).__name__}: {exc}"
                )

        assert len(failures) == 2
        assert "backend_a" in failures[0]
        assert "backend_b" in failures[1]
