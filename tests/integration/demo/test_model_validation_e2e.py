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

# Fixture root relative to repository root
DEMO_FIXTURES_ROOT = Path(__file__).parent.parent.parent.parent / "examples" / "demo"
MODEL_VALIDATE_ROOT = DEMO_FIXTURES_ROOT / "model-validate"

# Expected golden sample filenames (tickets 001-010)
GOLDEN_SAMPLE_FILENAMES: tuple[str, ...] = (
    "ticket_001_billing_refund.yaml",
    "ticket_002_billing_payment.yaml",
    "ticket_003_account_access.yaml",
    "ticket_004_account_profile.yaml",
    "ticket_005_technical_bug.yaml",
    "ticket_006_technical_howto.yaml",
    "ticket_007_billing_refund_enterprise.yaml",
    "ticket_008_account_access_chat.yaml",
    "ticket_009_technical_bug_detailed.yaml",
    "ticket_010_billing_payment_pro.yaml",
)

# Expected edge-case sample filenames (tickets 011-015)
# Note: ticket_013 (confidence 0.58) and ticket_014 (confidence 0.62)
# are specifically tested for confidence threshold failures
EDGE_CASE_SAMPLE_FILENAMES: tuple[str, ...] = (
    "ticket_011_malformed_date.yaml",
    "ticket_012_missing_fields.yaml",
    "ticket_013_unicode_body.yaml",
    "ticket_014_borderline_content.yaml",
    "ticket_015_negative_sentiment.yaml",
)

# Sample ID to name mapping for mock responses (all 15 samples)
# Used to generate response filenames like "response_001_billing_refund.json"
SAMPLE_ID_NAME_MAPPING: tuple[tuple[int, str], ...] = (
    (1, "billing_refund"),
    (2, "billing_payment"),
    (3, "account_access"),
    (4, "account_profile"),
    (5, "technical_bug"),
    (6, "technical_howto"),
    (7, "billing_refund_enterprise"),
    (8, "account_access_chat"),
    (9, "technical_bug_detailed"),
    (10, "billing_payment_pro"),
    (11, "malformed_date"),
    (12, "missing_fields"),
    (13, "unicode_body"),
    (14, "borderline_content"),
    (15, "negative_sentiment"),
)


@pytest.fixture
def runner() -> CliRunner:
    """Create CLI runner."""
    return CliRunner()


class TestDemoFixtureValidation:
    """Validate that required fixtures exist before running E2E tests.

    These tests ensure that the fixture files in examples/demo/model-validate/
    are present. If fixtures are moved or deleted, these tests will fail with
    clear error messages indicating which files are missing.

    This provides early detection of missing fixtures rather than cryptic
    errors during actual test execution.
    """

    def test_model_validate_root_exists(self) -> None:
        """The model-validate scenario directory must exist."""
        assert MODEL_VALIDATE_ROOT.exists(), (
            f"Missing fixture directory: {MODEL_VALIDATE_ROOT}\n"
            "The model-validate demo scenario requires this directory."
        )
        assert MODEL_VALIDATE_ROOT.is_dir(), (
            f"Expected directory but found file: {MODEL_VALIDATE_ROOT}"
        )

    def test_required_config_files_exist(self) -> None:
        """Contract and invariants config files must exist."""
        required_configs = [
            ("contract.yaml", "Defines the validation contract schema"),
            ("invariants.yaml", "Defines validation invariants and thresholds"),
        ]
        missing = []
        for filename, description in required_configs:
            path = MODEL_VALIDATE_ROOT / filename
            if not path.exists():
                missing.append(f"  - {filename}: {description}")

        assert not missing, (
            f"Missing required config files in {MODEL_VALIDATE_ROOT}:\n"
            + "\n".join(missing)
        )

    def test_corpus_directories_exist(self) -> None:
        """Corpus directories for golden and edge-case samples must exist."""
        corpus_root = MODEL_VALIDATE_ROOT / "corpus"
        assert corpus_root.exists(), (
            f"Missing corpus directory: {corpus_root}\n"
            "The corpus contains sample tickets for validation testing."
        )

        required_subdirs = [
            ("golden", "High-confidence samples that should pass validation"),
            ("edge-cases", "Samples designed to test boundary conditions"),
        ]
        missing = []
        for dirname, description in required_subdirs:
            path = corpus_root / dirname
            if not path.exists() or not path.is_dir():
                missing.append(f"  - corpus/{dirname}/: {description}")

        assert not missing, "Missing required corpus subdirectories:\n" + "\n".join(
            missing
        )

    def test_golden_corpus_samples_exist(self) -> None:
        """Golden corpus must contain expected sample files."""
        golden_dir = MODEL_VALIDATE_ROOT / "corpus" / "golden"
        if not golden_dir.exists():
            pytest.skip(
                "Golden directory missing (covered by test_corpus_directories_exist)"
            )

        # These samples are referenced in test assertions and mock responses
        missing = [s for s in GOLDEN_SAMPLE_FILENAMES if not (golden_dir / s).exists()]

        assert not missing, (
            f"Missing golden corpus samples in {golden_dir}:\n"
            + "\n".join(f"  - {s}" for s in missing)
        )

    def test_edge_case_corpus_samples_exist(self) -> None:
        """Edge-case corpus must contain expected sample files."""
        edge_cases_dir = MODEL_VALIDATE_ROOT / "corpus" / "edge-cases"
        if not edge_cases_dir.exists():
            pytest.skip(
                "Edge-cases directory missing (covered by test_corpus_directories_exist)"
            )

        # These samples are specifically tested for failures (TKT-2024-013, TKT-2024-014)
        missing = [
            s for s in EDGE_CASE_SAMPLE_FILENAMES if not (edge_cases_dir / s).exists()
        ]

        assert not missing, (
            f"Missing edge-case corpus samples in {edge_cases_dir}:\n"
            + "\n".join(f"  - {s}" for s in missing)
            + "\n\nNote: ticket_013 and ticket_014 are specifically tested "
            "for confidence threshold failures."
        )

    def test_mock_responses_directories_exist(self) -> None:
        """Mock response directories for baseline and candidate must exist."""
        mock_root = MODEL_VALIDATE_ROOT / "mock-responses"
        assert mock_root.exists(), (
            f"Missing mock-responses directory: {mock_root}\n"
            "Mock responses are required for running tests without API keys."
        )

        required_subdirs = [
            ("baseline", "Responses from the baseline model for comparison"),
            ("candidate", "Responses from the candidate model being validated"),
        ]
        missing = []
        for dirname, description in required_subdirs:
            path = mock_root / dirname
            if not path.exists() or not path.is_dir():
                missing.append(f"  - mock-responses/{dirname}/: {description}")

        assert not missing, (
            "Missing required mock-response subdirectories:\n" + "\n".join(missing)
        )

    def test_baseline_mock_responses_exist(self) -> None:
        """Baseline mock responses must exist for all corpus samples."""
        baseline_dir = MODEL_VALIDATE_ROOT / "mock-responses" / "baseline"
        if not baseline_dir.exists():
            pytest.skip(
                "Baseline directory missing (covered by test_mock_responses_directories_exist)"
            )

        # One response per corpus sample (golden + edge-cases)
        expected_responses = [
            f"response_{i:03d}_{name}.json" for i, name in SAMPLE_ID_NAME_MAPPING
        ]
        missing = [r for r in expected_responses if not (baseline_dir / r).exists()]

        assert not missing, (
            f"Missing baseline mock responses in {baseline_dir}:\n"
            + "\n".join(f"  - {r}" for r in missing)
        )

    def test_candidate_mock_responses_exist(self) -> None:
        """Candidate mock responses must exist for all corpus samples."""
        candidate_dir = MODEL_VALIDATE_ROOT / "mock-responses" / "candidate"
        if not candidate_dir.exists():
            pytest.skip(
                "Candidate directory missing (covered by test_mock_responses_directories_exist)"
            )

        # One response per corpus sample (golden + edge-cases)
        expected_responses = [
            f"response_{i:03d}_{name}.json" for i, name in SAMPLE_ID_NAME_MAPPING
        ]
        missing = [r for r in expected_responses if not (candidate_dir / r).exists()]

        assert not missing, (
            f"Missing candidate mock responses in {candidate_dir}:\n"
            + "\n".join(f"  - {r}" for r in missing)
        )

    def test_fixture_counts_match(self) -> None:
        """Verify corpus samples and mock responses are in sync.

        Each corpus sample should have corresponding baseline and candidate
        mock responses. A mismatch indicates incomplete fixture setup.
        """
        corpus_golden = MODEL_VALIDATE_ROOT / "corpus" / "golden"
        corpus_edge = MODEL_VALIDATE_ROOT / "corpus" / "edge-cases"
        baseline = MODEL_VALIDATE_ROOT / "mock-responses" / "baseline"
        candidate = MODEL_VALIDATE_ROOT / "mock-responses" / "candidate"

        # Skip if directories don't exist (covered by other tests)
        if not all(
            d.exists() for d in [corpus_golden, corpus_edge, baseline, candidate]
        ):
            pytest.skip("Fixture directories missing (covered by other tests)")

        corpus_count = len(list(corpus_golden.glob("*.yaml"))) + len(
            list(corpus_edge.glob("*.yaml"))
        )
        baseline_count = len(list(baseline.glob("*.json")))
        candidate_count = len(list(candidate.glob("*.json")))

        mismatches = []
        if baseline_count != corpus_count:
            mismatches.append(
                f"  - Baseline responses ({baseline_count}) != corpus samples ({corpus_count})"
            )
        if candidate_count != corpus_count:
            mismatches.append(
                f"  - Candidate responses ({candidate_count}) != corpus samples ({corpus_count})"
            )

        assert not mismatches, (
            "Fixture count mismatch detected:\n"
            + "\n".join(mismatches)
            + "\n\nEach corpus sample needs both baseline and candidate mock responses."
        )


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

        Expected exit code is ERROR (1) because the corpus contains 2 edge-case
        samples (TKT-2024-013 and TKT-2024-014) with confidence below the 0.70
        threshold, resulting in invariant failures. This is expected behavior -
        the demo intentionally includes failing samples to demonstrate validation.
        """
        result = runner.invoke(
            cli,
            ["demo", "run", "--scenario", "model-validate", "--output", str(tmp_path)],
        )
        # Exit code ERROR (1) expected: 2 samples fail confidence threshold invariant
        assert result.exit_code == EnumCLIExitCode.ERROR
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
