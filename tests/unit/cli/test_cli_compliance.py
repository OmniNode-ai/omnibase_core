# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for onex compliance CLI command group."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from omnibase_core.cli.cli_commands import cli


@pytest.mark.unit
class TestComplianceCommandExists:
    """Verify the compliance command group is registered and reachable."""

    def test_compliance_check_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["compliance", "check", "--help"])
        assert result.exit_code == 0
        assert "repo-root" in result.output
        assert "output" in result.output

    def test_compliance_group_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["compliance", "--help"])
        assert result.exit_code == 0
        assert "check" in result.output


@pytest.mark.unit
class TestComplianceCheckRuns:
    """Verify compliance check discovers contracts and produces output."""

    def test_check_with_passing_node(self, tmp_path: Path) -> None:
        """A minimal valid node with contract + handler file passes all checks."""
        node_dir = tmp_path / "nodes" / "node_test_compute"
        node_dir.mkdir(parents=True)

        contract = {
            "node_id": "node_test_compute",
            "node_kind": "COMPUTE",
            "version": {"major": 1, "minor": 0, "patch": 0},
            "handler_routing": {
                "default_handler": "handler_test:HandlerTest",
            },
        }
        (node_dir / "contract.yaml").write_text(yaml.dump(contract))
        (node_dir / "handler_test.py").write_text("class HandlerTest: pass\n")

        output_path = tmp_path / "report.yaml"
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "compliance",
                "check",
                "--repo-root",
                str(tmp_path),
                "--output",
                str(output_path),
            ],
        )
        assert result.exit_code == 0
        assert "PASS node_test_compute" in result.output
        assert output_path.exists()

        report = yaml.safe_load(output_path.read_text())
        assert report["passed"] == 1
        assert report["failed"] == 0

    def test_check_with_no_contracts(self, tmp_path: Path) -> None:
        """Empty directory produces no failures."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["compliance", "check", "--repo-root", str(tmp_path)],
        )
        assert result.exit_code == 0
        assert "No contract.yaml files found" in result.output
