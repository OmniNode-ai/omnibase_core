# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for onex.cli dynamic extension loading (OMN-8435).

Tests that cli_commands.py correctly loads click Groups registered via the
onex.cli entry-point group. The kafka produce subcommand implementation lives
in omnibase_infra; these tests verify the loading contract only.

Scope note (OMN-16967). What remains here is the HEALTHY path, asserted the way
this file always has: patch ``entry_points`` and reload the module. The four
malformed-registration cases that used to live here asserted the loader would
log-and-skip — a broken target, a non-callable target, a non-click callable, and
a name colliding with a built-in. That contract is inverted: those shapes now
raise at import time, and the replacement cases live in
``test_cli_extension_loader_fail_loud_omn16967.py``, which drives
``load_cli_extensions`` with injected entry points instead of reloading the
module. That is why they moved rather than being edited in place: reload runs
the module-scope ``load_cli_extensions`` call, so under the new contract a test
for a malformed registration cannot get far enough to make an assertion.
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
