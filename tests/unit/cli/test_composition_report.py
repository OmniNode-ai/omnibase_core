# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for composition-report CLI command.

Tests the CLI command for generating composition analysis reports
from execution manifests.

.. versionadded:: 0.4.0
    Added as part of Manifest Generation & Observability (OMN-1113)
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from click.testing import CliRunner

from omnibase_core.cli.cli_commands import cli
from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
from omnibase_core.enums.enum_handler_execution_phase import EnumHandlerExecutionPhase
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.manifest import (
    ModelContractIdentity,
    ModelEmissionsSummary,
    ModelExecutionManifest,
    ModelHookTrace,
    ModelNodeIdentity,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.fixture
def sample_manifest() -> ModelExecutionManifest:
    """Create a sample manifest for testing."""
    node_identity = ModelNodeIdentity(
        node_id="test-compute-node",
        node_kind=EnumNodeKind.COMPUTE,
        node_version=ModelSemVer(major=1, minor=0, patch=0),
        namespace="test.namespace",
    )
    contract_identity = ModelContractIdentity(
        contract_id="test-contract",
        contract_path="contracts/test.yaml",
        profile_name="default",
    )
    hook_trace = ModelHookTrace(
        hook_id="hook-1",
        handler_id="handler_test",
        phase=EnumHandlerExecutionPhase.EXECUTE,
        status=EnumExecutionStatus.SUCCESS,
        started_at=datetime.now(UTC),
        duration_ms=45.5,
    )
    emissions = ModelEmissionsSummary(
        events_count=2,
        event_types=["UserCreated", "UserUpdated"],
    )
    return ModelExecutionManifest(
        node_identity=node_identity,
        contract_identity=contract_identity,
        hook_traces=[hook_trace],
        emissions_summary=emissions,
    )


@pytest.fixture
def manifest_file(sample_manifest: ModelExecutionManifest, tmp_path: Path) -> Path:
    """Create a temporary manifest file."""
    path = tmp_path / "manifest.json"
    path.write_text(sample_manifest.model_dump_json())
    return path  # No cleanup needed, tmp_path handles it


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI runner."""
    return CliRunner()


@pytest.mark.unit
class TestCompositionReportCommand:
    """Test composition-report command."""

    def test_default_text_output(self, runner: CliRunner, manifest_file: Path) -> None:
        """Test default text format output."""
        result = runner.invoke(cli, ["composition-report", str(manifest_file)])

        assert result.exit_code == 0
        assert "COMPOSITION REPORT" in result.output
        assert "test-compute-node" in result.output

    def test_json_format(self, runner: CliRunner, manifest_file: Path) -> None:
        """Test JSON format output."""
        result = runner.invoke(
            cli, ["composition-report", str(manifest_file), "--format", "json"]
        )

        assert result.exit_code == 0
        # Should be valid JSON
        data = json.loads(result.output)
        assert "manifest_id" in data

    def test_yaml_format(self, runner: CliRunner, manifest_file: Path) -> None:
        """Test YAML format output."""
        result = runner.invoke(
            cli, ["composition-report", str(manifest_file), "--format", "yaml"]
        )

        assert result.exit_code == 0
        assert "manifest_id:" in result.output

    def test_markdown_format(self, runner: CliRunner, manifest_file: Path) -> None:
        """Test Markdown format output."""
        result = runner.invoke(
            cli, ["composition-report", str(manifest_file), "--format", "markdown"]
        )

        assert result.exit_code == 0
        assert "# Execution Manifest" in result.output

    def test_verbose_flag(self, runner: CliRunner, manifest_file: Path) -> None:
        """Test verbose output."""
        result = runner.invoke(
            cli, ["composition-report", str(manifest_file), "--verbose"]
        )

        assert result.exit_code == 0
        # Verbose output should include more details
        assert "handler_test" in result.output

    def test_show_timing_flag(self, runner: CliRunner, manifest_file: Path) -> None:
        """Test show-timing flag."""
        result = runner.invoke(
            cli, ["composition-report", str(manifest_file), "--show-timing"]
        )

        assert result.exit_code == 0
        # Should show timing information
        assert "ms" in result.output.lower()

    def test_output_to_file(
        self, runner: CliRunner, manifest_file: Path, tmp_path: Path
    ) -> None:
        """Test writing output to file."""
        output_path = tmp_path / "output.txt"

        result = runner.invoke(
            cli,
            ["composition-report", str(manifest_file), "-o", str(output_path)],
        )

        assert result.exit_code == 0
        assert "Report written to" in result.output
        assert output_path.exists()

        content = output_path.read_text()
        assert "COMPOSITION REPORT" in content

    def test_invalid_manifest_file(self, runner: CliRunner) -> None:
        """Test with non-existent file."""
        result = runner.invoke(cli, ["composition-report", "nonexistent.json"])

        assert result.exit_code != 0

    def test_invalid_json_file(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test with invalid JSON file."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("not valid json")

        result = runner.invoke(cli, ["composition-report", str(invalid_file)])

        assert result.exit_code != 0
        assert "Invalid JSON" in result.output


@pytest.mark.unit
class TestCompositionReportHelp:
    """Test composition-report help text."""

    def test_help_output(self, runner: CliRunner) -> None:
        """Test help output."""
        result = runner.invoke(cli, ["composition-report", "--help"])

        assert result.exit_code == 0
        assert "composition-report" in result.output.lower()
        assert "--format" in result.output
        assert "--output" in result.output
        assert "--verbose" in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
