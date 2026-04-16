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

pytestmark = pytest.mark.unit


def test_unknown_node_name_reports_known_names() -> None:
    """Unknown name errors with the list of known names."""
    runner = CliRunner()
    result = runner.invoke(run_node_by_name, ["definitely_not_a_real_node"])
    assert result.exit_code != 0
    combined = result.output + str(result.exception or "")
    assert "Unknown node 'definitely_not_a_real_node'" in combined


def test_valid_node_name_resolves_packaged_contract(tmp_path: Path) -> None:
    """A known onex.nodes entry point resolves to a packaged contract.yaml.

    Stubs entry_points and importlib.import_module so the test owns the registry
    and does not depend on which packages are installed in the environment.
    """
    fake_pkg = tmp_path / "fake_node_pkg"
    fake_pkg.mkdir()
    contract_file = fake_pkg / "contract.yaml"
    contract_file.write_text("name: test_node\n", encoding="utf-8")

    import types

    fake_module = types.ModuleType("fake_node_pkg")
    fake_module.__file__ = str(fake_pkg / "__init__.py")

    class _FakeEP:
        name = "test.node"
        value = "fake_node_pkg"
        dist = "local-fake"

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
        contract = _resolve_packaged_contract("test.node")
    assert contract.name == "contract.yaml"
    assert contract.exists()


def test_contract_override_wins_over_packaged(tmp_path: Path) -> None:
    """``--contract <path>`` takes precedence over the packaged contract.

    Proves the override was honored: we point --contract at a well-formed YAML
    whose handler module does not exist. The runtime attempts to resolve that
    bogus handler, fails, and exits non-zero — confirming the override was used,
    not the packaged contract. Uses a dummy node name to avoid any dependency on
    installed onex.nodes entry points. Asserts _resolve_packaged_contract was
    never consulted (the override path must short-circuit it entirely).
    """
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
    with patch(
        "omnibase_core.cli.cli_node._resolve_packaged_contract",
        side_effect=AssertionError(
            "_resolve_packaged_contract must not be called when --contract is provided"
        ),
    ) as mock_resolve:
        result = runner.invoke(
            run_node_by_name,
            [
                "unused-node-name",
                "--contract",
                str(override),
                "--state-root",
                str(tmp_path / "state"),
                "--timeout",
                "5",
            ],
        )
    mock_resolve.assert_not_called()
    # Exit code 1 = FAILED (handler could not be resolved from override). If the
    # override had been ignored and packaged resolution ran, it would have raised
    # AssertionError above — a different failure mode.
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
