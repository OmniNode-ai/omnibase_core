# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the ``onex registry status`` CLI command."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from omnibase_core.cli.cli_commands import cli

pytestmark = pytest.mark.unit


class TestRegistryStatus:
    """Tests for ``onex registry status``."""

    def test_exit_code_zero(self) -> None:
        """Command exits successfully."""
        runner = CliRunner()
        result = runner.invoke(cli, ["registry", "status"])
        assert result.exit_code == 0, result.output

    def test_shows_event_bus_backend(self) -> None:
        """Output contains an EventBus line with provenance."""
        runner = CliRunner()
        result = runner.invoke(cli, ["registry", "status"])
        assert "EventBus:" in result.output
        assert "source: default" in result.output
        assert "package: omnibase_core" in result.output

    def test_shows_state_store_backend(self) -> None:
        """Output contains a StateStore line."""
        runner = CliRunner()
        result = runner.invoke(cli, ["registry", "status"])
        assert "StateStore:" in result.output

    def test_shows_discovered_node_count(self) -> None:
        """Output contains a Nodes line with a count."""
        runner = CliRunner()
        result = runner.invoke(cli, ["registry", "status"])
        assert "Nodes:" in result.output
        assert "discovered" in result.output

    def test_shows_backend_count(self) -> None:
        """Output contains a Backends line referencing the entry-point group."""
        runner = CliRunner()
        result = runner.invoke(cli, ["registry", "status"])
        assert "Backends:" in result.output
        assert "onex.backends" in result.output

    def test_shows_cli_extension_count(self) -> None:
        """Output contains a CLI line referencing the entry-point group."""
        runner = CliRunner()
        result = runner.invoke(cli, ["registry", "status"])
        assert "CLI:" in result.output
        assert "onex.cli" in result.output

    def test_registry_group_help(self) -> None:
        """``onex registry --help`` shows the group help text."""
        runner = CliRunner()
        result = runner.invoke(cli, ["registry", "--help"])
        assert result.exit_code == 0
        assert "registry" in result.output.lower()
