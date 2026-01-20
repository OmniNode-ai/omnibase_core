"""E2E integration tests for model-validate demo scenario.

These tests verify the demo CLI works correctly with real fixtures from
examples/demo/model-validate/. No mocking is used - all tests run against
actual corpus samples and mock responses.

Tests cover:
- `onex demo list`: Listing available scenarios including model-validate
- `onex demo run --scenario model-validate`: Full execution with invariant evaluation
- Output bundle structure (report.json, report.md, run_manifest.yaml)
- Deterministic execution with --seed
- Specific failure detection (TKT-2024-013, TKT-2024-014)

Related Ticket: OMN-1397
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from omnibase_core.cli.cli_commands import cli
from omnibase_core.enums.enum_cli_exit_code import EnumCLIExitCode

pytestmark = pytest.mark.integration


@pytest.fixture
def runner() -> CliRunner:
    """Create CLI runner."""
    return CliRunner()


class TestDemoListCommand:
    """Tests for onex demo list command."""

    def test_demo_list_shows_scenarios(self, runner: CliRunner) -> None:
        """onex demo list returns available scenarios including model-validate."""
        result = runner.invoke(cli, ["demo", "list"])
        assert result.exit_code == EnumCLIExitCode.SUCCESS
        assert "model-validate" in result.output


class TestDemoRunCommand:
    """Tests for onex demo run command with real fixtures."""

    def test_demo_run_mock_mode_succeeds(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Demo runs successfully in mock mode with no API keys.

        The demo uses mock responses from examples/demo/model-validate/mock-responses/
        and should produce valid output without requiring external API calls.
        """
        result = runner.invoke(
            cli,
            ["demo", "run", "--scenario", "model-validate", "--output", str(tmp_path)],
        )
        # Exit code 1 is expected because there are failures (not errors)
        # The demo has 2 samples with confidence below threshold
        assert result.exit_code in (EnumCLIExitCode.SUCCESS, EnumCLIExitCode.ERROR)
        assert (tmp_path / "report.json").exists()
        assert (tmp_path / "report.md").exists()
        assert (tmp_path / "run_manifest.yaml").exists()

    def test_demo_run_produces_correct_bundle_structure(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Bundle contains all required artifacts.

        The output bundle should include:
        - run_manifest.yaml: Execution metadata
        - inputs/: Corpus samples copied for reproducibility
        - outputs/: Per-sample evaluation results
        - report.md: Human-readable summary
        - report.json: Machine-readable canonical report
        """
        runner.invoke(
            cli,
            ["demo", "run", "--scenario", "model-validate", "--output", str(tmp_path)],
        )
        assert (tmp_path / "run_manifest.yaml").exists()
        assert (tmp_path / "inputs").is_dir()
        assert (tmp_path / "outputs").is_dir()
        assert (tmp_path / "report.md").exists()
        assert (tmp_path / "report.json").exists()

    def test_demo_run_seed_produces_deterministic_output(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Same seed produces identical results.

        Running the demo twice with the same seed should produce
        identical pass rates and failure counts.
        """
        out1 = tmp_path / "run1"
        out2 = tmp_path / "run2"

        runner.invoke(
            cli,
            [
                "demo",
                "run",
                "--scenario",
                "model-validate",
                "--seed",
                "42",
                "--output",
                str(out1),
            ],
        )
        runner.invoke(
            cli,
            [
                "demo",
                "run",
                "--scenario",
                "model-validate",
                "--seed",
                "42",
                "--output",
                str(out2),
            ],
        )

        r1 = json.loads((out1 / "report.json").read_text())
        r2 = json.loads((out2 / "report.json").read_text())

        assert r1["summary"]["pass_rate"] == r2["summary"]["pass_rate"]
        assert r1["summary"]["failed"] == r2["summary"]["failed"]

    def test_demo_run_detects_confidence_failures(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Demo correctly identifies confidence threshold failures.

        The model-validate scenario has invariants with confidence_min=0.70
        and golden_confidence_min=0.85. Edge case samples TKT-2024-013 (0.58)
        and TKT-2024-014 (0.62) should fail the confidence threshold.
        """
        runner.invoke(
            cli,
            ["demo", "run", "--scenario", "model-validate", "--output", str(tmp_path)],
        )

        report = json.loads((tmp_path / "report.json").read_text())

        # Expect 2 failures from edge cases with low confidence
        assert (
            report["summary"]["invariant_results"]["confidence_threshold"]["failed"]
            == 2
        )
        assert report["summary"]["recommendation"] in (
            "promote",
            "promote_with_review",
            "reject",
        )

    def test_demo_run_report_contains_failure_details(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Report includes details for each failure.

        Each failure in the report should include:
        - sample_id: The failing sample's identifier
        - invariant_id: Which invariant was violated
        """
        runner.invoke(
            cli,
            ["demo", "run", "--scenario", "model-validate", "--output", str(tmp_path)],
        )

        report = json.loads((tmp_path / "report.json").read_text())

        for failure in report["summary"]["failures"]:
            assert "sample_id" in failure
            assert "invariant_id" in failure

    def test_demo_run_manifest_captures_config(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """run_manifest.yaml captures execution config.

        The manifest should record the scenario name, seed, and mode
        for reproducibility and debugging.
        """
        runner.invoke(
            cli,
            [
                "demo",
                "run",
                "--scenario",
                "model-validate",
                "--seed",
                "123",
                "--output",
                str(tmp_path),
            ],
        )

        manifest = yaml.safe_load((tmp_path / "run_manifest.yaml").read_text())

        assert manifest["scenario"] == "model-validate"
        assert manifest["seed"] == 123
        assert manifest["live_mode"] is False

    def test_demo_run_report_has_schema_version(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Report includes schema_version for future compatibility.

        The canonical report schema includes a version field to support
        backward compatibility as the schema evolves.
        """
        runner.invoke(
            cli,
            ["demo", "run", "--scenario", "model-validate", "--output", str(tmp_path)],
        )

        report = json.loads((tmp_path / "report.json").read_text())
        # schema_version is a ModelSemVer, serialized as dict
        assert report["schema_version"]["major"] == 1
        assert report["schema_version"]["minor"] == 0
        assert report["schema_version"]["patch"] == 0

    def test_demo_run_known_failing_samples(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Verify specific samples fail as expected.

        Based on mock-responses/candidate/:
        - TKT-2024-013 (unicode_body): confidence 0.58 < 0.70 threshold
        - TKT-2024-014 (borderline_content): confidence 0.62 < 0.70 threshold

        These are edge-case samples that should fail the confidence invariant.
        """
        runner.invoke(
            cli,
            ["demo", "run", "--scenario", "model-validate", "--output", str(tmp_path)],
        )

        report = json.loads((tmp_path / "report.json").read_text())

        failing_sample_ids = {f["sample_id"] for f in report["summary"]["failures"]}

        # These samples have confidence below 0.70 threshold
        assert "TKT-2024-013" in failing_sample_ids  # unicode_body, confidence 0.58
        assert (
            "TKT-2024-014" in failing_sample_ids
        )  # borderline_content, confidence 0.62
