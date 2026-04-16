# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ``onex run`` CLI command."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from omnibase_core.cli.cli_commands import cli
from omnibase_core.cli.cli_run import _resolve_node_module

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

    # ------------------------------------------------------------------
    # Node name resolution
    # ------------------------------------------------------------------

    def test_run_with_workflow_yaml_calls_existing_path(self, tmp_path: Path) -> None:
        """When target is an existing YAML file, RuntimeLocal is invoked (not node path)."""
        workflow = tmp_path / "workflow.yaml"
        workflow.write_text("terminal_event: done\nnodes: []\n")

        mock_runtime = MagicMock()
        mock_runtime.exit_code = 0

        with patch("omnibase_core.cli.cli_run.RuntimeLocal", return_value=mock_runtime):
            with patch(
                "omnibase_core.cli.cli_run.parse_backend_overrides", return_value={}
            ):
                runner = CliRunner()
                result = runner.invoke(cli, ["run", str(workflow)])

        mock_runtime.run.assert_called_once()

    def test_run_with_node_name_short_form(self) -> None:
        """``onex run merge_sweep`` resolves to omnimarket.nodes.node_merge_sweep."""
        with patch(
            "omnibase_core.cli.cli_run._resolve_node_module",
            return_value="omnimarket.nodes.node_merge_sweep",
        ) as mock_resolve:
            with patch(
                "omnibase_core.cli.cli_run.subprocess.run",
                return_value=MagicMock(returncode=0),
            ) as mock_sub:
                runner = CliRunner()
                result = runner.invoke(cli, ["run", "merge_sweep"])

        mock_resolve.assert_called_once_with("merge_sweep")
        mock_sub.assert_called_once()
        called_cmd = mock_sub.call_args[0][0]
        assert called_cmd == [sys.executable, "-m", "omnimarket.nodes.node_merge_sweep"]

    def test_run_with_node_name_full_form(self) -> None:
        """``onex run node_merge_sweep`` resolves to omnimarket.nodes.node_merge_sweep."""
        with patch(
            "omnibase_core.cli.cli_run._resolve_node_module",
            return_value="omnimarket.nodes.node_merge_sweep",
        ):
            with patch(
                "omnibase_core.cli.cli_run.subprocess.run",
                return_value=MagicMock(returncode=0),
            ) as mock_sub:
                runner = CliRunner()
                result = runner.invoke(cli, ["run", "node_merge_sweep"])

        mock_sub.assert_called_once()
        called_cmd = mock_sub.call_args[0][0]
        assert called_cmd == [sys.executable, "-m", "omnimarket.nodes.node_merge_sweep"]

    def test_run_with_unknown_node_emits_helpful_error(self) -> None:
        """Unknown node name produces a helpful error message and exits non-zero."""
        with patch("omnibase_core.cli.cli_run._resolve_node_module", return_value=None):
            runner = CliRunner()
            result = runner.invoke(cli, ["run", "totally_unknown_node"])

        assert result.exit_code != 0
        assert "totally_unknown_node" in result.output
        assert "merge_sweep" in result.output or "node name" in result.output.lower()

    def test_run_passes_through_unknown_args_to_node_argparse(self) -> None:
        """Extra args after the node name are forwarded to the node subprocess."""
        with patch(
            "omnibase_core.cli.cli_run._resolve_node_module",
            return_value="omnimarket.nodes.node_merge_sweep",
        ):
            with patch(
                "omnibase_core.cli.cli_run.subprocess.run",
                return_value=MagicMock(returncode=0),
            ) as mock_sub:
                runner = CliRunner()
                result = runner.invoke(
                    cli, ["run", "merge_sweep", "--dry-run", "--repo", "omnibase_core"]
                )

        mock_sub.assert_called_once()
        called_cmd = mock_sub.call_args[0][0]
        assert "--dry-run" in called_cmd
        assert "--repo" in called_cmd
        assert "omnibase_core" in called_cmd


class TestResolveNodeModule:
    """Unit tests for ``_resolve_node_module`` helper."""

    def test_returns_none_for_unimportable_name(self) -> None:
        """Returns None when neither candidate module is importable."""
        result = _resolve_node_module("totally_nonexistent_xyz_abc")
        assert result is None

    def test_returns_full_path_on_first_candidate_match(self) -> None:
        """Returns the first importable candidate path."""
        fake_module = MagicMock()
        with patch("omnibase_core.cli.cli_run.importlib.import_module") as mock_import:
            mock_import.side_effect = [fake_module, ImportError()]
            result = _resolve_node_module("merge_sweep")
        assert result == "omnimarket.nodes.merge_sweep"

    def test_returns_second_candidate_when_first_missing(self) -> None:
        """Falls back to node_<name> when <name> is not importable."""
        fake_module = MagicMock()
        with patch("omnibase_core.cli.cli_run.importlib.import_module") as mock_import:
            mock_import.side_effect = [ImportError(), fake_module]
            result = _resolve_node_module("merge_sweep")
        assert result == "omnimarket.nodes.node_merge_sweep"
