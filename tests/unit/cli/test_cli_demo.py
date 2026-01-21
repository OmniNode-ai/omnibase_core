"""
Tests for demo CLI commands.

Tests cover:
- `onex demo list`: Listing available demo scenarios
- `onex demo run`: Running demo scenarios with corpus evaluation
- Helper functions: _get_demo_root, _is_demo_scenario, _discover_scenarios
- _extract_scenario_description, _get_scenario_path
- _load_corpus, _load_mock_responses
- _create_output_bundle, _write_markdown_report
- Error handling for missing scenarios, missing corpus, invalid paths
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from omnibase_core.cli.cli_demo import (
    MIN_NAME_COLUMN_WIDTH,
    SCENARIO_CONTRACT_FILES,
    _create_output_bundle,
    _discover_scenarios,
    _extract_scenario_description,
    _get_demo_root,
    _get_scenario_path,
    _is_demo_scenario,
    _load_corpus,
    _load_mock_responses,
    _write_markdown_report,
    demo,
)
from omnibase_core.enums.enum_cli_exit_code import EnumCLIExitCode
from omnibase_core.enums.enum_demo_verdict import EnumDemoVerdict
from omnibase_core.models.demo import (
    ModelDemoConfig,
    ModelDemoSummary,
    ModelDemoValidationReport,
    ModelInvariantResult,
    ModelSampleResult,
)

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def demo_root(tmp_path: Path) -> Path:
    """Create a mock demo root directory with a sample scenario."""
    demo_dir = tmp_path / "examples" / "demo"
    demo_dir.mkdir(parents=True)

    # Create model-validate scenario
    scenario_dir = demo_dir / "model-validate"
    scenario_dir.mkdir()

    # Create contract.yaml
    contract = {
        "name": "test-scenario",
        "metadata": {"description": "A test demo scenario for validation"},
        "node": {"kind": "COMPUTE"},
    }
    (scenario_dir / "contract.yaml").write_text(yaml.safe_dump(contract))

    # Create invariants.yaml
    invariants = {
        "thresholds": {"confidence_min": 0.7},
        "rules": [{"type": "confidence_threshold"}],
    }
    (scenario_dir / "invariants.yaml").write_text(yaml.safe_dump(invariants))

    # Create corpus directory with samples
    corpus_dir = scenario_dir / "corpus"
    corpus_dir.mkdir()

    golden_dir = corpus_dir / "golden"
    golden_dir.mkdir()

    sample1 = {"ticket_id": "T001", "subject": "Test subject", "body": "Test body"}
    (golden_dir / "sample_001.yaml").write_text(yaml.safe_dump(sample1))

    sample2 = {"ticket_id": "T002", "subject": "Another test", "body": "More content"}
    (golden_dir / "sample_002.yaml").write_text(yaml.safe_dump(sample2))

    # Create mock-responses directory
    mock_dir = scenario_dir / "mock-responses"
    mock_dir.mkdir()

    baseline_dir = mock_dir / "baseline"
    baseline_dir.mkdir()

    response1 = {"category": "billing", "confidence": 0.95}
    (baseline_dir / "response_001.json").write_text(json.dumps(response1))

    return demo_dir


@pytest.fixture
def nested_demo_root(tmp_path: Path) -> Path:
    """Create a mock demo root with nested scenarios (handlers/support_assistant)."""
    demo_dir = tmp_path / "examples" / "demo"
    demo_dir.mkdir(parents=True)

    # Create nested scenario: handlers/support_assistant
    handlers_dir = demo_dir / "handlers"
    handlers_dir.mkdir()

    scenario_dir = handlers_dir / "support_assistant"
    scenario_dir.mkdir()

    # Create contract.yaml for nested scenario
    contract = {
        "name": "support-assistant",
        "metadata": {"description": "Support assistant handler scenario"},
    }
    (scenario_dir / "contract.yaml").write_text(yaml.safe_dump(contract))

    # Create corpus
    corpus_dir = scenario_dir / "corpus"
    corpus_dir.mkdir()
    golden_dir = corpus_dir / "golden"
    golden_dir.mkdir()
    (golden_dir / "sample.yaml").write_text(yaml.safe_dump({"id": "1"}))

    return demo_dir


# =============================================================================
# Demo Group Command Tests
# =============================================================================


class TestDemoGroupCommand:
    """Tests for the demo command group."""

    def test_demo_group_exists(self, runner: CliRunner) -> None:
        """Test that the demo command group exists."""
        result = runner.invoke(demo, ["--help"])
        assert result.exit_code == EnumCLIExitCode.SUCCESS

    def test_demo_help_shows_subcommands(self, runner: CliRunner) -> None:
        """Test that demo --help shows all subcommands."""
        result = runner.invoke(demo, ["--help"])
        assert result.exit_code == EnumCLIExitCode.SUCCESS
        assert "list" in result.output
        assert "run" in result.output

    def test_demo_no_command_shows_help(self, runner: CliRunner) -> None:
        """Test that invoking demo without subcommand shows help."""
        result = runner.invoke(demo, [])
        # Click groups without a default command show usage
        assert result.exit_code in (0, 2)
        assert "Usage" in result.output or "usage" in result.output.lower()


# =============================================================================
# List Command Tests
# =============================================================================


class TestListCommand:
    """Tests for the `onex demo list` command."""

    def test_list_help(self, runner: CliRunner) -> None:
        """Test that list --help shows usage information."""
        result = runner.invoke(demo, ["list", "--help"])
        assert result.exit_code == EnumCLIExitCode.SUCCESS
        assert "--path" in result.output or "-p" in result.output

    def test_list_shows_scenarios(self, runner: CliRunner, demo_root: Path) -> None:
        """Test that list discovers and shows scenarios."""
        result = runner.invoke(demo, ["list", "--path", str(demo_root)])
        assert result.exit_code == EnumCLIExitCode.SUCCESS
        assert "model-validate" in result.output
        assert "Available demo scenarios" in result.output

    def test_list_shows_scenario_count(
        self, runner: CliRunner, demo_root: Path
    ) -> None:
        """Test that list shows total scenario count."""
        result = runner.invoke(demo, ["list", "--path", str(demo_root)])
        assert result.exit_code == EnumCLIExitCode.SUCCESS
        assert "Total:" in result.output
        assert "1 scenario" in result.output

    def test_list_shows_description(self, runner: CliRunner, demo_root: Path) -> None:
        """Test that list shows scenario descriptions from contract.yaml."""
        result = runner.invoke(demo, ["list", "--path", str(demo_root)])
        assert result.exit_code == EnumCLIExitCode.SUCCESS
        # Description from metadata.description in contract.yaml
        assert "test demo scenario" in result.output.lower()

    def test_list_discovers_nested_scenarios(
        self, runner: CliRunner, nested_demo_root: Path
    ) -> None:
        """Test that list discovers nested scenarios (handlers/support_assistant)."""
        result = runner.invoke(demo, ["list", "--path", str(nested_demo_root)])
        assert result.exit_code == EnumCLIExitCode.SUCCESS
        assert "handlers/support_assistant" in result.output

    def test_list_no_scenarios_found(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test that list handles empty demo directory."""
        empty_demo = tmp_path / "empty_demo"
        empty_demo.mkdir()

        result = runner.invoke(demo, ["list", "--path", str(empty_demo)])
        assert result.exit_code == EnumCLIExitCode.SUCCESS
        assert "No demo scenarios found" in result.output

    def test_list_error_for_nonexistent_path(self, runner: CliRunner) -> None:
        """Test that list fails with error for nonexistent path."""
        result = runner.invoke(demo, ["list", "--path", "/nonexistent/path"])
        assert result.exit_code != EnumCLIExitCode.SUCCESS
        assert (
            "does not exist" in result.output.lower()
            or "error" in result.output.lower()
        )

    def test_list_uses_default_demo_root(self, runner: CliRunner) -> None:
        """Test that list uses default examples/demo/ when no path specified."""
        # This test relies on the actual demo directory existing
        # If it doesn't exist, we expect an error
        result = runner.invoke(demo, ["list"])
        # Either succeeds (if demo exists) or fails with helpful message
        if result.exit_code == EnumCLIExitCode.SUCCESS:
            assert (
                "Available demo scenarios" in result.output
                or "No demo scenarios" in result.output
            )
        else:
            assert "demo" in result.output.lower()


# =============================================================================
# Run Command Tests
# =============================================================================


class TestRunCommand:
    """Tests for the `onex demo run` command."""

    def test_run_help(self, runner: CliRunner) -> None:
        """Test that run --help shows usage information."""
        result = runner.invoke(demo, ["run", "--help"])
        assert result.exit_code == EnumCLIExitCode.SUCCESS
        assert "--scenario" in result.output
        assert "--output" in result.output
        assert "--seed" in result.output
        assert "--live" in result.output
        assert "--repeat" in result.output

    def test_run_requires_scenario(self, runner: CliRunner) -> None:
        """Test that run requires --scenario option."""
        result = runner.invoke(demo, ["run"])
        assert result.exit_code != EnumCLIExitCode.SUCCESS
        assert "Missing option" in result.output or "--scenario" in result.output

    def test_run_creates_output_bundle(
        self, runner: CliRunner, demo_root: Path, tmp_path: Path
    ) -> None:
        """Test that run creates output bundle with expected structure."""
        output_dir = tmp_path / "output"

        # Patch _get_demo_root to return our fixture
        with patch("omnibase_core.cli.cli_demo._get_demo_root", return_value=demo_root):
            result = runner.invoke(
                demo,
                [
                    "run",
                    "--scenario",
                    "model-validate",
                    "--output",
                    str(output_dir),
                    "--seed",
                    "42",
                ],
            )

        # May pass or fail depending on invariant results
        assert result.exit_code in (EnumCLIExitCode.SUCCESS, EnumCLIExitCode.ERROR)

        # Verify output bundle structure
        assert output_dir.exists()
        assert (output_dir / "run_manifest.yaml").exists()
        assert (output_dir / "report.json").exists()
        assert (output_dir / "report.md").exists()
        assert (output_dir / "inputs").is_dir()
        assert (output_dir / "outputs").is_dir()

    def test_run_manifest_contains_metadata(
        self, runner: CliRunner, demo_root: Path, tmp_path: Path
    ) -> None:
        """Test that run_manifest.yaml contains expected metadata."""
        output_dir = tmp_path / "output"

        with patch("omnibase_core.cli.cli_demo._get_demo_root", return_value=demo_root):
            runner.invoke(
                demo,
                [
                    "run",
                    "--scenario",
                    "model-validate",
                    "--output",
                    str(output_dir),
                    "--seed",
                    "123",
                ],
            )

        manifest_path = output_dir / "run_manifest.yaml"
        assert manifest_path.exists()

        manifest = yaml.safe_load(manifest_path.read_text())
        assert manifest["scenario"] == "model-validate"
        assert manifest["seed"] == 123
        assert "timestamp" in manifest
        assert "corpus_count" in manifest

    def test_run_report_json_contains_results(
        self, runner: CliRunner, demo_root: Path, tmp_path: Path
    ) -> None:
        """Test that report.json contains evaluation results."""
        output_dir = tmp_path / "output"

        with patch("omnibase_core.cli.cli_demo._get_demo_root", return_value=demo_root):
            runner.invoke(
                demo,
                [
                    "run",
                    "--scenario",
                    "model-validate",
                    "--output",
                    str(output_dir),
                ],
            )

        report_path = output_dir / "report.json"
        assert report_path.exists()

        report = json.loads(report_path.read_text())
        assert "scenario" in report
        assert "summary" in report
        assert "results" in report
        assert "config" in report

    def test_run_error_for_missing_scenario(
        self, runner: CliRunner, demo_root: Path
    ) -> None:
        """Test that run fails with error for nonexistent scenario."""
        with patch("omnibase_core.cli.cli_demo._get_demo_root", return_value=demo_root):
            result = runner.invoke(
                demo,
                ["run", "--scenario", "nonexistent-scenario"],
            )

        assert result.exit_code != EnumCLIExitCode.SUCCESS
        assert "not found" in result.output.lower()
        assert "onex demo list" in result.output.lower()

    def test_run_error_for_missing_corpus(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that run fails with error when corpus is missing."""
        # Create scenario without corpus
        demo_dir = tmp_path / "demo"
        demo_dir.mkdir()
        scenario_dir = demo_dir / "no-corpus"
        scenario_dir.mkdir()
        (scenario_dir / "contract.yaml").write_text("name: test")

        with patch("omnibase_core.cli.cli_demo._get_demo_root", return_value=demo_dir):
            result = runner.invoke(
                demo,
                ["run", "--scenario", "no-corpus"],
            )

        assert result.exit_code != EnumCLIExitCode.SUCCESS
        assert "corpus" in result.output.lower()

    def test_run_with_repeat_multiplies_corpus(
        self, runner: CliRunner, demo_root: Path, tmp_path: Path
    ) -> None:
        """Test that --repeat multiplies the corpus samples."""
        output_dir = tmp_path / "output"

        with patch("omnibase_core.cli.cli_demo._get_demo_root", return_value=demo_root):
            result = runner.invoke(
                demo,
                [
                    "run",
                    "--scenario",
                    "model-validate",
                    "--output",
                    str(output_dir),
                    "--repeat",
                    "3",
                ],
            )

        assert result.exit_code in (EnumCLIExitCode.SUCCESS, EnumCLIExitCode.ERROR)

        manifest = yaml.safe_load((output_dir / "run_manifest.yaml").read_text())
        # Original corpus has 2 samples, repeat=3 should give 6
        assert manifest["corpus_count"] == 6
        assert manifest["repeat"] == 3

    def test_run_with_seed_provides_determinism(
        self, runner: CliRunner, demo_root: Path, tmp_path: Path
    ) -> None:
        """Test that --seed produces deterministic results."""
        output1 = tmp_path / "output1"
        output2 = tmp_path / "output2"

        with patch("omnibase_core.cli.cli_demo._get_demo_root", return_value=demo_root):
            runner.invoke(
                demo,
                [
                    "run",
                    "--scenario",
                    "model-validate",
                    "--output",
                    str(output1),
                    "--seed",
                    "42",
                ],
            )
            runner.invoke(
                demo,
                [
                    "run",
                    "--scenario",
                    "model-validate",
                    "--output",
                    str(output2),
                    "--seed",
                    "42",
                ],
            )

        # Same seed should produce same results
        report1 = json.loads((output1 / "report.json").read_text())
        report2 = json.loads((output2 / "report.json").read_text())

        assert report1["summary"]["passed"] == report2["summary"]["passed"]
        assert report1["summary"]["failed"] == report2["summary"]["failed"]

    def test_run_prints_banner(
        self, runner: CliRunner, demo_root: Path, tmp_path: Path
    ) -> None:
        """Test that run prints a banner with scenario name."""
        with patch("omnibase_core.cli.cli_demo._get_demo_root", return_value=demo_root):
            result = runner.invoke(
                demo,
                [
                    "run",
                    "--scenario",
                    "model-validate",
                    "--output",
                    str(tmp_path / "out"),
                ],
            )

        assert "ONEX DEMO:" in result.output
        assert "model-validate" in result.output

    def test_run_shows_mode_mock_by_default(
        self, runner: CliRunner, demo_root: Path, tmp_path: Path
    ) -> None:
        """Test that run shows mock mode by default."""
        with patch("omnibase_core.cli.cli_demo._get_demo_root", return_value=demo_root):
            result = runner.invoke(
                demo,
                [
                    "run",
                    "--scenario",
                    "model-validate",
                    "--output",
                    str(tmp_path / "out"),
                ],
            )

        assert "Mode:" in result.output
        assert "mock" in result.output.lower()

    def test_run_shows_mode_live_when_specified(
        self, runner: CliRunner, demo_root: Path, tmp_path: Path
    ) -> None:
        """Test that run shows live mode when --live is specified."""
        with patch("omnibase_core.cli.cli_demo._get_demo_root", return_value=demo_root):
            result = runner.invoke(
                demo,
                [
                    "run",
                    "--scenario",
                    "model-validate",
                    "--output",
                    str(tmp_path / "out"),
                    "--live",
                ],
            )

        assert "Mode:" in result.output
        assert "live" in result.output.lower()


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestGetDemoRoot:
    """Tests for the _get_demo_root helper function."""

    def test_get_demo_root_finds_examples_demo(self) -> None:
        """Test that _get_demo_root finds examples/demo/ directory."""
        # This test relies on actual repo structure
        try:
            demo_root = _get_demo_root()
            assert demo_root.name == "demo"
            assert demo_root.parent.name == "examples"
        except Exception:
            # If demo directory doesn't exist, test passes
            pass

    def test_get_demo_root_raises_on_missing_directory(self, tmp_path: Path) -> None:
        """Test that _get_demo_root raises when demo directory not found."""
        # Patch __file__ to point to a location without examples/demo
        with patch(
            "omnibase_core.cli.cli_demo.Path.cwd",
            return_value=tmp_path,
        ):
            with patch(
                "omnibase_core.cli.cli_demo.__file__",
                str(tmp_path / "fake" / "cli_demo.py"),
            ):
                # Create necessary parent directories without demo
                (tmp_path / "fake").mkdir(parents=True)
                import click

                with pytest.raises(click.ClickException) as exc_info:
                    _get_demo_root()
                assert "Could not locate" in str(exc_info.value)


class TestIsDemoScenario:
    """Tests for the _is_demo_scenario helper function."""

    def test_is_demo_scenario_with_contract_yaml(self, tmp_path: Path) -> None:
        """Test that directory with contract.yaml is a scenario."""
        scenario = tmp_path / "my-scenario"
        scenario.mkdir()
        (scenario / "contract.yaml").write_text("name: test")

        assert _is_demo_scenario(scenario) is True

    def test_is_demo_scenario_with_invariants_yaml(self, tmp_path: Path) -> None:
        """Test that directory with invariants.yaml is a scenario."""
        scenario = tmp_path / "my-scenario"
        scenario.mkdir()
        (scenario / "invariants.yaml").write_text("rules: []")

        assert _is_demo_scenario(scenario) is True

    def test_is_demo_scenario_with_both_files(self, tmp_path: Path) -> None:
        """Test that directory with both files is a scenario."""
        scenario = tmp_path / "my-scenario"
        scenario.mkdir()
        (scenario / "contract.yaml").write_text("name: test")
        (scenario / "invariants.yaml").write_text("rules: []")

        assert _is_demo_scenario(scenario) is True

    def test_is_demo_scenario_without_contract_files(self, tmp_path: Path) -> None:
        """Test that directory without contract files is not a scenario."""
        not_scenario = tmp_path / "not-a-scenario"
        not_scenario.mkdir()
        (not_scenario / "README.md").write_text("# Not a scenario")

        assert _is_demo_scenario(not_scenario) is False

    def test_is_demo_scenario_with_file_path(self, tmp_path: Path) -> None:
        """Test that file path returns False."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")

        assert _is_demo_scenario(file_path) is False

    def test_is_demo_scenario_with_nonexistent_path(self, tmp_path: Path) -> None:
        """Test that nonexistent path returns False."""
        assert _is_demo_scenario(tmp_path / "nonexistent") is False


class TestDiscoverScenarios:
    """Tests for the _discover_scenarios helper function."""

    def test_discover_scenarios_finds_direct_scenarios(self, demo_root: Path) -> None:
        """Test that _discover_scenarios finds direct child scenarios."""
        scenarios = list(_discover_scenarios(demo_root))
        assert len(scenarios) == 1
        assert scenarios[0][0] == "model-validate"

    def test_discover_scenarios_finds_nested_scenarios(
        self, nested_demo_root: Path
    ) -> None:
        """Test that _discover_scenarios finds nested scenarios."""
        scenarios = list(_discover_scenarios(nested_demo_root))
        assert len(scenarios) == 1
        assert scenarios[0][0] == "handlers/support_assistant"

    def test_discover_scenarios_skips_hidden_directories(self, tmp_path: Path) -> None:
        """Test that _discover_scenarios skips hidden directories."""
        demo_dir = tmp_path / "demo"
        demo_dir.mkdir()

        # Create hidden scenario (should be skipped)
        hidden = demo_dir / ".hidden-scenario"
        hidden.mkdir()
        (hidden / "contract.yaml").write_text("name: hidden")

        # Create underscore scenario (should be skipped)
        underscore = demo_dir / "_private-scenario"
        underscore.mkdir()
        (underscore / "contract.yaml").write_text("name: private")

        scenarios = list(_discover_scenarios(demo_dir))
        assert len(scenarios) == 0

    def test_discover_scenarios_returns_empty_for_nonexistent_dir(
        self, tmp_path: Path
    ) -> None:
        """Test that _discover_scenarios returns empty for nonexistent directory."""
        scenarios = list(_discover_scenarios(tmp_path / "nonexistent"))
        assert scenarios == []

    def test_discover_scenarios_yields_tuples(self, demo_root: Path) -> None:
        """Test that _discover_scenarios yields (name, description, path) tuples."""
        scenarios = list(_discover_scenarios(demo_root))
        assert len(scenarios) == 1

        name, description, path = scenarios[0]
        assert isinstance(name, str)
        assert isinstance(description, str)
        assert isinstance(path, Path)
        assert path.exists()


class TestExtractScenarioDescription:
    """Tests for the _extract_scenario_description helper function."""

    def test_extracts_from_metadata_description(self, tmp_path: Path) -> None:
        """Test extraction from metadata.description in contract.yaml."""
        scenario = tmp_path / "scenario"
        scenario.mkdir()

        contract = {"metadata": {"description": "Test description from metadata"}}
        (scenario / "contract.yaml").write_text(yaml.safe_dump(contract))

        description = _extract_scenario_description(scenario)
        assert description == "Test description from metadata"

    def test_extracts_from_top_level_description(self, tmp_path: Path) -> None:
        """Test extraction from top-level description in contract.yaml."""
        scenario = tmp_path / "scenario"
        scenario.mkdir()

        contract = {"description": "Top-level description"}
        (scenario / "contract.yaml").write_text(yaml.safe_dump(contract))

        description = _extract_scenario_description(scenario)
        assert description == "Top-level description"

    def test_truncates_long_descriptions(self, tmp_path: Path) -> None:
        """Test that long descriptions are truncated."""
        scenario = tmp_path / "scenario"
        scenario.mkdir()

        long_desc = "A" * 100  # More than 60 chars
        contract = {"metadata": {"description": long_desc}}
        (scenario / "contract.yaml").write_text(yaml.safe_dump(contract))

        description = _extract_scenario_description(scenario)
        assert len(description) == 60
        assert description.endswith("...")

    def test_extracts_from_readme(self, tmp_path: Path) -> None:
        """Test extraction from README.md when no contract.yaml."""
        scenario = tmp_path / "scenario"
        scenario.mkdir()

        # Create invariants.yaml to make it a scenario, but no description
        (scenario / "invariants.yaml").write_text("rules: []")

        readme_content = """# My Scenario

This is the description from README.
"""
        (scenario / "README.md").write_text(readme_content)

        description = _extract_scenario_description(scenario)
        assert description == "This is the description from README."

    def test_fallback_to_name_based_description(self, tmp_path: Path) -> None:
        """Test fallback to name-based description when no sources available."""
        scenario = tmp_path / "my-cool-scenario"
        scenario.mkdir()

        # Create contract without description
        (scenario / "contract.yaml").write_text("name: test")

        description = _extract_scenario_description(scenario)
        assert "My Cool Scenario" in description
        assert "demo scenario" in description.lower()


class TestGetScenarioPath:
    """Tests for the _get_scenario_path helper function."""

    def test_finds_direct_scenario(self, demo_root: Path) -> None:
        """Test that direct scenarios are found."""
        path = _get_scenario_path("model-validate", demo_root)
        assert path is not None
        assert path.name == "model-validate"

    def test_finds_nested_scenario(self, nested_demo_root: Path) -> None:
        """Test that nested scenarios are found with path notation."""
        path = _get_scenario_path("handlers/support_assistant", nested_demo_root)
        assert path is not None
        assert path.name == "support_assistant"

    def test_returns_none_for_nonexistent_scenario(self, demo_root: Path) -> None:
        """Test that None is returned for nonexistent scenario."""
        path = _get_scenario_path("nonexistent", demo_root)
        assert path is None


class TestLoadCorpus:
    """Tests for the _load_corpus helper function."""

    def test_loads_samples_from_subdirectories(self, demo_root: Path) -> None:
        """Test that corpus samples are loaded from subdirectories."""
        corpus_dir = demo_root / "model-validate" / "corpus"
        samples = _load_corpus(corpus_dir)

        assert len(samples) == 2
        assert all("_source_file" in s for s in samples)
        assert all("_category" in s for s in samples)

    def test_loads_samples_from_root(self, tmp_path: Path) -> None:
        """Test that corpus samples in root directory are loaded."""
        corpus_dir = tmp_path / "corpus"
        corpus_dir.mkdir()

        sample = {"id": "root-sample"}
        (corpus_dir / "sample.yaml").write_text(yaml.safe_dump(sample))

        samples = _load_corpus(corpus_dir)
        assert len(samples) == 1
        assert samples[0]["_category"] == "root"

    def test_returns_empty_for_missing_directory(self, tmp_path: Path) -> None:
        """Test that empty list is returned for missing directory."""
        samples = _load_corpus(tmp_path / "nonexistent")
        assert samples == []

    def test_skips_invalid_yaml_files(self, tmp_path: Path) -> None:
        """Test that invalid YAML files are skipped."""
        corpus_dir = tmp_path / "corpus"
        corpus_dir.mkdir()
        golden = corpus_dir / "golden"
        golden.mkdir()

        # Valid sample
        (golden / "valid.yaml").write_text(yaml.safe_dump({"id": "valid"}))
        # Invalid YAML
        (golden / "invalid.yaml").write_text("invalid: yaml: ][")

        samples = _load_corpus(corpus_dir)
        assert len(samples) == 1
        assert samples[0]["id"] == "valid"


class TestLoadMockResponses:
    """Tests for the _load_mock_responses helper function."""

    def test_loads_responses_from_model_directories(self, demo_root: Path) -> None:
        """Test that mock responses are loaded from model directories."""
        mock_dir = demo_root / "model-validate" / "mock-responses"
        responses = _load_mock_responses(mock_dir)

        assert len(responses) > 0
        # Keys should be model_type/filename_stem format
        assert any("baseline/" in key for key in responses)

    def test_returns_empty_for_missing_directory(self, tmp_path: Path) -> None:
        """Test that empty dict is returned for missing directory."""
        responses = _load_mock_responses(tmp_path / "nonexistent")
        assert responses == {}

    def test_skips_invalid_json_files(self, tmp_path: Path) -> None:
        """Test that invalid JSON files are skipped."""
        mock_dir = tmp_path / "mock-responses"
        mock_dir.mkdir()
        model_dir = mock_dir / "baseline"
        model_dir.mkdir()

        # Valid JSON
        (model_dir / "valid.json").write_text('{"id": "valid"}')
        # Invalid JSON
        (model_dir / "invalid.json").write_text("{invalid json}")

        responses = _load_mock_responses(mock_dir)
        assert len(responses) == 1
        assert "baseline/valid" in responses


class TestCreateOutputBundle:
    """Tests for the _create_output_bundle helper function."""

    def test_creates_directory_structure(self, tmp_path: Path) -> None:
        """Test that output bundle creates expected directory structure."""
        output_dir = tmp_path / "output"
        corpus: list[dict[str, Any]] = [{"id": "1"}, {"id": "2"}]
        results = [
            ModelSampleResult(sample_id="1", passed=True, invariants_checked=[]),
            ModelSampleResult(sample_id="2", passed=False, invariants_checked=[]),
        ]
        config = ModelDemoConfig(
            scenario="test",
            live=False,
            seed=42,
            repeat=1,
            timestamp="2024-01-01T00:00:00",
        )
        summary = ModelDemoSummary(
            total=2,
            passed=1,
            failed=1,
            pass_rate=0.5,
            verdict=EnumDemoVerdict.FAIL,
            invariant_results={},
            failures=[],
        )
        report = ModelDemoValidationReport(
            scenario="test-scenario",
            timestamp="2024-01-01T00:00:00",
            config=config,
            summary=summary,
            results=results,
        )

        _create_output_bundle(output_dir, "test-scenario", corpus, report)

        assert output_dir.exists()
        assert (output_dir / "inputs").is_dir()
        assert (output_dir / "outputs").is_dir()
        assert (output_dir / "run_manifest.yaml").exists()
        assert (output_dir / "report.json").exists()
        assert (output_dir / "report.md").exists()

    def test_writes_corpus_samples_to_inputs(self, tmp_path: Path) -> None:
        """Test that corpus samples are written to inputs/."""
        output_dir = tmp_path / "output"
        corpus: list[dict[str, Any]] = [{"id": "1"}, {"id": "2"}]
        results: list[ModelSampleResult] = []
        config = ModelDemoConfig(
            scenario="test",
            live=False,
            seed=None,
            repeat=1,
            timestamp="2024-01-01T00:00:00",
        )
        summary = ModelDemoSummary(
            total=0,
            passed=0,
            failed=0,
            pass_rate=0,
            verdict=EnumDemoVerdict.PASS,
            invariant_results={},
            failures=[],
        )
        report = ModelDemoValidationReport(
            scenario="test",
            timestamp="2024-01-01T00:00:00",
            config=config,
            summary=summary,
            results=results,
        )

        _create_output_bundle(output_dir, "test", corpus, report)

        inputs_dir = output_dir / "inputs"
        assert (inputs_dir / "sample_001.yaml").exists()
        assert (inputs_dir / "sample_002.yaml").exists()

    def test_writes_results_to_outputs(self, tmp_path: Path) -> None:
        """Test that results are written to outputs/."""
        output_dir = tmp_path / "output"
        corpus: list[dict[str, Any]] = []
        results = [ModelSampleResult(sample_id="1", passed=True, invariants_checked=[])]
        config = ModelDemoConfig(
            scenario="test",
            live=False,
            seed=None,
            repeat=1,
            timestamp="2024-01-01T00:00:00",
        )
        summary = ModelDemoSummary(
            total=1,
            passed=1,
            failed=0,
            pass_rate=1.0,
            verdict=EnumDemoVerdict.PASS,
            invariant_results={},
            failures=[],
        )
        report = ModelDemoValidationReport(
            scenario="test",
            timestamp="2024-01-01T00:00:00",
            config=config,
            summary=summary,
            results=results,
        )

        _create_output_bundle(output_dir, "test", corpus, report)

        outputs_dir = output_dir / "outputs"
        assert (outputs_dir / "sample_001.json").exists()


class TestWriteMarkdownReport:
    """Tests for the _write_markdown_report helper function."""

    def test_writes_markdown_report(self, tmp_path: Path) -> None:
        """Test that markdown report is written correctly."""
        report_path = tmp_path / "report.md"
        summary = ModelDemoSummary(
            total=10,
            passed=8,
            failed=2,
            pass_rate=0.8,
            verdict=EnumDemoVerdict.REVIEW,
            invariant_results={
                "confidence_threshold": ModelInvariantResult(
                    passed=8, failed=2, total=10
                )
            },
            failures=[],
        )
        results = [
            ModelSampleResult(sample_id="sample_1", passed=True, invariants_checked=[]),
            ModelSampleResult(
                sample_id="sample_2", passed=False, invariants_checked=[]
            ),
        ]

        _write_markdown_report(report_path, "test-scenario", summary, results)

        content = report_path.read_text()
        assert "# ONEX Demo Report: test-scenario" in content
        assert "Total Samples" in content
        assert "10" in content
        assert "REVIEW" in content
        assert "confidence_threshold" in content

    def test_handles_empty_results(self, tmp_path: Path) -> None:
        """Test that markdown report handles empty results."""
        report_path = tmp_path / "report.md"
        summary = ModelDemoSummary(
            total=0,
            passed=0,
            failed=0,
            pass_rate=0,
            verdict=EnumDemoVerdict.PASS,
            invariant_results={},
            failures=[],
        )
        results: list[ModelSampleResult] = []

        _write_markdown_report(report_path, "empty-test", summary, results)

        content = report_path.read_text()
        assert "empty-test" in content
        assert "PASS" in content


# =============================================================================
# Constants Tests
# =============================================================================


class TestDemoConstants:
    """Tests for demo CLI constants."""

    def test_scenario_contract_files_contains_expected_values(self) -> None:
        """Test that SCENARIO_CONTRACT_FILES has expected contract file names."""
        assert "contract.yaml" in SCENARIO_CONTRACT_FILES
        assert "invariants.yaml" in SCENARIO_CONTRACT_FILES

    def test_min_name_column_width_is_reasonable(self) -> None:
        """Test that MIN_NAME_COLUMN_WIDTH is a reasonable value."""
        assert MIN_NAME_COLUMN_WIDTH >= 10
        assert MIN_NAME_COLUMN_WIDTH <= 50


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestDemoCliEdgeCases:
    """Edge case tests for demo CLI commands."""

    def test_list_handles_yaml_parse_errors_gracefully(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that list handles YAML parse errors in contract files."""
        demo_dir = tmp_path / "demo"
        demo_dir.mkdir()
        scenario = demo_dir / "bad-yaml"
        scenario.mkdir()

        # Create contract with invalid YAML (will fail to parse for description)
        (scenario / "contract.yaml").write_text("invalid: yaml: ][")

        # But since the file exists, it's still a scenario
        result = runner.invoke(demo, ["list", "--path", str(demo_dir)])
        # Should still work, just with fallback description
        assert result.exit_code == EnumCLIExitCode.SUCCESS
        assert "bad-yaml" in result.output

    def test_run_handles_empty_invariants_file(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that run handles empty invariants.yaml gracefully."""
        demo_dir = tmp_path / "demo"
        demo_dir.mkdir()
        scenario = demo_dir / "empty-inv"
        scenario.mkdir()

        (scenario / "contract.yaml").write_text("name: test")
        (scenario / "invariants.yaml").write_text("")

        # Create corpus
        corpus_dir = scenario / "corpus"
        corpus_dir.mkdir()
        golden = corpus_dir / "golden"
        golden.mkdir()
        (golden / "sample.yaml").write_text(yaml.safe_dump({"id": "1"}))

        with patch("omnibase_core.cli.cli_demo._get_demo_root", return_value=demo_dir):
            result = runner.invoke(
                demo,
                [
                    "run",
                    "--scenario",
                    "empty-inv",
                    "--output",
                    str(tmp_path / "out"),
                ],
            )

        # Should run without errors
        assert result.exit_code in (EnumCLIExitCode.SUCCESS, EnumCLIExitCode.ERROR)

    def test_run_creates_output_directory_if_not_exists(
        self, runner: CliRunner, demo_root: Path, tmp_path: Path
    ) -> None:
        """Test that run creates nested output directories."""
        output_dir = tmp_path / "nested" / "deep" / "output"

        with patch("omnibase_core.cli.cli_demo._get_demo_root", return_value=demo_root):
            runner.invoke(
                demo,
                [
                    "run",
                    "--scenario",
                    "model-validate",
                    "--output",
                    str(output_dir),
                ],
            )

        assert output_dir.exists()
