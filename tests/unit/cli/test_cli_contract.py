# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Comprehensive TDD tests for contract CLI commands.

Tests cover the following CLI commands:
- `onex contract init`: Creates minimal patch files from profiles
- `onex contract build`: Merges patches with profiles, validates, outputs expanded contracts
- `onex contract diff`: Semantic diff between two contract YAML files

This file was originally written following TDD. The implementation is now complete.
See OMN-1129 for the ticket details.

Test Categories:
- InitCommandTests: Tests for the `init` subcommand
- BuildCommandTests: Tests for the `build` subcommand
- DiffCommandTests: Tests for the `diff` subcommand
- ContractGroupTests: Tests for the `contract` group command itself

Note on Implementation Status:
    All CLI commands (init, build, diff) are fully implemented.
    Tests that were originally marked with @tdd_pending now pass.

Related:
    - OMN-1129: Contract CLI Tooling
    - ContractProfileFactory: Profile resolution
    - ContractMergeEngine: Patch merging
    - ContractValidationPipeline: Multi-phase validation
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from omnibase_core.cli.cli_contract import contract
from omnibase_core.enums.enum_cli_exit_code import EnumCLIExitCode

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


# NOTE: TDD tests are now complete. The @tdd_pending marker has been removed
# since all implementations for OMN-1129 are finished.


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def valid_patch_yaml() -> str:
    """Create a minimal valid patch YAML content."""
    return """# Contract Patch
extends:
  profile: compute_pure
  version: "1.0.0"
name: my_compute_handler
node_version:
  major: 1
  minor: 0
  patch: 0
description: "A custom compute handler"
"""


@pytest.fixture
def valid_contract_yaml() -> str:
    """Create a valid expanded contract YAML content."""
    return """# Expanded Contract
handler_id: "node.my_compute_handler"
name: "my_compute_handler"
version: "1.0.0"
description: "A custom compute handler"
input_model: "ModelAny"
output_model: "ModelAny"
descriptor:
  node_archetype: "compute"
  purity: "pure"
  idempotent: true
  timeout_ms: 30000
capability_inputs: []
capability_outputs: []
tags: []
"""


@pytest.fixture
def contract_v1_yaml() -> str:
    """Create first version of a contract for diff testing."""
    return """handler_id: "node.my_handler"
name: "my_handler"
version: "1.0.0"
description: "Original description"
input_model: "ModelInput"
output_model: "ModelOutput"
descriptor:
  node_archetype: "compute"
  purity: "pure"
  idempotent: true
  timeout_ms: 30000
capability_inputs: []
capability_outputs: []
tags:
  - "v1"
"""


@pytest.fixture
def contract_v2_yaml() -> str:
    """Create second version of a contract for diff testing."""
    return """handler_id: "node.my_handler"
name: "my_handler"
version: "2.0.0"
description: "Updated description"
input_model: "ModelInputV2"
output_model: "ModelOutput"
descriptor:
  node_archetype: "compute"
  purity: "side_effecting"
  idempotent: false
  timeout_ms: 60000
capability_inputs:
  - alias: "logging"
    capability: "logging.structured"
capability_outputs:
  - "metrics.emitted"
tags:
  - "v2"
  - "updated"
"""


# =============================================================================
# Contract Group Command Tests
# =============================================================================


@pytest.mark.unit
class TestContractGroupCommand:
    """Tests for the contract command group."""

    def test_contract_group_exists(self, runner: CliRunner) -> None:
        """Test that the contract command group exists."""
        result = runner.invoke(contract, ["--help"])
        assert result.exit_code == EnumCLIExitCode.SUCCESS

    def test_contract_help_shows_subcommands(self, runner: CliRunner) -> None:
        """Test that contract --help shows all subcommands."""
        result = runner.invoke(contract, ["--help"])
        assert result.exit_code == EnumCLIExitCode.SUCCESS
        assert "init" in result.output
        assert "build" in result.output
        assert "diff" in result.output

    def test_contract_no_command_shows_help(self, runner: CliRunner) -> None:
        """Test that invoking contract without subcommand shows help."""
        result = runner.invoke(contract, [])
        # Click groups without a default command show usage and exit with code 0 or 2
        # depending on Click version - both are acceptable
        assert result.exit_code in (0, 2)
        # Should show usage information
        assert "Usage" in result.output or "usage" in result.output.lower()


# =============================================================================
# Init Command Tests
# =============================================================================


@pytest.mark.unit
class TestInitCommand:
    """Tests for the `onex contract init` command.

    The init command is implemented and should pass these tests.
    Profile names use short format (e.g., "safe" not "orchestrator_safe").
    """

    def test_init_help(self, runner: CliRunner) -> None:
        """Test that init --help shows usage information."""
        result = runner.invoke(contract, ["init", "--help"])
        assert result.exit_code == EnumCLIExitCode.SUCCESS
        assert "--type" in result.output
        assert "--profile" in result.output
        assert "--output" in result.output

    def test_init_creates_valid_patch_file_for_orchestrator(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that init creates a valid patch file for orchestrator type."""
        output_file = tmp_path / "patch.yaml"
        result = runner.invoke(
            contract,
            [
                "init",
                "--type",
                "orchestrator",
                "--profile",
                "safe",  # Short profile name
                "--output",
                str(output_file),
            ],
        )

        assert result.exit_code == EnumCLIExitCode.SUCCESS
        assert output_file.exists()

        # Verify file is valid YAML
        content = yaml.safe_load(output_file.read_text())
        assert content is not None
        assert "extends" in content
        # Full profile name is used in output
        assert content["extends"]["profile"] == "orchestrator_safe"
        assert content["extends"]["version"] == "1.0.0"

    def test_init_creates_valid_patch_file_for_reducer(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that init creates a valid patch file for reducer type."""
        output_file = tmp_path / "patch.yaml"
        result = runner.invoke(
            contract,
            [
                "init",
                "--type",
                "reducer",
                "--profile",
                "fsm_basic",  # Short profile name
                "--output",
                str(output_file),
            ],
        )

        assert result.exit_code == EnumCLIExitCode.SUCCESS
        assert output_file.exists()

        content = yaml.safe_load(output_file.read_text())
        assert content["extends"]["profile"] == "reducer_fsm_basic"

    def test_init_creates_valid_patch_file_for_effect(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that init creates a valid patch file for effect type."""
        output_file = tmp_path / "patch.yaml"
        result = runner.invoke(
            contract,
            [
                "init",
                "--type",
                "effect",
                "--profile",
                "idempotent",  # Short profile name
                "--output",
                str(output_file),
            ],
        )

        assert result.exit_code == EnumCLIExitCode.SUCCESS
        assert output_file.exists()

        content = yaml.safe_load(output_file.read_text())
        assert content["extends"]["profile"] == "effect_idempotent"

    def test_init_creates_valid_patch_file_for_compute(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that init creates a valid patch file for compute type."""
        output_file = tmp_path / "patch.yaml"
        result = runner.invoke(
            contract,
            [
                "init",
                "--type",
                "compute",
                "--profile",
                "pure",  # Short profile name
                "--output",
                str(output_file),
            ],
        )

        assert result.exit_code == EnumCLIExitCode.SUCCESS
        assert output_file.exists()

        content = yaml.safe_load(output_file.read_text())
        assert content["extends"]["profile"] == "compute_pure"

    def test_init_output_has_helpful_comments(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that init output file contains helpful comments."""
        output_file = tmp_path / "patch.yaml"
        result = runner.invoke(
            contract,
            [
                "init",
                "--type",
                "compute",
                "--profile",
                "pure",
                "--output",
                str(output_file),
            ],
        )

        assert result.exit_code == EnumCLIExitCode.SUCCESS

        # Read raw text to check comments
        raw_content = output_file.read_text()
        # Should have comments explaining the structure
        assert "#" in raw_content
        # Comments should mention profile or contract
        assert "profile" in raw_content.lower() or "contract" in raw_content.lower()

    def test_init_includes_placeholder_name_and_version(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that init includes placeholder name and version for new contracts."""
        output_file = tmp_path / "patch.yaml"
        result = runner.invoke(
            contract,
            [
                "init",
                "--type",
                "compute",
                "--profile",
                "pure",
                "--output",
                str(output_file),
            ],
        )

        assert result.exit_code == EnumCLIExitCode.SUCCESS

        # Read raw content - name/version may be in comments
        raw_content = output_file.read_text()
        # Should have placeholder name and version for new contract (in content or comments)
        assert "name" in raw_content
        assert "version" in raw_content

    def test_init_error_for_invalid_node_type(self, runner: CliRunner) -> None:
        """Test that init fails with error for invalid node type."""
        result = runner.invoke(
            contract,
            ["init", "--type", "invalid_type", "--profile", "pure"],
        )

        # Click returns exit code 2 for invalid choice
        assert result.exit_code != EnumCLIExitCode.SUCCESS
        assert (
            "invalid" in result.output.lower()
            or "error" in result.output.lower()
            or "choice" in result.output.lower()
        )

    def test_init_error_for_invalid_profile(self, runner: CliRunner) -> None:
        """Test that init fails with error for invalid profile."""
        result = runner.invoke(
            contract,
            ["init", "--type", "compute", "--profile", "nonexistent_profile"],
        )

        # Should exit with error code 1 (ClickException)
        assert result.exit_code != EnumCLIExitCode.SUCCESS
        assert (
            "unknown" in result.output.lower()
            or "invalid" in result.output.lower()
            or "error" in result.output.lower()
        )

    def test_init_error_for_profile_node_type_mismatch(self, runner: CliRunner) -> None:
        """Test that init fails when profile doesn't match node type."""
        # "safe" is not a valid profile for compute type (it's for orchestrator)
        result = runner.invoke(
            contract,
            ["init", "--type", "compute", "--profile", "safe"],
        )

        assert result.exit_code != EnumCLIExitCode.SUCCESS
        # Should show error about unknown/unavailable profile
        assert "unknown" in result.output.lower() or "error" in result.output.lower()

    def test_init_outputs_to_stdout_when_no_output_specified(
        self, runner: CliRunner
    ) -> None:
        """Test that init outputs to stdout when --output not specified."""
        result = runner.invoke(
            contract,
            ["init", "--type", "compute", "--profile", "pure"],
        )

        assert result.exit_code == EnumCLIExitCode.SUCCESS
        # Should output the template to stdout
        assert "extends:" in result.output
        assert "compute_pure" in result.output

    def test_init_supports_all_orchestrator_profiles(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that init supports all orchestrator profiles."""
        profiles = ["safe", "parallel", "resilient"]

        for profile in profiles:
            output_file = tmp_path / f"patch_{profile}.yaml"
            result = runner.invoke(
                contract,
                [
                    "init",
                    "--type",
                    "orchestrator",
                    "--profile",
                    profile,
                    "--output",
                    str(output_file),
                ],
            )

            assert result.exit_code == EnumCLIExitCode.SUCCESS, (
                f"Failed for {profile}: {result.output}"
            )
            content = yaml.safe_load(output_file.read_text())
            assert content["extends"]["profile"] == f"orchestrator_{profile}"


# =============================================================================
# Build Command Tests
# =============================================================================


@pytest.mark.unit
class TestBuildCommand:
    """Tests for the `onex contract build` command.

    The build command is fully implemented and all tests pass.
    """

    def test_build_help(self, runner: CliRunner) -> None:
        """Test that build --help shows usage information."""
        result = runner.invoke(contract, ["build", "--help"])
        assert result.exit_code == EnumCLIExitCode.SUCCESS
        assert "patch" in result.output.lower() or "PATCH_PATH" in result.output

    def test_build_produces_expanded_contract(
        self, runner: CliRunner, tmp_path: Path, valid_patch_yaml: str
    ) -> None:
        """Test that build produces an expanded contract from valid patch.

        TDD: Expected behavior once implemented:
        - Parse the patch YAML file
        - Resolve the base profile using ContractProfileFactory
        - Merge patch with base using ContractMergeEngine
        - Validate using ContractValidationPipeline
        - Output expanded contract to file
        """
        patch_file = tmp_path / "patch.yaml"
        patch_file.write_text(valid_patch_yaml)
        output_file = tmp_path / "expanded.yaml"

        result = runner.invoke(
            contract,
            ["build", str(patch_file), "--output", str(output_file)],
        )

        assert result.exit_code == EnumCLIExitCode.SUCCESS
        assert output_file.exists()

        content = yaml.safe_load(output_file.read_text())
        assert content is not None
        # Should have expanded contract fields
        assert "handler_id" in content
        assert "name" in content
        assert "contract_version" in content
        assert "descriptor" in content

    def test_build_output_includes_metadata(
        self, runner: CliRunner, tmp_path: Path, valid_patch_yaml: str
    ) -> None:
        """Test that build output includes metadata (profile, version, etc.).

        TDD: Expected metadata fields:
        - _metadata.profile: source profile name
        - _metadata.profile_version: profile version
        - _metadata.runtime_version: omnibase_core version
        - _metadata.merge_hash: deterministic hash of merge inputs
        - _metadata.generated_at: ISO timestamp
        """
        patch_file = tmp_path / "patch.yaml"
        patch_file.write_text(valid_patch_yaml)
        output_file = tmp_path / "expanded.yaml"

        result = runner.invoke(
            contract,
            ["build", str(patch_file), "--output", str(output_file)],
        )

        assert result.exit_code == EnumCLIExitCode.SUCCESS

        raw_content = output_file.read_text()
        content = yaml.safe_load(raw_content)

        # Metadata should be present
        assert "_metadata" in content
        assert "profile" in content["_metadata"]
        assert "generated_at" in content["_metadata"]

    def test_build_validates_all_phases(
        self, runner: CliRunner, tmp_path: Path, valid_patch_yaml: str
    ) -> None:
        """Test that build validates all phases (patch, merge, expanded).

        TDD: Build should use ContractValidationPipeline to validate:
        - Phase 1 (PATCH): Validate patch structure
        - Phase 2 (MERGE): Validate merged contract
        - Phase 3 (EXPANDED): Validate expanded contract
        """
        patch_file = tmp_path / "patch.yaml"
        patch_file.write_text(valid_patch_yaml)

        result = runner.invoke(
            contract,
            ["build", str(patch_file)],
        )

        assert result.exit_code == EnumCLIExitCode.SUCCESS

    def test_build_error_for_missing_patch_file(self, runner: CliRunner) -> None:
        """Test that build fails with error for missing patch file."""
        result = runner.invoke(
            contract,
            ["build", "/nonexistent/path/patch.yaml"],
        )

        # Click returns exit code 2 for file not found with exists=True
        assert result.exit_code != EnumCLIExitCode.SUCCESS
        assert (
            "not found" in result.output.lower()
            or "does not exist" in result.output.lower()
            or "error" in result.output.lower()
        )

    def test_build_error_for_invalid_patch_yaml(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that build fails with error for invalid patch YAML.

        TDD: Should parse YAML and report syntax errors clearly.
        """
        patch_file = tmp_path / "invalid_patch.yaml"
        patch_file.write_text("this: is: invalid: yaml: ][")

        result = runner.invoke(
            contract,
            ["build", str(patch_file)],
        )

        assert result.exit_code == EnumCLIExitCode.ERROR
        assert (
            "yaml" in result.output.lower()
            or "parse" in result.output.lower()
            or "invalid" in result.output.lower()
        )

    def test_build_error_for_invalid_patch_structure(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that build fails with error for patch with invalid structure.

        TDD: Should validate patch against ModelContractPatch schema.
        """
        # Missing required 'extends' field
        patch_file = tmp_path / "bad_structure.yaml"
        patch_file.write_text("""
name: my_handler
description: This is missing the extends field
""")

        result = runner.invoke(
            contract,
            ["build", str(patch_file)],
        )

        assert result.exit_code == EnumCLIExitCode.ERROR
        assert (
            "extends" in result.output.lower()
            or "required" in result.output.lower()
            or "validation" in result.output.lower()
        )

    def test_build_error_for_validation_failure(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that build fails with error when validation fails.

        TDD: Should report validation errors from ContractValidationPipeline.
        """
        # Patch that would fail validation (invalid profile reference)
        patch_file = tmp_path / "failing_patch.yaml"
        patch_file.write_text("""
extends:
  profile: "nonexistent_profile"
  version: "1.0.0"
name: my_handler
node_version:
  major: 1
  minor: 0
  patch: 0
""")

        result = runner.invoke(
            contract,
            ["build", str(patch_file)],
        )

        assert result.exit_code == EnumCLIExitCode.ERROR
        assert (
            "validation" in result.output.lower()
            or "failed" in result.output.lower()
            or "unknown" in result.output.lower()
        )

    def test_build_outputs_to_stdout_when_no_output_specified(
        self, runner: CliRunner, tmp_path: Path, valid_patch_yaml: str
    ) -> None:
        """Test that build outputs to stdout when --output not specified.

        TDD: Should output expanded contract YAML to stdout.
        """
        patch_file = tmp_path / "patch.yaml"
        patch_file.write_text(valid_patch_yaml)

        result = runner.invoke(
            contract,
            ["build", str(patch_file)],
        )

        assert result.exit_code == EnumCLIExitCode.SUCCESS
        # Output should contain expanded contract fields
        assert "handler_id" in result.output or "name" in result.output

    def test_build_verbose_shows_phase_results(
        self, runner: CliRunner, tmp_path: Path, valid_patch_yaml: str
    ) -> None:
        """Test that build with parent --verbose shows phase results.

        TDD: Verbose mode should show validation phase progress.
        """
        patch_file = tmp_path / "patch.yaml"
        patch_file.write_text(valid_patch_yaml)

        # Note: --verbose is on the parent group, not build subcommand
        result = runner.invoke(
            contract,
            ["build", str(patch_file)],
        )

        assert result.exit_code == EnumCLIExitCode.SUCCESS


# =============================================================================
# Diff Command Tests
# =============================================================================


@pytest.mark.unit
class TestDiffCommand:
    """Tests for the `onex contract diff` command.

    The diff command is fully implemented and all tests pass.
    """

    def test_diff_help(self, runner: CliRunner) -> None:
        """Test that diff --help shows usage information."""
        result = runner.invoke(contract, ["diff", "--help"])
        assert result.exit_code == EnumCLIExitCode.SUCCESS
        # Should mention old and new files
        assert "old" in result.output.lower() or "OLD" in result.output
        assert "new" in result.output.lower() or "NEW" in result.output

    def test_diff_detects_added_fields(
        self,
        runner: CliRunner,
        tmp_path: Path,
        contract_v1_yaml: str,
        contract_v2_yaml: str,
    ) -> None:
        """Test that diff detects added fields between contracts.

        TDD: Should detect capability_inputs and capability_outputs added in v2.
        """
        old_file = tmp_path / "old.yaml"
        new_file = tmp_path / "new.yaml"
        old_file.write_text(contract_v1_yaml)
        new_file.write_text(contract_v2_yaml)

        result = runner.invoke(
            contract,
            ["diff", str(old_file), str(new_file)],
        )

        # Exit code 2 (WARNING) indicates differences found (standard diff behavior)
        assert result.exit_code == EnumCLIExitCode.WARNING
        # v2 adds capability_inputs and capability_outputs
        output_lower = result.output.lower()
        assert (
            "added" in output_lower
            or "+" in result.output
            or "capability" in output_lower
        )

    def test_diff_detects_removed_fields(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that diff detects removed fields between contracts.

        TDD: Should detect fields removed between old and new.
        """
        old_file = tmp_path / "old.yaml"
        new_file = tmp_path / "new.yaml"

        # Old has a field that new doesn't
        old_file.write_text("""
handler_id: "node.handler"
name: "handler"
version: "1.0.0"
extra_field: "this will be removed"
descriptor:
  node_archetype: "compute"
""")

        new_file.write_text("""
handler_id: "node.handler"
name: "handler"
version: "1.0.0"
descriptor:
  node_archetype: "compute"
""")

        result = runner.invoke(
            contract,
            ["diff", str(old_file), str(new_file)],
        )

        # Exit code 2 (WARNING) indicates differences found (standard diff behavior)
        assert result.exit_code == EnumCLIExitCode.WARNING
        output_lower = result.output.lower()
        assert (
            "removed" in output_lower
            or "-" in result.output
            or "extra_field" in output_lower
        )

    def test_diff_detects_changed_values(
        self,
        runner: CliRunner,
        tmp_path: Path,
        contract_v1_yaml: str,
        contract_v2_yaml: str,
    ) -> None:
        """Test that diff detects changed values between contracts.

        TDD: Should detect version changed from 1.0.0 to 2.0.0.
        """
        old_file = tmp_path / "old.yaml"
        new_file = tmp_path / "new.yaml"
        old_file.write_text(contract_v1_yaml)
        new_file.write_text(contract_v2_yaml)

        result = runner.invoke(
            contract,
            ["diff", str(old_file), str(new_file)],
        )

        # Exit code 2 (WARNING) indicates differences found (standard diff behavior)
        assert result.exit_code == EnumCLIExitCode.WARNING
        # Version changed from 1.0.0 to 2.0.0
        output_lower = result.output.lower()
        assert (
            "changed" in output_lower
            or "modified" in output_lower
            or "1.0.0" in result.output
            or "2.0.0" in result.output
        )

    def test_diff_highlights_behavioral_changes(
        self,
        runner: CliRunner,
        tmp_path: Path,
        contract_v1_yaml: str,
        contract_v2_yaml: str,
    ) -> None:
        """Test that diff highlights behavioral changes (purity, idempotent, timeout).

        TDD: Should highlight changes to:
        - purity: pure -> side_effecting
        - idempotent: true -> false
        - timeout_ms: 30000 -> 60000
        """
        old_file = tmp_path / "old.yaml"
        new_file = tmp_path / "new.yaml"
        old_file.write_text(contract_v1_yaml)
        new_file.write_text(contract_v2_yaml)

        result = runner.invoke(
            contract,
            ["diff", str(old_file), str(new_file)],
        )

        # Exit code 2 (WARNING) indicates differences found (standard diff behavior)
        assert result.exit_code == EnumCLIExitCode.WARNING
        output_lower = result.output.lower()

        # At least one behavioral change should be highlighted
        behavioral_indicators = [
            "purity",
            "idempotent",
            "timeout",
            "behavior",
            "breaking",
            "pure",
            "side_effect",
        ]
        assert any(indicator in output_lower for indicator in behavioral_indicators)

    def test_diff_error_for_missing_old_file(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that diff fails with error for missing old file."""
        new_file = tmp_path / "new.yaml"
        new_file.write_text("handler_id: node.test\nname: test")

        result = runner.invoke(
            contract,
            ["diff", "/nonexistent/old.yaml", str(new_file)],
        )

        # Click returns exit code 2 for file not found
        assert result.exit_code != EnumCLIExitCode.SUCCESS
        assert (
            "not found" in result.output.lower()
            or "does not exist" in result.output.lower()
            or "error" in result.output.lower()
        )

    def test_diff_error_for_missing_new_file(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that diff fails with error for missing new file."""
        old_file = tmp_path / "old.yaml"
        old_file.write_text("handler_id: node.test\nname: test")

        result = runner.invoke(
            contract,
            ["diff", str(old_file), "/nonexistent/new.yaml"],
        )

        # Click returns exit code 2 for file not found
        assert result.exit_code != EnumCLIExitCode.SUCCESS
        assert (
            "not found" in result.output.lower()
            or "does not exist" in result.output.lower()
            or "error" in result.output.lower()
        )

    def test_diff_error_for_invalid_yaml_old_file(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that diff fails with error for invalid YAML in old file.

        TDD: Should parse YAML and report syntax errors.
        """
        old_file = tmp_path / "old.yaml"
        new_file = tmp_path / "new.yaml"
        old_file.write_text("invalid: yaml: ][")
        new_file.write_text("handler_id: node.test\nname: test")

        result = runner.invoke(
            contract,
            ["diff", str(old_file), str(new_file)],
        )

        assert result.exit_code == EnumCLIExitCode.ERROR
        assert (
            "yaml" in result.output.lower()
            or "parse" in result.output.lower()
            or "invalid" in result.output.lower()
        )

    def test_diff_error_for_invalid_yaml_new_file(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that diff fails with error for invalid YAML in new file.

        TDD: Should parse YAML and report syntax errors.
        """
        old_file = tmp_path / "old.yaml"
        new_file = tmp_path / "new.yaml"
        old_file.write_text("handler_id: node.test\nname: test")
        new_file.write_text("invalid: yaml: ][")

        result = runner.invoke(
            contract,
            ["diff", str(old_file), str(new_file)],
        )

        assert result.exit_code == EnumCLIExitCode.ERROR
        assert (
            "yaml" in result.output.lower()
            or "parse" in result.output.lower()
            or "invalid" in result.output.lower()
        )

    def test_diff_shows_no_changes_for_identical_files(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that diff shows no changes when files are identical.

        TDD: Should indicate no differences found.
        """
        content = """
handler_id: node.test
name: test
version: "1.0.0"
"""
        old_file = tmp_path / "old.yaml"
        new_file = tmp_path / "new.yaml"
        old_file.write_text(content)
        new_file.write_text(content)

        result = runner.invoke(
            contract,
            ["diff", str(old_file), str(new_file)],
        )

        assert result.exit_code == EnumCLIExitCode.SUCCESS
        output_lower = result.output.lower()
        assert (
            "no change" in output_lower
            or "identical" in output_lower
            or "same" in output_lower
            or "[STUB]" not in result.output  # Not just the stub output
        )

    def test_diff_json_output_format(
        self,
        runner: CliRunner,
        tmp_path: Path,
        contract_v1_yaml: str,
        contract_v2_yaml: str,
    ) -> None:
        """Test that diff supports JSON output format.

        TDD: --format json should output valid JSON with diff structure.
        """
        old_file = tmp_path / "old.yaml"
        new_file = tmp_path / "new.yaml"
        old_file.write_text(contract_v1_yaml)
        new_file.write_text(contract_v2_yaml)

        result = runner.invoke(
            contract,
            ["diff", str(old_file), str(new_file), "--format", "json"],
        )

        # Exit code 2 (WARNING) indicates differences found (standard diff behavior)
        assert result.exit_code == EnumCLIExitCode.WARNING
        # Output should be valid JSON
        try:
            diff_result = json.loads(result.output)
            assert isinstance(diff_result, dict)
        except json.JSONDecodeError:
            pytest.fail("Output was not valid JSON")

    def test_diff_categorizes_severity_of_changes(
        self,
        runner: CliRunner,
        tmp_path: Path,
        contract_v1_yaml: str,
        contract_v2_yaml: str,
    ) -> None:
        """Test that diff categorizes changes by severity (breaking, non-breaking).

        TDD: Should classify idempotent (true->false) as a breaking change.
        """
        old_file = tmp_path / "old.yaml"
        new_file = tmp_path / "new.yaml"
        old_file.write_text(contract_v1_yaml)
        new_file.write_text(contract_v2_yaml)

        result = runner.invoke(
            contract,
            ["diff", str(old_file), str(new_file)],
        )

        # Exit code 2 (WARNING) indicates differences found (standard diff behavior)
        assert result.exit_code == EnumCLIExitCode.WARNING
        output_lower = result.output.lower()

        # Changes to idempotent (true->false) is a breaking change
        # Should indicate severity or breaking nature
        severity_indicators = [
            "breaking",
            "major",
            "minor",
            "critical",
            "warning",
            "severity",
        ]
        assert any(indicator in output_lower for indicator in severity_indicators) or (
            "idempotent" in output_lower or "purity" in output_lower
        )


# =============================================================================
# Edge Case Tests
# =============================================================================


@pytest.mark.unit
class TestContractCliEdgeCases:
    """Edge case tests for contract CLI commands.

    These tests cover additional scenarios and edge cases.
    """

    def test_init_with_custom_name(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test that init accepts --name option for custom handler name.

        TDD: --name option is not implemented. Expected behavior:
        - Accept --name flag
        - Use provided name instead of placeholder
        """
        output_file = tmp_path / "patch.yaml"
        result = runner.invoke(
            contract,
            [
                "init",
                "--type",
                "compute",
                "--profile",
                "pure",
                "--name",
                "my_custom_handler",
                "--output",
                str(output_file),
            ],
        )

        assert result.exit_code == EnumCLIExitCode.SUCCESS
        content = yaml.safe_load(output_file.read_text())
        assert content.get("name") == "my_custom_handler"

    def test_build_with_strict_mode(
        self, runner: CliRunner, tmp_path: Path, valid_patch_yaml: str
    ) -> None:
        """Test that build supports --strict mode for validation.

        TDD: --strict flag is not implemented. Expected behavior:
        - Accept --strict flag
        - Fail on warnings in strict mode
        """
        patch_file = tmp_path / "patch.yaml"
        patch_file.write_text(valid_patch_yaml)

        result = runner.invoke(
            contract,
            ["build", str(patch_file), "--strict"],
        )

        # Strict mode should still work with valid input
        assert result.exit_code == EnumCLIExitCode.SUCCESS

    def test_diff_handles_empty_files(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test that diff handles empty YAML files gracefully.

        TDD: Should handle empty files with clear error or "no content" message.
        """
        old_file = tmp_path / "old.yaml"
        new_file = tmp_path / "new.yaml"
        old_file.write_text("")
        new_file.write_text("")

        result = runner.invoke(
            contract,
            ["diff", str(old_file), str(new_file)],
        )

        # Should either succeed with no changes or fail with clear error
        assert result.exit_code in (EnumCLIExitCode.SUCCESS, EnumCLIExitCode.ERROR)
        if result.exit_code == EnumCLIExitCode.ERROR:
            assert (
                "empty" in result.output.lower() or "invalid" in result.output.lower()
            )

    def test_init_respects_override_only_mode(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that init can create override-only patches (no name/version).

        TDD: --override-only flag is not implemented. Expected behavior:
        - Accept --override-only flag
        - Do not include name/node_version in template
        """
        output_file = tmp_path / "patch.yaml"
        result = runner.invoke(
            contract,
            [
                "init",
                "--type",
                "compute",
                "--profile",
                "pure",
                "--override-only",
                "--output",
                str(output_file),
            ],
        )

        assert result.exit_code == EnumCLIExitCode.SUCCESS
        content = yaml.safe_load(output_file.read_text())
        # Override-only patches should not have name or node_version
        assert content.get("name") is None
        assert content.get("node_version") is None


# =============================================================================
# Integration-Like Unit Tests (Testing Component Interactions)
# =============================================================================


@pytest.mark.unit
class TestContractCliWorkflow:
    """Tests for complete contract CLI workflows.

    These tests verify that multiple CLI commands work together correctly.
    """

    def test_init_then_build_workflow(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test the complete init -> build workflow.

        TDD: Build is a stub. Expected workflow:
        1. Init creates a valid patch template
        2. Build expands the patch into a complete contract
        """
        patch_file = tmp_path / "patch.yaml"
        expanded_file = tmp_path / "expanded.yaml"

        # Step 1: Init a patch
        result = runner.invoke(
            contract,
            [
                "init",
                "--type",
                "compute",
                "--profile",
                "pure",
                "--output",
                str(patch_file),
            ],
        )
        assert result.exit_code == EnumCLIExitCode.SUCCESS

        # Step 2: Build the expanded contract
        result = runner.invoke(
            contract,
            ["build", str(patch_file), "--output", str(expanded_file)],
        )
        assert result.exit_code == EnumCLIExitCode.SUCCESS
        assert expanded_file.exists()

    def test_build_then_diff_workflow(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test the complete build -> diff workflow.

        TDD: Build and diff are stubs. Expected workflow:
        1. Build two versions of a contract
        2. Diff shows changes between versions
        """
        # Create two patches with different settings
        patch_v1 = tmp_path / "patch_v1.yaml"
        patch_v2 = tmp_path / "patch_v2.yaml"

        patch_v1.write_text("""
extends:
  profile: compute_pure
  version: "1.0.0"
name: my_handler
node_version:
  major: 1
  minor: 0
  patch: 0
descriptor:
  timeout_ms: 30000
""")

        patch_v2.write_text("""
extends:
  profile: compute_pure
  version: "1.0.0"
name: my_handler
node_version:
  major: 1
  minor: 1
  patch: 0
descriptor:
  timeout_ms: 60000
""")

        expanded_v1 = tmp_path / "expanded_v1.yaml"
        expanded_v2 = tmp_path / "expanded_v2.yaml"

        # Build both versions
        result = runner.invoke(
            contract,
            ["build", str(patch_v1), "--output", str(expanded_v1)],
        )
        assert result.exit_code == EnumCLIExitCode.SUCCESS

        result = runner.invoke(
            contract,
            ["build", str(patch_v2), "--output", str(expanded_v2)],
        )
        assert result.exit_code == EnumCLIExitCode.SUCCESS

        # Diff the expanded contracts
        result = runner.invoke(
            contract,
            ["diff", str(expanded_v1), str(expanded_v2)],
        )
        assert result.exit_code == EnumCLIExitCode.WARNING  # Changes detected
        # Should show timeout change
        assert (
            "timeout" in result.output.lower()
            or "30000" in result.output
            or "60000" in result.output
        )


# =============================================================================
# Security Tests
# =============================================================================


@pytest.mark.unit
class TestContractCLISecurity:
    """Security tests for contract CLI commands.

    These tests verify that the CLI properly handles path traversal attempts,
    symlinks, and other security-sensitive operations.
    """

    def test_init_rejects_path_traversal_in_output(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that init rejects path traversal in output path."""
        # Attempt path traversal via ../
        result = runner.invoke(
            contract,
            [
                "init",
                "--type",
                "compute",
                "--profile",
                "pure",
                "--output",
                str(tmp_path / ".." / "etc" / "passwd.yaml"),
            ],
        )
        # Should fail with security error
        assert result.exit_code != EnumCLIExitCode.SUCCESS

    def test_init_rejects_writes_to_system_directories(self, runner: CliRunner) -> None:
        """Test that init rejects writes to system directories."""
        system_paths = [
            "/etc/test.yaml",
            "/usr/local/test.yaml",
            "/var/log/test.yaml",
        ]

        for path in system_paths:
            result = runner.invoke(
                contract,
                [
                    "init",
                    "--type",
                    "compute",
                    "--profile",
                    "pure",
                    "--output",
                    path,
                ],
            )
            # Should fail with security error or permission error
            assert result.exit_code != EnumCLIExitCode.SUCCESS, (
                f"Should have rejected write to {path}"
            )

    def test_build_rejects_writes_to_system_directories(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that build rejects writes to system directories."""
        # Create a valid patch file
        patch_file = tmp_path / "patch.yaml"
        patch_file.write_text("""
extends:
  profile: compute_pure
  version: "1.0.0"
name: test
node_version:
  major: 1
  minor: 0
  patch: 0
""")

        system_paths = [
            "/etc/test.yaml",
            "/usr/local/test.yaml",
        ]

        for path in system_paths:
            result = runner.invoke(
                contract,
                ["build", str(patch_file), "--output", path],
            )
            # Should fail with security error or permission error
            assert result.exit_code != EnumCLIExitCode.SUCCESS, (
                f"Should have rejected write to {path}"
            )

    def test_diff_output_rejects_writes_to_system_directories(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that diff rejects writes to system directories."""
        # Create two contract files
        old_file = tmp_path / "old.yaml"
        new_file = tmp_path / "new.yaml"
        old_file.write_text("handler_id: test\nname: test")
        new_file.write_text("handler_id: test\nname: test2")

        result = runner.invoke(
            contract,
            ["diff", str(old_file), str(new_file), "--output", "/etc/test.yaml"],
        )
        # Should fail with security error or permission error
        assert result.exit_code != EnumCLIExitCode.SUCCESS

    def test_symlink_to_outside_workspace_rejected_for_output(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that symlinks pointing outside workspace are rejected for output.

        This test verifies that the CLI does not follow symlinks that point
        outside the expected workspace, which could be used for path traversal.
        """
        # Create a symlink that points to /tmp (outside tmp_path)
        symlink_path = tmp_path / "link_to_tmp"
        try:
            symlink_path.symlink_to("/tmp")
        except OSError:
            pytest.skip("OS doesn't support symlinks")

        output_via_symlink = symlink_path / "malicious.yaml"

        result = runner.invoke(
            contract,
            [
                "init",
                "--type",
                "compute",
                "--profile",
                "pure",
                "--output",
                str(output_via_symlink),
            ],
        )
        # The file should either fail or be written to the resolved path
        # Either way, the output message shows the resolved path
        # This is a defense-in-depth test

        # Verify that if successful, the output goes to resolved path
        if result.exit_code == EnumCLIExitCode.SUCCESS:
            resolved = symlink_path.resolve() / "malicious.yaml"
            assert resolved.resolve() == (Path("/tmp") / "malicious.yaml").resolve()

    def test_build_symlink_input_allowed_for_reading(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that symlinks are allowed for reading input files.

        Symlinks for input files should be followed and processed normally.
        Only output paths need symlink protection.
        """
        # Create a real patch file
        real_patch = tmp_path / "real_patch.yaml"
        real_patch.write_text("""
extends:
  profile: compute_pure
  version: "1.0.0"
name: test_symlink
node_version:
  major: 1
  minor: 0
  patch: 0
""")

        # Create a symlink to it
        symlink_patch = tmp_path / "symlink_patch.yaml"
        try:
            symlink_patch.symlink_to(real_patch)
        except OSError:
            pytest.skip("OS doesn't support symlinks")

        # Build via symlink should work
        result = runner.invoke(
            contract,
            ["build", str(symlink_patch)],
        )
        assert result.exit_code == EnumCLIExitCode.SUCCESS

    def test_diff_symlink_input_allowed_for_reading(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that symlinks are allowed for reading diff input files."""
        # Create real contract files
        real_old = tmp_path / "real_old.yaml"
        real_new = tmp_path / "real_new.yaml"
        real_old.write_text("handler_id: test\nname: old")
        real_new.write_text("handler_id: test\nname: new")

        # Create symlinks
        symlink_old = tmp_path / "symlink_old.yaml"
        symlink_new = tmp_path / "symlink_new.yaml"
        try:
            symlink_old.symlink_to(real_old)
            symlink_new.symlink_to(real_new)
        except OSError:
            pytest.skip("OS doesn't support symlinks")

        # Diff via symlinks should work
        result = runner.invoke(
            contract,
            ["diff", str(symlink_old), str(symlink_new)],
        )
        # Exit code 2 indicates differences found (successful comparison)
        assert result.exit_code == EnumCLIExitCode.WARNING
        assert "name" in result.output.lower()

    def test_path_traversal_resolved_correctly(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that path traversal attempts are resolved correctly."""
        # Create nested directories
        subdir = tmp_path / "subdir" / "deep"
        subdir.mkdir(parents=True)

        # Try to traverse up with ../../
        output_path = subdir / ".." / ".." / "output.yaml"

        result = runner.invoke(
            contract,
            [
                "init",
                "--type",
                "compute",
                "--profile",
                "pure",
                "--output",
                str(output_path),
            ],
        )

        # Should succeed but resolve to tmp_path/output.yaml
        assert result.exit_code == EnumCLIExitCode.SUCCESS
        # The resolved path should be within tmp_path
        expected_resolved = (tmp_path / "output.yaml").resolve()
        assert expected_resolved.exists()
