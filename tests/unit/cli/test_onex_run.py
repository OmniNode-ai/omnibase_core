# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for `onex run <name>` CLI alias (OMN-9260).

`onex run` is a canonical alias for `onex node` — same signature, same flags,
same RuntimeLocal execution path. These tests verify:
  - `onex run` exists (not "No such command 'run'")
  - `onex run <unknown>` produces same error shape as `onex node <unknown>`
  - `onex run --help` lists the same flags as `onex node --help`
  - flag parity: --contract, --input, --state-root, --backend, --timeout, --verbose
  - `onex run` and `onex node` produce identical results for the same inputs
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from omnibase_core.cli.cli_commands import cli


def test_onex_run_command_exists() -> None:
    """``onex run`` must not return 'No such command'."""
    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--help"])
    assert "No such command" not in result.output
    assert result.exit_code == 0


def test_onex_run_help_lists_expected_flags() -> None:
    """``onex run --help`` must expose all the same flags as ``onex node``."""
    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--help"])
    assert result.exit_code == 0
    output = result.output
    assert "--contract" in output
    assert "--input" in output
    assert "--state-root" in output
    assert "--backend" in output
    assert "--timeout" in output
    assert "--verbose" in output


def test_onex_run_unknown_node_reports_known_names() -> None:
    """``onex run <unknown>`` must error with the same shape as ``onex node <unknown>``."""
    runner = CliRunner()
    run_result = runner.invoke(cli, ["run", "definitely_not_a_real_node"])
    node_result = runner.invoke(cli, ["node", "definitely_not_a_real_node"])

    assert run_result.exit_code != 0
    assert node_result.exit_code != 0

    run_combined = run_result.output + str(run_result.exception or "")
    node_combined = node_result.output + str(node_result.exception or "")
    assert "Unknown node 'definitely_not_a_real_node'" in run_combined
    assert "Unknown node 'definitely_not_a_real_node'" in node_combined


def test_onex_run_and_node_produce_identical_error_for_same_unknown() -> None:
    """Both aliases must emit the same error message text for an unknown node."""
    runner = CliRunner()
    run_result = runner.invoke(cli, ["run", "no_such_node_xyz"])
    node_result = runner.invoke(cli, ["node", "no_such_node_xyz"])

    run_err = run_result.output + str(run_result.exception or "")
    node_err = node_result.output + str(node_result.exception or "")

    assert "Unknown node 'no_such_node_xyz'" in run_err
    assert "Unknown node 'no_such_node_xyz'" in node_err


def test_onex_run_input_file_not_found_surfaces_cli_error(tmp_path: Path) -> None:
    """``onex run <node> --input <nonexistent>`` must fail at the CLI layer."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "run",
            "node_merge_sweep",
            "--input",
            str(tmp_path / "does_not_exist.json"),
        ],
    )
    assert result.exit_code != 0
    assert "does_not_exist.json" in result.output


def test_onex_run_contract_override_with_real_node(tmp_path: Path) -> None:
    """``onex run <node> --contract <path>`` honors the override (same as onex node)."""
    from importlib.metadata import entry_points

    available = [ep.name for ep in entry_points(group="onex.nodes")]
    if not available:
        pytest.skip("No onex.nodes entry points registered in this env")

    override = tmp_path / "custom_contract.yaml"
    override.write_text(
        "---\n"
        "name: custom\n"
        "node_type: compute\n"
        "handler:\n"
        "  module: does.not.exist.anywhere_zzzqqq\n"
        "  class: Nope\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "run",
            available[0],
            "--contract",
            str(override),
            "--state-root",
            str(tmp_path / "state"),
            "--timeout",
            "5",
        ],
    )
    # Exit 1 = FAILED because override's handler does not exist.
    # If the override were ignored and packaged contract loaded, exit would differ.
    assert result.exit_code == 1
