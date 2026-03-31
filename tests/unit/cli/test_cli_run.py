# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ``onex run`` CLI command."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from omnibase_core.cli.cli_commands import cli

pytestmark = pytest.mark.unit


class TestRunCommand:
    """Tests for the ``onex run`` sub-command."""

    def test_run_command_exists(self) -> None:
        """``onex run --help`` should succeed and mention workflow."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])
        assert result.exit_code == 0
        assert (
            "workflow" in result.output.lower() or "contract" in result.output.lower()
        )

    def test_run_missing_workflow_fails(self, tmp_path: Path) -> None:
        """``onex run nonexistent.yaml`` should exit non-zero with clear message."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", str(tmp_path / "nonexistent.yaml")])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_run_invalid_backend_key_fails(self, tmp_path: Path) -> None:
        """``--backend bad_key=value`` should fail with known-keys hint."""
        workflow = tmp_path / "wf.yaml"
        workflow.write_text("terminal_event: done\nnodes: []\n")
        runner = CliRunner()
        result = runner.invoke(
            cli, ["run", str(workflow), "--backend", "bad_key=value"]
        )
        assert result.exit_code != 0
        assert "unknown backend key" in result.output.lower()

    def test_run_invalid_backend_format_fails(self, tmp_path: Path) -> None:
        """``--backend noequals`` should fail with format hint."""
        workflow = tmp_path / "wf.yaml"
        workflow.write_text("terminal_event: done\nnodes: []\n")
        runner = CliRunner()
        result = runner.invoke(cli, ["run", str(workflow), "--backend", "noequals"])
        assert result.exit_code != 0
        assert "expected key=value" in result.output.lower()
