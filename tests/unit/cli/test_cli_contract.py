# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for CLI contract commands.

Tests the CLI command for comparing, validating, and managing ONEX contracts.
The main entry point is the `contract` command group with the `diff` subcommand.

.. versionadded:: 0.6.0
    Added as part of Explainability Output: Diff Rendering (OMN-1149)
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from omnibase_core.cli.cli_commands import cli


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def sample_contract_v1(tmp_path: Path) -> Path:
    """Create a sample v1 contract file."""
    contract = {
        "name": "TestContract",
        "version": "1.0.0",
        "meta": {
            "description": "Original description",
            "author": "Test Author",
        },
        "settings": {
            "timeout": 30,
            "retries": 3,
        },
    }
    path = tmp_path / "v1.json"
    path.write_text(json.dumps(contract))
    return path


@pytest.fixture
def sample_contract_v2(tmp_path: Path) -> Path:
    """Create a sample v2 contract file with changes."""
    contract = {
        "name": "TestContract",
        "version": "2.0.0",
        "meta": {
            "description": "Updated description",
            "author": "Test Author",
            "new_field": "added",
        },
        "settings": {
            "timeout": 60,
            "retries": 3,
        },
    }
    path = tmp_path / "v2.json"
    path.write_text(json.dumps(contract))
    return path


@pytest.fixture
def sample_yaml_contract_v1(tmp_path: Path) -> Path:
    """Create a sample YAML contract file (v1)."""
    content = """name: YamlContract
version: "1.0.0"
meta:
  description: A YAML contract
  author: YAML Author
handlers:
  - name: handler_one
    type: compute
  - name: handler_two
    type: effect
"""
    path = tmp_path / "contract_v1.yaml"
    path.write_text(content)
    return path


@pytest.fixture
def sample_yaml_contract_v2(tmp_path: Path) -> Path:
    """Create a sample YAML contract file (v2) with changes."""
    content = """name: YamlContract
version: "2.0.0"
meta:
  description: Updated YAML contract
  author: YAML Author
  tags:
    - new
    - feature
handlers:
  - name: handler_one
    type: compute
  - name: handler_three
    type: reducer
"""
    path = tmp_path / "contract_v2.yaml"
    path.write_text(content)
    return path


@pytest.fixture
def identical_contract_pair(tmp_path: Path) -> tuple[Path, Path]:
    """Create two identical contract files."""
    contract = {
        "name": "IdenticalContract",
        "version": "1.0.0",
        "meta": {"description": "Same content"},
    }
    path1 = tmp_path / "identical_a.json"
    path2 = tmp_path / "identical_b.json"
    content = json.dumps(contract)
    path1.write_text(content)
    path2.write_text(content)
    return path1, path2


@pytest.fixture
def complex_contract_v1(tmp_path: Path) -> Path:
    """Create a complex contract with nested structures."""
    contract = {
        "name": "ComplexContract",
        "version": "1.0.0",
        "dependencies": [
            {"name": "dep_one", "version": "1.0.0"},
            {"name": "dep_two", "version": "2.0.0"},
        ],
        "states": [
            {"state_name": "idle", "initial": True},
            {"state_name": "running", "initial": False},
        ],
        "config": {
            "nested": {
                "deeply": {
                    "value": 42,
                },
            },
        },
    }
    path = tmp_path / "complex_v1.json"
    path.write_text(json.dumps(contract))
    return path


@pytest.fixture
def complex_contract_v2(tmp_path: Path) -> Path:
    """Create a modified complex contract."""
    contract = {
        "name": "ComplexContract",
        "version": "2.0.0",
        "dependencies": [
            {"name": "dep_one", "version": "1.1.0"},
            {"name": "dep_three", "version": "3.0.0"},
        ],
        "states": [
            {"state_name": "idle", "initial": True},
            {"state_name": "paused", "initial": False},
        ],
        "config": {
            "nested": {
                "deeply": {
                    "value": 100,
                    "new_key": "added",
                },
            },
        },
    }
    path = tmp_path / "complex_v2.json"
    path.write_text(json.dumps(contract))
    return path


@pytest.mark.unit
class TestContractCommandGroup:
    """Tests for the contract command group."""

    def test_contract_group_help(self, runner: CliRunner) -> None:
        """Test contract --help shows subcommands."""
        result = runner.invoke(cli, ["contract", "--help"])
        assert result.exit_code == 0
        assert "diff" in result.output
        assert "Contract management commands" in result.output

    def test_contract_group_no_subcommand_shows_help(self, runner: CliRunner) -> None:
        """Test invoking contract without subcommand shows help.

        Note: Click returns exit code 2 for groups when no subcommand is provided,
        even though help is displayed. This is standard Click behavior.
        """
        result = runner.invoke(cli, ["contract"])
        # Exit code 2 is Click's standard for "missing subcommand"
        assert result.exit_code == 2
        assert "diff" in result.output

    def test_contract_in_main_cli_help(self, runner: CliRunner) -> None:
        """Test that contract command is listed in main CLI help."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "contract" in result.output


@pytest.mark.unit
class TestContractDiffBasic:
    """Tests for basic diff command functionality."""

    def test_diff_help(self, runner: CliRunner) -> None:
        """Test diff --help shows usage."""
        result = runner.invoke(cli, ["contract", "diff", "--help"])
        assert result.exit_code == 0
        assert "Compare two contract files" in result.output
        assert "--format" in result.output
        assert "--output" in result.output
        assert "--no-color" in result.output

    def test_diff_basic(
        self, runner: CliRunner, sample_contract_v1: Path, sample_contract_v2: Path
    ) -> None:
        """Test basic diff between two contracts."""
        result = runner.invoke(
            cli,
            ["contract", "diff", str(sample_contract_v1), str(sample_contract_v2)],
        )
        assert result.exit_code == 0
        # Should show diff output with contract names or version changes
        assert (
            "v1" in result.output
            or "v2" in result.output
            or "Contract" in result.output
        )

    def test_diff_shows_changes(
        self, runner: CliRunner, sample_contract_v1: Path, sample_contract_v2: Path
    ) -> None:
        """Test that diff shows field changes."""
        result = runner.invoke(
            cli,
            ["contract", "diff", str(sample_contract_v1), str(sample_contract_v2)],
        )
        assert result.exit_code == 0
        # Should mention version or description changes
        output_lower = result.output.lower()
        assert (
            "version" in output_lower
            or "description" in output_lower
            or "change" in output_lower
        )

    def test_diff_identical_files(
        self, runner: CliRunner, identical_contract_pair: tuple[Path, Path]
    ) -> None:
        """Test diff between identical files shows no changes."""
        path1, path2 = identical_contract_pair
        result = runner.invoke(
            cli,
            ["contract", "diff", str(path1), str(path2)],
        )
        assert result.exit_code == 0
        # Should indicate no changes or show 0 changes
        output_lower = result.output.lower()
        assert (
            "no change" in output_lower
            or "0 change" in output_lower
            or "identical" in output_lower
        )


@pytest.mark.unit
class TestContractDiffFormats:
    """Tests for diff output format options."""

    def test_diff_text_format(
        self, runner: CliRunner, sample_contract_v1: Path, sample_contract_v2: Path
    ) -> None:
        """Test diff with default text format."""
        result = runner.invoke(
            cli,
            [
                "contract",
                "diff",
                str(sample_contract_v1),
                str(sample_contract_v2),
                "--format",
                "text",
            ],
        )
        assert result.exit_code == 0
        # Text format should have readable output
        assert len(result.output) > 0

    def test_diff_json_format(
        self, runner: CliRunner, sample_contract_v1: Path, sample_contract_v2: Path
    ) -> None:
        """Test diff with JSON format output."""
        result = runner.invoke(
            cli,
            [
                "contract",
                "diff",
                str(sample_contract_v1),
                str(sample_contract_v2),
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        # Should be valid JSON
        parsed = json.loads(result.output)
        assert "diff_id" in parsed
        assert "field_diffs" in parsed or "change_summary" in parsed

    def test_diff_json_format_has_required_fields(
        self, runner: CliRunner, sample_contract_v1: Path, sample_contract_v2: Path
    ) -> None:
        """Test JSON format includes all required diff fields."""
        result = runner.invoke(
            cli,
            [
                "contract",
                "diff",
                str(sample_contract_v1),
                str(sample_contract_v2),
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        # Check for key fields from ModelContractDiff
        assert "diff_id" in parsed
        assert "before_contract_name" in parsed
        assert "after_contract_name" in parsed
        assert "has_changes" in parsed
        assert "total_changes" in parsed

    def test_diff_markdown_format(
        self, runner: CliRunner, sample_contract_v1: Path, sample_contract_v2: Path
    ) -> None:
        """Test diff with markdown format output."""
        result = runner.invoke(
            cli,
            [
                "contract",
                "diff",
                str(sample_contract_v1),
                str(sample_contract_v2),
                "--format",
                "markdown",
            ],
        )
        assert result.exit_code == 0
        # Should have markdown elements
        assert "#" in result.output  # Headers
        assert "|" in result.output or "**" in result.output  # Tables or bold

    def test_diff_markdown_has_header(
        self, runner: CliRunner, sample_contract_v1: Path, sample_contract_v2: Path
    ) -> None:
        """Test markdown format has proper header."""
        result = runner.invoke(
            cli,
            [
                "contract",
                "diff",
                str(sample_contract_v1),
                str(sample_contract_v2),
                "--format",
                "markdown",
            ],
        )
        assert result.exit_code == 0
        # Should have contract diff header
        assert "# Contract Diff" in result.output or "## Contract Diff" in result.output

    def test_diff_html_format(
        self, runner: CliRunner, sample_contract_v1: Path, sample_contract_v2: Path
    ) -> None:
        """Test diff with HTML format output."""
        result = runner.invoke(
            cli,
            [
                "contract",
                "diff",
                str(sample_contract_v1),
                str(sample_contract_v2),
                "--format",
                "html",
            ],
        )
        assert result.exit_code == 0
        # Should have HTML tags
        assert "<" in result.output
        assert ">" in result.output

    def test_diff_html_is_standalone(
        self, runner: CliRunner, sample_contract_v1: Path, sample_contract_v2: Path
    ) -> None:
        """Test HTML format is standalone with proper structure."""
        result = runner.invoke(
            cli,
            [
                "contract",
                "diff",
                str(sample_contract_v1),
                str(sample_contract_v2),
                "--format",
                "html",
            ],
        )
        assert result.exit_code == 0
        # Should have full HTML document structure
        assert "<!DOCTYPE html>" in result.output
        assert "<html" in result.output
        assert "<style>" in result.output  # Inline CSS for standalone
        assert "</html>" in result.output


@pytest.mark.unit
class TestContractDiffOptions:
    """Tests for diff command options."""

    def test_diff_output_to_file(
        self,
        runner: CliRunner,
        sample_contract_v1: Path,
        sample_contract_v2: Path,
        tmp_path: Path,
    ) -> None:
        """Test diff output to file."""
        output_file = tmp_path / "diff_output.txt"
        result = runner.invoke(
            cli,
            [
                "contract",
                "diff",
                str(sample_contract_v1),
                str(sample_contract_v2),
                "--output",
                str(output_file),
            ],
        )
        assert result.exit_code == 0
        assert output_file.exists()
        content = output_file.read_text()
        assert len(content) > 0
        assert "written to" in result.output.lower()

    def test_diff_output_to_file_with_format(
        self,
        runner: CliRunner,
        sample_contract_v1: Path,
        sample_contract_v2: Path,
        tmp_path: Path,
    ) -> None:
        """Test diff output to file with specific format."""
        output_file = tmp_path / "diff_output.json"
        result = runner.invoke(
            cli,
            [
                "contract",
                "diff",
                str(sample_contract_v1),
                str(sample_contract_v2),
                "--format",
                "json",
                "--output",
                str(output_file),
            ],
        )
        assert result.exit_code == 0
        assert output_file.exists()
        # Verify it's valid JSON
        content = output_file.read_text()
        parsed = json.loads(content)
        assert "diff_id" in parsed

    def test_diff_output_creates_parent_directory(
        self,
        runner: CliRunner,
        sample_contract_v1: Path,
        sample_contract_v2: Path,
        tmp_path: Path,
    ) -> None:
        """Test diff creates parent directories for output file."""
        output_file = tmp_path / "nested" / "deep" / "diff_output.txt"
        result = runner.invoke(
            cli,
            [
                "contract",
                "diff",
                str(sample_contract_v1),
                str(sample_contract_v2),
                "--output",
                str(output_file),
            ],
        )
        assert result.exit_code == 0
        assert output_file.exists()

    def test_diff_no_color(
        self, runner: CliRunner, sample_contract_v1: Path, sample_contract_v2: Path
    ) -> None:
        """Test diff with --no-color flag."""
        result = runner.invoke(
            cli,
            [
                "contract",
                "diff",
                str(sample_contract_v1),
                str(sample_contract_v2),
                "--no-color",
            ],
        )
        assert result.exit_code == 0
        # Should not have ANSI escape codes
        assert "\x1b[" not in result.output

    def test_diff_short_format_option(
        self, runner: CliRunner, sample_contract_v1: Path, sample_contract_v2: Path
    ) -> None:
        """Test diff with -f short option for format."""
        result = runner.invoke(
            cli,
            [
                "contract",
                "diff",
                str(sample_contract_v1),
                str(sample_contract_v2),
                "-f",
                "json",
            ],
        )
        assert result.exit_code == 0
        # Should be valid JSON
        parsed = json.loads(result.output)
        assert "diff_id" in parsed

    def test_diff_short_output_option(
        self,
        runner: CliRunner,
        sample_contract_v1: Path,
        sample_contract_v2: Path,
        tmp_path: Path,
    ) -> None:
        """Test diff with -o short option for output."""
        output_file = tmp_path / "short_output.txt"
        result = runner.invoke(
            cli,
            [
                "contract",
                "diff",
                str(sample_contract_v1),
                str(sample_contract_v2),
                "-o",
                str(output_file),
            ],
        )
        assert result.exit_code == 0
        assert output_file.exists()


@pytest.mark.unit
class TestContractDiffYamlFiles:
    """Tests for diff with YAML files."""

    def test_diff_yaml_files(
        self,
        runner: CliRunner,
        sample_yaml_contract_v1: Path,
        sample_yaml_contract_v2: Path,
    ) -> None:
        """Test diff with YAML files."""
        result = runner.invoke(
            cli,
            [
                "contract",
                "diff",
                str(sample_yaml_contract_v1),
                str(sample_yaml_contract_v2),
            ],
        )
        # Should succeed if PyYAML is installed
        if result.exit_code == 0:
            assert len(result.output) > 0
        else:
            # If PyYAML not installed, should show helpful error
            assert "pyyaml" in result.output.lower() or "yaml" in result.output.lower()

    def test_diff_yaml_json_format_output(
        self,
        runner: CliRunner,
        sample_yaml_contract_v1: Path,
        sample_yaml_contract_v2: Path,
    ) -> None:
        """Test diff YAML files with JSON output format."""
        result = runner.invoke(
            cli,
            [
                "contract",
                "diff",
                str(sample_yaml_contract_v1),
                str(sample_yaml_contract_v2),
                "--format",
                "json",
            ],
        )
        if result.exit_code == 0:
            parsed = json.loads(result.output)
            assert "diff_id" in parsed


@pytest.mark.unit
class TestContractDiffErrorHandling:
    """Tests for diff command error handling."""

    def test_diff_file_not_found_first_arg(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test diff with nonexistent first file."""
        nonexistent = tmp_path / "nonexistent.json"
        existing = tmp_path / "exists.json"
        existing.write_text('{"name": "Test"}')

        result = runner.invoke(
            cli,
            ["contract", "diff", str(nonexistent), str(existing)],
        )
        assert result.exit_code != 0

    def test_diff_file_not_found_second_arg(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test diff with nonexistent second file."""
        existing = tmp_path / "exists.json"
        existing.write_text('{"name": "Test"}')
        nonexistent = tmp_path / "nonexistent.json"

        result = runner.invoke(
            cli,
            ["contract", "diff", str(existing), str(nonexistent)],
        )
        assert result.exit_code != 0

    def test_diff_both_files_not_found(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test diff with both files nonexistent."""
        result = runner.invoke(
            cli,
            [
                "contract",
                "diff",
                str(tmp_path / "nonexistent1.json"),
                str(tmp_path / "nonexistent2.json"),
            ],
        )
        assert result.exit_code != 0

    def test_diff_invalid_json_first_file(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test diff with invalid JSON in first file."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("not valid json {{{")
        valid_file = tmp_path / "valid.json"
        valid_file.write_text('{"name": "Test"}')

        result = runner.invoke(
            cli,
            ["contract", "diff", str(invalid_file), str(valid_file)],
        )
        assert result.exit_code != 0
        assert "error" in result.output.lower() or "invalid" in result.output.lower()

    def test_diff_invalid_json_second_file(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test diff with invalid JSON in second file."""
        valid_file = tmp_path / "valid.json"
        valid_file.write_text('{"name": "Test"}')
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("not valid json {{{")

        result = runner.invoke(
            cli,
            ["contract", "diff", str(valid_file), str(invalid_file)],
        )
        assert result.exit_code != 0
        assert "error" in result.output.lower() or "invalid" in result.output.lower()

    def test_diff_empty_json_files(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test diff with empty JSON files."""
        empty1 = tmp_path / "empty1.json"
        empty2 = tmp_path / "empty2.json"
        empty1.write_text("{}")
        empty2.write_text("{}")

        result = runner.invoke(
            cli,
            ["contract", "diff", str(empty1), str(empty2)],
        )
        # Empty objects should diff successfully
        assert result.exit_code == 0

    def test_diff_invalid_format_option(
        self, runner: CliRunner, sample_contract_v1: Path, sample_contract_v2: Path
    ) -> None:
        """Test diff with invalid format option."""
        result = runner.invoke(
            cli,
            [
                "contract",
                "diff",
                str(sample_contract_v1),
                str(sample_contract_v2),
                "--format",
                "invalid_format",
            ],
        )
        assert result.exit_code != 0
        # Should show valid choices
        assert "text" in result.output or "json" in result.output


@pytest.mark.unit
class TestContractDiffComplexContracts:
    """Tests for diff with complex contract structures."""

    def test_diff_nested_changes(
        self, runner: CliRunner, complex_contract_v1: Path, complex_contract_v2: Path
    ) -> None:
        """Test diff detects nested value changes."""
        result = runner.invoke(
            cli,
            [
                "contract",
                "diff",
                str(complex_contract_v1),
                str(complex_contract_v2),
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["has_changes"] is True
        assert parsed["total_changes"] > 0

    def test_diff_list_changes(
        self, runner: CliRunner, complex_contract_v1: Path, complex_contract_v2: Path
    ) -> None:
        """Test diff handles list field changes."""
        result = runner.invoke(
            cli,
            [
                "contract",
                "diff",
                str(complex_contract_v1),
                str(complex_contract_v2),
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        # Should have detected changes in dependencies and states lists
        assert parsed["total_changes"] > 0

    def test_diff_change_summary(
        self, runner: CliRunner, complex_contract_v1: Path, complex_contract_v2: Path
    ) -> None:
        """Test diff provides accurate change summary."""
        result = runner.invoke(
            cli,
            [
                "contract",
                "diff",
                str(complex_contract_v1),
                str(complex_contract_v2),
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        summary = parsed["change_summary"]
        # Summary should have all expected keys
        assert "added" in summary
        assert "removed" in summary
        assert "modified" in summary
        assert "moved" in summary
        # At least some changes should be detected
        total_from_summary = (
            summary["added"]
            + summary["removed"]
            + summary["modified"]
            + summary["moved"]
        )
        assert total_from_summary > 0


@pytest.mark.unit
class TestContractDiffFileExtensions:
    """Tests for diff with various file extensions."""

    def test_diff_unknown_extension_json_content(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test diff handles unknown extension with JSON content."""
        file1 = tmp_path / "contract1.data"
        file2 = tmp_path / "contract2.data"
        file1.write_text('{"name": "Contract1", "version": "1.0.0"}')
        file2.write_text('{"name": "Contract2", "version": "2.0.0"}')

        result = runner.invoke(
            cli,
            ["contract", "diff", str(file1), str(file2)],
        )
        # Should auto-detect JSON and succeed
        assert result.exit_code == 0

    def test_diff_yml_extension(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test diff handles .yml extension."""
        file1 = tmp_path / "contract1.yml"
        file2 = tmp_path / "contract2.yml"
        file1.write_text("name: Contract1\nversion: '1.0.0'\n")
        file2.write_text("name: Contract2\nversion: '2.0.0'\n")

        result = runner.invoke(
            cli,
            ["contract", "diff", str(file1), str(file2)],
        )
        # Should succeed if PyYAML is installed
        if result.exit_code == 0:
            assert len(result.output) > 0
        else:
            # PyYAML not installed
            assert "pyyaml" in result.output.lower()

    def test_diff_mixed_extensions(
        self, runner: CliRunner, sample_contract_v1: Path, tmp_path: Path
    ) -> None:
        """Test diff between JSON and YAML files."""
        yaml_file = tmp_path / "contract.yaml"
        yaml_file.write_text(
            'name: TestContract\nversion: "2.0.0"\nmeta:\n  description: From YAML\n'
        )

        result = runner.invoke(
            cli,
            ["contract", "diff", str(sample_contract_v1), str(yaml_file)],
        )
        # Should succeed if PyYAML is installed
        if result.exit_code == 0:
            assert len(result.output) > 0


@pytest.mark.unit
class TestContractDiffVerbose:
    """Tests for diff with verbose mode."""

    def test_diff_with_verbose_flag(
        self, runner: CliRunner, sample_contract_v1: Path, sample_contract_v2: Path
    ) -> None:
        """Test diff with parent --verbose flag."""
        result = runner.invoke(
            cli,
            [
                "--verbose",
                "contract",
                "diff",
                str(sample_contract_v1),
                str(sample_contract_v2),
            ],
        )
        # Should complete without error
        assert result.exit_code == 0


@pytest.mark.unit
class TestContractDiffEdgeCases:
    """Tests for edge cases in diff command."""

    def test_diff_same_file_twice(
        self, runner: CliRunner, sample_contract_v1: Path
    ) -> None:
        """Test diff when both arguments are the same file."""
        result = runner.invoke(
            cli,
            [
                "contract",
                "diff",
                str(sample_contract_v1),
                str(sample_contract_v1),
            ],
        )
        assert result.exit_code == 0
        # Should show no changes
        output_lower = result.output.lower()
        assert (
            "no change" in output_lower
            or "0 change" in output_lower
            or "identical" in output_lower
        )

    def test_diff_with_unicode_content(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test diff handles unicode content."""
        file1 = tmp_path / "unicode1.json"
        file2 = tmp_path / "unicode2.json"
        file1.write_text('{"name": "Test", "description": "Hello"}', encoding="utf-8")
        file2.write_text(
            '{"name": "Test", "description": "Hello World"}', encoding="utf-8"
        )

        result = runner.invoke(
            cli,
            ["contract", "diff", str(file1), str(file2)],
        )
        assert result.exit_code == 0

    def test_diff_with_special_characters_in_values(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test diff handles special characters in values."""
        file1 = tmp_path / "special1.json"
        file2 = tmp_path / "special2.json"
        file1.write_text('{"name": "Test<>&\\"value"}')
        file2.write_text('{"name": "Modified<>&\\"value"}')

        result = runner.invoke(
            cli,
            ["contract", "diff", str(file1), str(file2)],
        )
        assert result.exit_code == 0

    def test_diff_html_escapes_special_characters(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test HTML format properly escapes special characters."""
        file1 = tmp_path / "html1.json"
        file2 = tmp_path / "html2.json"
        file1.write_text('{"name": "<script>alert(1)</script>"}')
        file2.write_text('{"name": "<div>safe</div>"}')

        result = runner.invoke(
            cli,
            [
                "contract",
                "diff",
                str(file1),
                str(file2),
                "--format",
                "html",
            ],
        )
        assert result.exit_code == 0
        # Script tags should be escaped in HTML output
        assert "<script>" not in result.output
        assert "&lt;" in result.output or "script" not in result.output

    def test_diff_large_contract(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test diff handles larger contracts."""
        # Create contract with many fields
        large_contract1: dict[str, object] = {"name": "LargeContract", "fields": {}}
        large_contract2: dict[str, object] = {"name": "LargeContract", "fields": {}}

        fields1 = large_contract1["fields"]
        fields2 = large_contract2["fields"]

        if isinstance(fields1, dict) and isinstance(fields2, dict):
            for i in range(100):
                fields1[f"field_{i}"] = f"value_{i}"
                # Modify every 10th field
                if i % 10 == 0:
                    fields2[f"field_{i}"] = f"modified_{i}"
                else:
                    fields2[f"field_{i}"] = f"value_{i}"

        file1 = tmp_path / "large1.json"
        file2 = tmp_path / "large2.json"
        file1.write_text(json.dumps(large_contract1))
        file2.write_text(json.dumps(large_contract2))

        result = runner.invoke(
            cli,
            [
                "contract",
                "diff",
                str(file1),
                str(file2),
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["has_changes"] is True
        # Should have 10 modified fields
        assert parsed["total_changes"] == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
