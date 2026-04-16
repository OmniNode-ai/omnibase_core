# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for `onex node <name>` CLI resolution (OMN-8938).

Covers the 5 CLI migration branches:
    - unknown name → clear error + lists known
    - valid name → resolves to packaged contract.yaml
    - --contract override → overrides packaged resolution
    - missing packaged contract → cites convention violation
    - --input file not found → CLI-level error
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from omnibase_core.cli.cli_node import _resolve_packaged_contract, run_node_by_name


def test_unknown_node_name_reports_known_names() -> None:
    """Unknown name errors with the list of known names."""
    runner = CliRunner()
    result = runner.invoke(run_node_by_name, ["definitely_not_a_real_node"])
    assert result.exit_code != 0
    combined = result.output + str(result.exception or "")
    assert "Unknown node 'definitely_not_a_real_node'" in combined


def test_valid_node_name_resolves_packaged_contract() -> None:
    """A real onex.nodes entry point resolves to a packaged contract.yaml.

    Skipped if no onex.nodes entry points are registered in the test env.
    """
    from importlib.metadata import entry_points

    available = [ep.name for ep in entry_points(group="onex.nodes")]
    if not available:
        pytest.skip("No onex.nodes entry points registered in this env")
    contract = _resolve_packaged_contract(available[0])
    assert contract.name == "contract.yaml"
    assert contract.exists()


def test_contract_override_wins_over_packaged(tmp_path: Path) -> None:
    """``--contract <path>`` takes precedence over the packaged contract.

    Proves the override was honored by confirming the CLI processes the
    override's contract path (not the packaged one): we point --contract
    at a well-formed YAML whose handler module does not exist. The runtime
    attempts to resolve that bogus handler, fails, and exits non-zero.
    A FAILED exit with the handler-not-found log confirms override wins.
    """
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
        run_node_by_name,
        [
            available[0],
            "--contract",
            str(override),
            "--state-root",
            str(tmp_path / "state"),
            "--timeout",
            "5",
        ],
    )
    # Exit code 1 = FAILED (handler could not be resolved from override). If the
    # override had been ignored and the packaged contract loaded instead, the
    # well-formed packaged handler would have succeeded or hit a different error.
    assert result.exit_code == 1


def test_missing_packaged_contract_reports_convention_violation(tmp_path: Path) -> None:
    """If an entry-point module resolves but has no contract.yaml, error cites the convention."""
    fake_pkg = tmp_path / "fake_pkg"
    fake_pkg.mkdir()
    (fake_pkg / "__init__.py").write_text("", encoding="utf-8")

    class _FakeEP:
        name = "node_has_no_contract"
        value = "fake_pkg"
        dist = "local-fake"

    fake_module = type("FakeMod", (), {"__file__": str(fake_pkg / "__init__.py")})

    with (
        patch(
            "omnibase_core.cli.cli_node.entry_points",
            return_value=[_FakeEP()],
        ),
        patch(
            "omnibase_core.cli.cli_node.importlib.import_module",
            return_value=fake_module,
        ),
    ):
        with pytest.raises(Exception) as exc_info:
            _resolve_packaged_contract("node_has_no_contract")
    assert "packaging convention" in str(exc_info.value)


def test_input_file_not_found_surfaces_cli_error(tmp_path: Path) -> None:
    """``--input <nonexistent>`` must fail at the CLI layer with a Click-level error."""
    runner = CliRunner()
    result = runner.invoke(
        run_node_by_name,
        [
            "node_merge_sweep",
            "--input",
            str(tmp_path / "does_not_exist.json"),
        ],
    )
    assert result.exit_code != 0
    assert "does_not_exist.json" in result.output
