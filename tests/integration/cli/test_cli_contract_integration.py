# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Integration tests for contract CLI commands.

These tests verify the full workflow of the contract CLI:
- `onex contract init` -> creates patch file
- `onex contract build` -> expands contract from patch
- `onex contract diff` -> compares two contracts

See OMN-1129 for implementation details.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from omnibase_core.cli.cli_contract import contract
from omnibase_core.enums.enum_cli_exit_code import EnumCLIExitCode

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


class TestContractCLIIntegration:
    """Integration tests for full contract CLI workflow."""

    def test_full_workflow_init_build_diff(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test complete workflow: init -> build -> modify -> build -> diff.

        This test exercises the full contract CLI workflow:
        1. Initialize a new patch file from a profile
        2. Build an expanded contract from the patch
        3. Create a modified version of the patch
        4. Build the second version
        5. Diff the two expanded contracts
        """
        # Step 1: Initialize a patch file
        patch_v1 = tmp_path / "patch_v1.yaml"
        result = runner.invoke(
            contract,
            [
                "init",
                "--type",
                "compute",
                "--profile",
                "pure",
                "--output",
                str(patch_v1),
            ],
        )
        assert result.exit_code == EnumCLIExitCode.SUCCESS, (
            f"Init failed: {result.output}"
        )
        assert patch_v1.exists(), "Patch file was not created"

        # Verify patch structure
        patch_content = yaml.safe_load(patch_v1.read_text())
        assert patch_content is not None
        assert "extends" in patch_content
        assert patch_content["extends"]["profile"] == "compute_pure"

        # Step 2: Build expanded contract v1
        expanded_v1 = tmp_path / "expanded_v1.yaml"
        result = runner.invoke(
            contract,
            ["build", str(patch_v1), "--output", str(expanded_v1)],
        )
        assert result.exit_code == EnumCLIExitCode.SUCCESS, (
            f"Build v1 failed: {result.output}"
        )
        assert expanded_v1.exists(), "Expanded contract v1 was not created"

        # Verify expanded contract has required fields
        expanded_v1_content = yaml.safe_load(expanded_v1.read_text())
        assert "_metadata" in expanded_v1_content
        assert "profile" in expanded_v1_content["_metadata"]
        assert expanded_v1_content["_metadata"]["profile"] == "compute_pure"

        # Step 3: Create modified patch (version 2)
        patch_v2 = tmp_path / "patch_v2.yaml"
        patch_v2_content = """# Modified patch for version 2
extends:
  profile: compute_pure
  version: "1.0.0"
name: my_contract_name
node_version:
  major: 1
  minor: 1
  patch: 0
description: "Modified contract with version bump"
descriptor:
  timeout_ms: 60000
"""
        patch_v2.write_text(patch_v2_content)

        # Step 4: Build expanded contract v2
        expanded_v2 = tmp_path / "expanded_v2.yaml"
        result = runner.invoke(
            contract,
            ["build", str(patch_v2), "--output", str(expanded_v2)],
        )
        assert result.exit_code == EnumCLIExitCode.SUCCESS, (
            f"Build v2 failed: {result.output}"
        )
        assert expanded_v2.exists(), "Expanded contract v2 was not created"

        # Step 5: Diff the two contracts
        result = runner.invoke(
            contract,
            ["diff", str(expanded_v1), str(expanded_v2)],
        )
        # Exit code 2 (WARNING) indicates differences found
        assert result.exit_code == EnumCLIExitCode.WARNING, (
            f"Diff unexpected exit: {result.output}"
        )

        # Verify diff output shows meaningful changes
        output_lower = result.output.lower()
        assert any(
            indicator in output_lower
            for indicator in ["changed", "added", "timeout", "version", "description"]
        ), f"Diff output missing expected change indicators: {result.output}"

    def test_workflow_init_build_json_format(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test init -> build workflow with JSON output format."""
        # Initialize patch
        patch_file = tmp_path / "patch.yaml"
        result = runner.invoke(
            contract,
            [
                "init",
                "--type",
                "orchestrator",
                "--profile",
                "safe",
                "--output",
                str(patch_file),
            ],
        )
        assert result.exit_code == EnumCLIExitCode.SUCCESS

        # Build with JSON format
        result = runner.invoke(
            contract,
            ["build", str(patch_file), "--format", "json"],
        )
        assert result.exit_code == EnumCLIExitCode.SUCCESS

        # Verify JSON output is valid
        try:
            output_json = json.loads(result.output)
            assert isinstance(output_json, dict)
            assert "_metadata" in output_json
        except json.JSONDecodeError:
            pytest.fail(f"Build output was not valid JSON: {result.output}")

    def test_workflow_diff_with_json_format(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test diff workflow with JSON output format."""
        # Create two contracts with differences
        contract_v1 = tmp_path / "v1.yaml"
        contract_v2 = tmp_path / "v2.yaml"

        contract_v1.write_text("""
handler_id: "node.test"
name: "test"
version: "1.0.0"
descriptor:
  timeout_ms: 30000
""")

        contract_v2.write_text("""
handler_id: "node.test"
name: "test"
version: "2.0.0"
descriptor:
  timeout_ms: 60000
""")

        # Diff with JSON format
        result = runner.invoke(
            contract,
            ["diff", str(contract_v1), str(contract_v2), "--format", "json"],
        )

        # Exit code 2 indicates differences
        assert result.exit_code == EnumCLIExitCode.WARNING

        # Verify JSON output is valid and has expected structure
        try:
            diff_json = json.loads(result.output)
            assert isinstance(diff_json, dict)
            assert "has_changes" in diff_json
            assert diff_json["has_changes"] is True
        except json.JSONDecodeError:
            pytest.fail(f"Diff JSON output was not valid: {result.output}")

    def test_workflow_diff_with_yaml_format(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test diff workflow with YAML output format."""
        # Create two contracts with differences
        contract_v1 = tmp_path / "v1.yaml"
        contract_v2 = tmp_path / "v2.yaml"

        contract_v1.write_text("""
handler_id: "node.test"
name: "test"
version: "1.0.0"
""")

        contract_v2.write_text("""
handler_id: "node.test"
name: "test"
version: "2.0.0"
""")

        # Diff with YAML format
        result = runner.invoke(
            contract,
            ["diff", str(contract_v1), str(contract_v2), "--format", "yaml"],
        )

        # Exit code 2 indicates differences
        assert result.exit_code == EnumCLIExitCode.WARNING

        # Verify YAML output is valid
        try:
            diff_yaml = yaml.safe_load(result.output)
            assert isinstance(diff_yaml, dict)
            assert "has_changes" in diff_yaml
            assert diff_yaml["has_changes"] is True
        except yaml.YAMLError:
            pytest.fail(f"Diff YAML output was not valid: {result.output}")

    def test_workflow_with_all_node_types(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test init -> build workflow for all node types."""
        node_types_and_profiles = [
            ("orchestrator", "safe"),
            ("orchestrator", "parallel"),
            ("orchestrator", "resilient"),
            ("reducer", "fsm_basic"),
            ("effect", "idempotent"),
            ("compute", "pure"),
        ]

        for node_type, profile in node_types_and_profiles:
            patch_file = tmp_path / f"patch_{node_type}_{profile}.yaml"
            expanded_file = tmp_path / f"expanded_{node_type}_{profile}.yaml"

            # Initialize
            result = runner.invoke(
                contract,
                [
                    "init",
                    "--type",
                    node_type,
                    "--profile",
                    profile,
                    "--output",
                    str(patch_file),
                ],
            )
            assert result.exit_code == EnumCLIExitCode.SUCCESS, (
                f"Init failed for {node_type}/{profile}: {result.output}"
            )

            # Build
            result = runner.invoke(
                contract,
                ["build", str(patch_file), "--output", str(expanded_file)],
            )
            assert result.exit_code == EnumCLIExitCode.SUCCESS, (
                f"Build failed for {node_type}/{profile}: {result.output}"
            )

            # Verify expanded contract
            expanded_content = yaml.safe_load(expanded_file.read_text())
            assert "_metadata" in expanded_content
            expected_profile = f"{node_type}_{profile}"
            assert expanded_content["_metadata"]["profile"] == expected_profile

    def test_diff_no_changes_for_identical_contracts(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that diff shows no changes when comparing identical contracts."""
        # Create identical contracts
        content = """
handler_id: "node.identical"
name: "identical"
version: "1.0.0"
descriptor:
  handler_kind: "compute"
"""
        contract_a = tmp_path / "a.yaml"
        contract_b = tmp_path / "b.yaml"
        contract_a.write_text(content)
        contract_b.write_text(content)

        result = runner.invoke(
            contract,
            ["diff", str(contract_a), str(contract_b)],
        )

        # Exit code 0 indicates no differences
        assert result.exit_code == EnumCLIExitCode.SUCCESS
        assert (
            "no differences" in result.output.lower()
            or "no change" in result.output.lower()
        )

    def test_build_validation_failure_reports_useful_error(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that build validation failures produce useful error messages."""
        # Create an invalid patch file with unknown profile
        invalid_patch = tmp_path / "invalid.yaml"
        invalid_patch.write_text("""
extends:
  profile: nonexistent_profile
  version: "1.0.0"
name: test
node_version:
  major: 1
  minor: 0
  patch: 0
""")

        result = runner.invoke(
            contract,
            ["build", str(invalid_patch)],
        )

        assert result.exit_code == EnumCLIExitCode.ERROR
        # Error message should be helpful
        assert "error" in result.output.lower() or "failed" in result.output.lower()

    def test_diff_output_to_file(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test diff command with output to file."""
        # Create contracts
        contract_v1 = tmp_path / "v1.yaml"
        contract_v2 = tmp_path / "v2.yaml"
        diff_output = tmp_path / "diff.txt"

        contract_v1.write_text("""
handler_id: "node.test"
name: "test"
version: "1.0.0"
""")

        contract_v2.write_text("""
handler_id: "node.test"
name: "test_updated"
version: "2.0.0"
""")

        result = runner.invoke(
            contract,
            ["diff", str(contract_v1), str(contract_v2), "--output", str(diff_output)],
        )

        # Exit code 2 indicates differences
        assert result.exit_code == EnumCLIExitCode.WARNING
        assert diff_output.exists()

        # Verify diff file content
        diff_content = diff_output.read_text()
        assert "name" in diff_content.lower() or "version" in diff_content.lower()


class TestContractCLIErrorHandling:
    """Integration tests for CLI error handling."""

    def test_init_invalid_profile_combination(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that init fails gracefully with invalid profile for node type."""
        result = runner.invoke(
            contract,
            [
                "init",
                "--type",
                "compute",
                "--profile",
                "safe",  # 'safe' is for orchestrator, not compute
                "--output",
                str(tmp_path / "patch.yaml"),
            ],
        )
        assert result.exit_code != EnumCLIExitCode.SUCCESS
        assert "unknown" in result.output.lower() or "error" in result.output.lower()

    def test_build_missing_file(self, runner: CliRunner) -> None:
        """Test that build fails gracefully for missing file."""
        result = runner.invoke(
            contract,
            ["build", "/nonexistent/path/to/patch.yaml"],
        )
        assert result.exit_code != EnumCLIExitCode.SUCCESS
        assert (
            "not found" in result.output.lower()
            or "does not exist" in result.output.lower()
            or "error" in result.output.lower()
        )

    def test_diff_missing_file(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test that diff fails gracefully for missing files."""
        existing = tmp_path / "existing.yaml"
        existing.write_text("handler_id: test\nname: test")

        result = runner.invoke(
            contract,
            ["diff", str(existing), "/nonexistent/new.yaml"],
        )
        assert result.exit_code != EnumCLIExitCode.SUCCESS

    def test_build_invalid_yaml(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test that build handles invalid YAML gracefully."""
        invalid_yaml = tmp_path / "invalid.yaml"
        invalid_yaml.write_text("this: is: invalid: yaml: [[[")

        result = runner.invoke(
            contract,
            ["build", str(invalid_yaml)],
        )
        assert result.exit_code == EnumCLIExitCode.ERROR
        assert "yaml" in result.output.lower() or "parse" in result.output.lower()

    def test_diff_invalid_yaml(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test that diff handles invalid YAML gracefully."""
        valid = tmp_path / "valid.yaml"
        invalid = tmp_path / "invalid.yaml"
        valid.write_text("handler_id: test\nname: test")
        invalid.write_text("not: valid: yaml: [[[")

        result = runner.invoke(
            contract,
            ["diff", str(valid), str(invalid)],
        )
        assert result.exit_code == EnumCLIExitCode.ERROR
        assert "yaml" in result.output.lower() or "parse" in result.output.lower()
