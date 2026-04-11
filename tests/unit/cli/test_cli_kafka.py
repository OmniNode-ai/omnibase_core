# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for onex.cli dynamic extension loading (OMN-8435).

Tests that cli_commands.py correctly loads click Groups registered via the
onex.cli entry-point group. The kafka produce subcommand implementation lives
in omnibase_infra; these tests verify the loading contract only.
"""

from __future__ import annotations

from importlib.metadata import EntryPoint
from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner

pytestmark = pytest.mark.unit


class TestOnexCliExtensionLoading:
    """Tests for dynamic onex.cli entry-point extension loading."""

    def test_extension_group_is_added_to_cli(self) -> None:
        mock_group = click.Group("testpkg", help="Test extension group")
        mock_ep: MagicMock = MagicMock(spec=EntryPoint)
        mock_ep.name = "testpkg"
        mock_ep.load.return_value = mock_group

        with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
            # Reload the cli with the patched entry points
            import importlib

            import omnibase_core.cli.cli_commands as mod

            importlib.reload(mod)
            reloaded_cli = mod.cli

        runner = CliRunner()
        result = runner.invoke(reloaded_cli, ["--help"])
        assert result.exit_code == 0
        assert "testpkg" in result.output

    def test_broken_extension_does_not_crash_cli(self) -> None:
        mock_ep: MagicMock = MagicMock(spec=EntryPoint)
        mock_ep.name = "broken"
        mock_ep.load.side_effect = ImportError("simulated failure")

        with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
            import importlib

            import omnibase_core.cli.cli_commands as mod

            importlib.reload(mod)
            reloaded_cli = mod.cli

        runner = CliRunner()
        result = runner.invoke(reloaded_cli, ["--help"])
        assert result.exit_code == 0

    def test_non_basecommand_extension_is_rejected(self) -> None:
        """Non-click.BaseCommand callables (e.g. malicious functions) are rejected."""
        mock_ep: MagicMock = MagicMock(spec=EntryPoint)
        mock_ep.name = "malicious"

        def _malicious_callable() -> None:
            pass  # A callable but NOT a click.BaseCommand

        mock_ep.load.return_value = _malicious_callable

        with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
            import importlib

            import omnibase_core.cli.cli_commands as mod

            importlib.reload(mod)
            reloaded_cli = mod.cli

        runner = CliRunner()
        result = runner.invoke(reloaded_cli, ["--help"])
        assert result.exit_code == 0
        assert "malicious" not in result.output

    def test_non_callable_extension_is_skipped(self) -> None:
        mock_ep: MagicMock = MagicMock(spec=EntryPoint)
        mock_ep.name = "notcallable"
        mock_ep.load.return_value = "not a click command"

        with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
            import importlib

            import omnibase_core.cli.cli_commands as mod

            importlib.reload(mod)
            reloaded_cli = mod.cli

        runner = CliRunner()
        result = runner.invoke(reloaded_cli, ["--help"])
        assert result.exit_code == 0
        assert "notcallable" not in result.output

    def test_cli_help_still_works_with_no_extensions(self) -> None:
        with patch("importlib.metadata.entry_points", return_value=[]):
            import importlib

            import omnibase_core.cli.cli_commands as mod

            importlib.reload(mod)
            reloaded_cli = mod.cli

        runner = CliRunner()
        result = runner.invoke(reloaded_cli, ["--help"])
        assert result.exit_code == 0
        assert "onex" in result.output.lower() or "cli" in result.output.lower()

    def test_duplicate_extension_name_does_not_overwrite_builtin(self) -> None:
        """An entry-point whose name collides with an existing built-in command must
        be skipped, not silently overwrite the built-in."""
        import importlib

        import omnibase_core.cli.cli_commands as mod

        importlib.reload(mod)
        # Pick any command already registered in the CLI after a clean reload.
        existing_name = next(iter(mod.cli.commands))
        _original_cmd = mod.cli.commands[existing_name]

        hijack_group = click.Group(existing_name, help="Hijack attempt")
        mock_ep: MagicMock = MagicMock(spec=EntryPoint)
        mock_ep.name = existing_name
        mock_ep.load.return_value = hijack_group

        with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
            importlib.reload(mod)
            reloaded_cli = mod.cli

        # The built-in must not be replaced by the extension.
        assert reloaded_cli.commands.get(existing_name) is not hijack_group

        runner = CliRunner()
        result = runner.invoke(reloaded_cli, ["--help"])
        assert result.exit_code == 0
