"""Tests for baseline enforcement in cross-repo validation.

Verifies that baseline suppression works correctly:
- Baselined violations are suppressed (INFO severity)
- New violations still fail
- Suppressed violations appear in output
- is_valid only considers unsuppressed violations

Related ticket: OMN-1774
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.validation.model_violation_baseline import (
    ModelBaselineGenerator,
    ModelBaselineViolation,
    ModelViolationBaseline,
)
from omnibase_core.validation.cross_repo.cli import (
    _is_suppressed,
    main,
    print_json_report,
    print_text_report,
)
from omnibase_core.validation.cross_repo.engine import (
    run_cross_repo_validation,
)
from omnibase_core.validation.cross_repo.policy_loader import load_policy

FIXTURES_DIR = (
    Path(__file__).parent.parent.parent.parent / "fixtures" / "cross_repo_validation"
)


def _create_baseline_with_fingerprints(
    fingerprints: list[str],
    policy_id: str = "test_policy",
) -> ModelViolationBaseline:
    """Helper to create a baseline with specific fingerprints."""
    violations = [
        ModelBaselineViolation(
            fingerprint=fp,
            rule_id="repo_boundaries",
            file_path="src/file.py",
            symbol="test.import",
            message="Test violation",
            first_seen=datetime(2026, 1, 31, 22, 0, 0, tzinfo=UTC),
        )
        for fp in fingerprints
    ]
    return ModelViolationBaseline(
        schema_version="1.0",
        created_at=datetime(2026, 1, 31, 22, 0, 0, tzinfo=UTC),
        policy_id=policy_id,
        generator=ModelBaselineGenerator(
            tool="test",
            version="1.0.0",
        ),
        violations=violations,
    )


class TestIsSupressedHelper:
    """Tests for _is_suppressed helper function."""

    def test_suppressed_true(self) -> None:
        """Test detection of suppressed issue."""
        issue = ModelValidationIssue(
            severity=EnumSeverity.INFO,
            message="Test message",
            context={"suppressed": "true"},
        )
        assert _is_suppressed(issue) is True

    def test_suppressed_false(self) -> None:
        """Test detection of unsuppressed issue."""
        issue = ModelValidationIssue(
            severity=EnumSeverity.ERROR,
            message="Test message",
            context={"suppressed": "false"},
        )
        assert _is_suppressed(issue) is False

    def test_no_context(self) -> None:
        """Test issue without context is not suppressed."""
        issue = ModelValidationIssue(
            severity=EnumSeverity.ERROR,
            message="Test message",
        )
        assert _is_suppressed(issue) is False

    def test_context_without_suppressed_key(self) -> None:
        """Test issue with context but no suppressed key."""
        issue = ModelValidationIssue(
            severity=EnumSeverity.ERROR,
            message="Test message",
            context={"other_key": "value"},
        )
        assert _is_suppressed(issue) is False


class TestEngineBaselineSuppression:
    """Tests for baseline suppression in the validation engine."""

    def test_no_baseline_marks_all_unsuppressed(self) -> None:
        """Test that without baseline, all issues are marked unsuppressed."""
        policy_path = FIXTURES_DIR / "policies" / "fake_app_policy.yaml"
        fake_app_dir = FIXTURES_DIR / "fake_app" / "src" / "fake_app"

        if not policy_path.exists():
            pytest.skip("Fixture not found")

        policy = load_policy(policy_path)
        result = run_cross_repo_validation(fake_app_dir, policy, baseline=None)

        # All issues should have suppressed: false
        for issue in result.issues:
            assert issue.context is not None
            assert issue.context.get("suppressed") == "false"

    def test_baselined_violation_is_suppressed(self) -> None:
        """Test that baselined violations are marked as suppressed."""
        policy_path = FIXTURES_DIR / "policies" / "fake_app_policy.yaml"
        fake_app_dir = FIXTURES_DIR / "fake_app" / "src" / "fake_app"

        if not policy_path.exists():
            pytest.skip("Fixture not found")

        policy = load_policy(policy_path)

        # First run without baseline to get fingerprints
        result_without_baseline = run_cross_repo_validation(
            fake_app_dir, policy, baseline=None
        )

        # Get fingerprints from violations
        fingerprints = []
        for issue in result_without_baseline.issues:
            if issue.context and "fingerprint" in issue.context:
                fingerprints.append(issue.context["fingerprint"])

        if not fingerprints:
            pytest.skip("No violations found in fixture")

        # Create baseline with first fingerprint
        baseline = _create_baseline_with_fingerprints(fingerprints[:1])

        # Run with baseline
        result_with_baseline = run_cross_repo_validation(
            fake_app_dir, policy, baseline=baseline
        )

        # Find the suppressed issue
        suppressed_issues = [
            i for i in result_with_baseline.issues if _is_suppressed(i)
        ]
        assert len(suppressed_issues) >= 1

        # Suppressed issues should have INFO severity
        for issue in suppressed_issues:
            assert issue.severity == EnumSeverity.INFO

    def test_baselined_violation_downgrades_severity(self) -> None:
        """Test that baselined violations are downgraded to INFO."""
        policy_path = FIXTURES_DIR / "policies" / "fake_app_policy.yaml"
        fake_app_dir = FIXTURES_DIR / "fake_app" / "src" / "fake_app"

        if not policy_path.exists():
            pytest.skip("Fixture not found")

        policy = load_policy(policy_path)

        # First run without baseline to get original severities
        result_without = run_cross_repo_validation(fake_app_dir, policy, baseline=None)

        # Collect fingerprints of ERROR level issues
        error_fingerprints = []
        for issue in result_without.issues:
            if issue.severity == EnumSeverity.ERROR:
                if issue.context and "fingerprint" in issue.context:
                    error_fingerprints.append(issue.context["fingerprint"])

        if not error_fingerprints:
            pytest.skip("No ERROR violations found in fixture")

        # Create baseline with all error fingerprints
        baseline = _create_baseline_with_fingerprints(error_fingerprints)

        # Run with baseline
        result_with = run_cross_repo_validation(fake_app_dir, policy, baseline=baseline)

        # Find issues that were baselined
        for issue in result_with.issues:
            if issue.context and issue.context.get("fingerprint") in error_fingerprints:
                # These should now be INFO (not ERROR)
                assert issue.severity == EnumSeverity.INFO
                assert issue.context.get("suppressed") == "true"

    def test_new_violation_still_fails(self) -> None:
        """Test that new (non-baselined) violations still cause failure."""
        policy_path = FIXTURES_DIR / "policies" / "fake_app_policy.yaml"
        fake_app_dir = FIXTURES_DIR / "fake_app" / "src" / "fake_app"

        if not policy_path.exists():
            pytest.skip("Fixture not found")

        policy = load_policy(policy_path)

        # Create empty baseline (no violations suppressed)
        baseline = _create_baseline_with_fingerprints([])

        # Run with empty baseline
        result = run_cross_repo_validation(fake_app_dir, policy, baseline=baseline)

        # Should still fail because no violations are suppressed
        assert result.is_valid is False

        # All issues should be unsuppressed
        unsuppressed = [i for i in result.issues if not _is_suppressed(i)]
        assert len(unsuppressed) >= 1

    def test_suppressed_violations_still_appear_in_output(self) -> None:
        """Test that suppressed violations are NOT hidden - they appear in output."""
        policy_path = FIXTURES_DIR / "policies" / "fake_app_policy.yaml"
        fake_app_dir = FIXTURES_DIR / "fake_app" / "src" / "fake_app"

        if not policy_path.exists():
            pytest.skip("Fixture not found")

        policy = load_policy(policy_path)

        # First run to get fingerprints
        result_without = run_cross_repo_validation(fake_app_dir, policy, baseline=None)
        initial_count = len(result_without.issues)

        if initial_count == 0:
            pytest.skip("No violations found in fixture")

        # Get all fingerprints
        fingerprints = [
            i.context["fingerprint"]
            for i in result_without.issues
            if i.context and "fingerprint" in i.context
        ]

        # Create baseline suppressing all
        baseline = _create_baseline_with_fingerprints(fingerprints)

        # Run with baseline
        result_with = run_cross_repo_validation(fake_app_dir, policy, baseline=baseline)

        # Issue count should remain the same (suppressed != hidden)
        assert len(result_with.issues) == initial_count

    def test_is_valid_only_considers_unsuppressed(self) -> None:
        """Test that is_valid only considers unsuppressed violations."""
        policy_path = FIXTURES_DIR / "policies" / "fake_app_policy.yaml"
        fake_app_dir = FIXTURES_DIR / "fake_app" / "src" / "fake_app"

        if not policy_path.exists():
            pytest.skip("Fixture not found")

        policy = load_policy(policy_path)

        # First run without baseline - should fail
        result_without = run_cross_repo_validation(fake_app_dir, policy, baseline=None)
        assert result_without.is_valid is False

        # Get all fingerprints
        fingerprints = [
            i.context["fingerprint"]
            for i in result_without.issues
            if i.context
            and "fingerprint" in i.context
            and i.severity in (EnumSeverity.ERROR, EnumSeverity.CRITICAL)
        ]

        if not fingerprints:
            pytest.skip("No ERROR/CRITICAL violations found")

        # Create baseline suppressing all error-level violations
        baseline = _create_baseline_with_fingerprints(fingerprints)

        # Run with baseline - should pass
        result_with = run_cross_repo_validation(fake_app_dir, policy, baseline=baseline)

        # Should now pass because all errors are suppressed
        assert result_with.is_valid is True

    def test_partial_baseline_some_pass_some_fail(self) -> None:
        """Test that partial baseline suppresses only matching violations."""
        policy_path = FIXTURES_DIR / "policies" / "fake_app_policy.yaml"
        fake_app_dir = FIXTURES_DIR / "fake_app" / "src" / "fake_app"

        if not policy_path.exists():
            pytest.skip("Fixture not found")

        policy = load_policy(policy_path)

        # First run to get all fingerprints
        result = run_cross_repo_validation(fake_app_dir, policy, baseline=None)

        error_fingerprints = [
            i.context["fingerprint"]
            for i in result.issues
            if i.context
            and "fingerprint" in i.context
            and i.severity == EnumSeverity.ERROR
        ]

        if len(error_fingerprints) < 2:
            pytest.skip("Need at least 2 ERROR violations for this test")

        # Baseline only first half
        baseline = _create_baseline_with_fingerprints(
            error_fingerprints[: len(error_fingerprints) // 2]
        )

        # Run with partial baseline
        result_partial = run_cross_repo_validation(
            fake_app_dir, policy, baseline=baseline
        )

        # Some should be suppressed, some not
        suppressed = [i for i in result_partial.issues if _is_suppressed(i)]
        unsuppressed = [i for i in result_partial.issues if not _is_suppressed(i)]

        assert len(suppressed) >= 1
        assert len(unsuppressed) >= 1


class TestTextReportSuppression:
    """Tests for suppression display in text reports."""

    def test_suppressed_marker_in_text_output(self) -> None:
        """Test that [SUPPRESSED] marker appears in text output."""
        policy_path = FIXTURES_DIR / "policies" / "fake_app_policy.yaml"
        fake_app_dir = FIXTURES_DIR / "fake_app" / "src" / "fake_app"

        if not policy_path.exists():
            pytest.skip("Fixture not found")

        policy = load_policy(policy_path)

        # Get fingerprints
        result_without = run_cross_repo_validation(fake_app_dir, policy, baseline=None)
        fingerprints = [
            i.context["fingerprint"]
            for i in result_without.issues
            if i.context and "fingerprint" in i.context
        ]

        if not fingerprints:
            pytest.skip("No violations found")

        # Create baseline and run
        baseline = _create_baseline_with_fingerprints(fingerprints[:1])
        result = run_cross_repo_validation(fake_app_dir, policy, baseline=baseline)

        # Capture text output
        output = StringIO()
        with patch("sys.stdout", output):
            print_text_report(result, policy.policy_id)

        text_output = output.getvalue()

        # Should contain [SUPPRESSED] marker
        assert "[SUPPRESSED]" in text_output

    def test_text_report_suppressed_counts(self) -> None:
        """Test that text report shows correct suppressed counts."""
        policy_path = FIXTURES_DIR / "policies" / "fake_app_policy.yaml"
        fake_app_dir = FIXTURES_DIR / "fake_app" / "src" / "fake_app"

        if not policy_path.exists():
            pytest.skip("Fixture not found")

        policy = load_policy(policy_path)

        # Get all fingerprints
        result_without = run_cross_repo_validation(fake_app_dir, policy, baseline=None)
        fingerprints = [
            i.context["fingerprint"]
            for i in result_without.issues
            if i.context and "fingerprint" in i.context
        ]

        if not fingerprints:
            pytest.skip("No violations found")

        # Suppress half
        suppress_count = len(fingerprints) // 2 or 1
        baseline = _create_baseline_with_fingerprints(fingerprints[:suppress_count])
        result = run_cross_repo_validation(fake_app_dir, policy, baseline=baseline)

        # Capture text output
        output = StringIO()
        with patch("sys.stdout", output):
            print_text_report(result, policy.policy_id)

        text_output = output.getvalue()

        # Should show correct suppressed count
        assert f"Suppressed: {suppress_count}" in text_output


class TestJsonReportSuppression:
    """Tests for suppression display in JSON reports."""

    def test_json_report_includes_suppressed_field(self) -> None:
        """Test that JSON report includes suppressed field on each issue."""
        policy_path = FIXTURES_DIR / "policies" / "fake_app_policy.yaml"
        fake_app_dir = FIXTURES_DIR / "fake_app" / "src" / "fake_app"

        if not policy_path.exists():
            pytest.skip("Fixture not found")

        policy = load_policy(policy_path)
        result = run_cross_repo_validation(fake_app_dir, policy, baseline=None)

        # Capture JSON output
        output = StringIO()
        with patch("sys.stdout", output):
            print_json_report(result, policy.policy_id)

        json_output = json.loads(output.getvalue())

        # Each issue should have suppressed field
        for issue in json_output["issues"]:
            assert "suppressed" in issue
            assert isinstance(issue["suppressed"], bool)

    def test_json_report_suppressed_counts(self) -> None:
        """Test that JSON report has correct suppressed counts."""
        policy_path = FIXTURES_DIR / "policies" / "fake_app_policy.yaml"
        fake_app_dir = FIXTURES_DIR / "fake_app" / "src" / "fake_app"

        if not policy_path.exists():
            pytest.skip("Fixture not found")

        policy = load_policy(policy_path)

        # Get fingerprints
        result_without = run_cross_repo_validation(fake_app_dir, policy, baseline=None)
        fingerprints = [
            i.context["fingerprint"]
            for i in result_without.issues
            if i.context and "fingerprint" in i.context
        ]

        if not fingerprints:
            pytest.skip("No violations found")

        # Suppress some
        suppress_count = len(fingerprints) // 2 or 1
        baseline = _create_baseline_with_fingerprints(fingerprints[:suppress_count])
        result = run_cross_repo_validation(fake_app_dir, policy, baseline=baseline)

        # Capture JSON output
        output = StringIO()
        with patch("sys.stdout", output):
            print_json_report(result, policy.policy_id)

        json_output = json.loads(output.getvalue())
        counts = json_output["counts"]

        # Verify counts
        assert counts["suppressed"] == suppress_count
        assert counts["unsuppressed"] == counts["total"] - suppress_count

        # Verify individual issues match counts
        suppressed_in_issues = sum(1 for i in json_output["issues"] if i["suppressed"])
        assert suppressed_in_issues == counts["suppressed"]


class TestCLIBaselineEnforce:
    """Tests for --baseline-enforce CLI flag."""

    def test_baseline_enforce_flag_exists(self) -> None:
        """Test that --baseline-enforce flag is accepted."""
        from omnibase_core.validation.cross_repo.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(
            ["--policy", "p.yaml", "--baseline-enforce", "baseline.yaml"]
        )
        assert args.baseline_enforce == Path("baseline.yaml")

    def test_baseline_enforce_mutually_exclusive_with_write(self) -> None:
        """Test that --baseline-enforce and --baseline-write are mutually exclusive."""
        from omnibase_core.validation.cross_repo.cli import create_parser

        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(
                [
                    "--policy",
                    "p.yaml",
                    "--baseline-enforce",
                    "enforce.yaml",
                    "--baseline-write",
                    "write.yaml",
                ]
            )

    def test_baseline_enforce_suppresses_violations(self, tmp_path: Path) -> None:
        """Test that --baseline-enforce suppresses matching violations."""
        policy_path = FIXTURES_DIR / "policies" / "fake_app_policy.yaml"
        fake_app_dir = FIXTURES_DIR / "fake_app" / "src" / "fake_app"
        baseline_path = tmp_path / "baseline.yaml"

        if not policy_path.exists():
            pytest.skip("Fixture not found")

        # First, write a baseline
        with patch(
            "sys.argv",
            [
                "cli",
                "--policy",
                str(policy_path),
                "--baseline-write",
                str(baseline_path),
                "--format",
                "json",
                str(fake_app_dir),
            ],
        ):
            with patch("sys.stdout", new_callable=StringIO):
                main()

        assert baseline_path.exists()

        # Now enforce against the baseline - should PASS
        with patch(
            "sys.argv",
            [
                "cli",
                "--policy",
                str(policy_path),
                "--baseline-enforce",
                str(baseline_path),
                "--format",
                "json",
                str(fake_app_dir),
            ],
        ):
            output = StringIO()
            with patch("sys.stdout", output):
                exit_code = main()

        # Should pass because all violations are baselined
        assert exit_code == 0

        json_output = json.loads(output.getvalue())
        assert json_output["is_valid"] is True

    def test_baseline_enforce_new_violation_fails(self, tmp_path: Path) -> None:
        """Test that new violations not in baseline still fail."""
        policy_path = FIXTURES_DIR / "policies" / "fake_app_policy.yaml"
        fake_app_dir = FIXTURES_DIR / "fake_app" / "src" / "fake_app"
        baseline_path = tmp_path / "baseline.yaml"

        if not policy_path.exists():
            pytest.skip("Fixture not found")

        # Create empty baseline (no violations suppressed)
        empty_baseline = _create_baseline_with_fingerprints([])
        from omnibase_core.validation.cross_repo.baseline_io import write_baseline

        write_baseline(baseline_path, empty_baseline)

        # Enforce against empty baseline - should FAIL
        with patch(
            "sys.argv",
            [
                "cli",
                "--policy",
                str(policy_path),
                "--baseline-enforce",
                str(baseline_path),
                "--format",
                "json",
                str(fake_app_dir),
            ],
        ):
            output = StringIO()
            with patch("sys.stdout", output):
                exit_code = main()

        # Should fail because violations are not baselined
        assert exit_code == 1

        json_output = json.loads(output.getvalue())
        assert json_output["is_valid"] is False

    def test_baseline_enforce_missing_file_exits_2(self) -> None:
        """Test that missing baseline file causes exit code 2."""
        policy_path = FIXTURES_DIR / "policies" / "fake_app_policy.yaml"
        fake_app_dir = FIXTURES_DIR / "fake_app" / "src" / "fake_app"

        if not policy_path.exists():
            pytest.skip("Fixture not found")

        with patch(
            "sys.argv",
            [
                "cli",
                "--policy",
                str(policy_path),
                "--baseline-enforce",
                "/nonexistent/baseline.yaml",
                "--format",
                "json",
                str(fake_app_dir),
            ],
        ):
            output = StringIO()
            with patch("sys.stdout", output):
                exit_code = main()

        # Should exit with code 2 (configuration error)
        assert exit_code == 2

    def test_baseline_enforce_invalid_yaml_exits_2(self, tmp_path: Path) -> None:
        """Test that invalid baseline YAML causes exit code 2."""
        policy_path = FIXTURES_DIR / "policies" / "fake_app_policy.yaml"
        fake_app_dir = FIXTURES_DIR / "fake_app" / "src" / "fake_app"
        baseline_path = tmp_path / "invalid.yaml"

        if not policy_path.exists():
            pytest.skip("Fixture not found")

        # Write invalid YAML
        baseline_path.write_text("{ invalid yaml [[[")

        with patch(
            "sys.argv",
            [
                "cli",
                "--policy",
                str(policy_path),
                "--baseline-enforce",
                str(baseline_path),
                "--format",
                "json",
                str(fake_app_dir),
            ],
        ):
            output = StringIO()
            with patch("sys.stdout", output):
                exit_code = main()

        # Should exit with code 2 (configuration error)
        assert exit_code == 2


class TestBaselineWithStaleEntries:
    """Tests for baseline behavior with stale entries."""

    def test_stale_baseline_entries_are_ignored(self, tmp_path: Path) -> None:
        """Test that stale baseline entries don't cause problems."""
        policy_path = FIXTURES_DIR / "policies" / "fake_app_policy.yaml"
        fake_app_dir = FIXTURES_DIR / "fake_app" / "src" / "fake_app"

        if not policy_path.exists():
            pytest.skip("Fixture not found")

        policy = load_policy(policy_path)

        # Create baseline with fake fingerprints that don't match anything
        stale_baseline = _create_baseline_with_fingerprints(
            ["fake123456789012", "fake987654321098"]
        )

        # Run with stale baseline
        result = run_cross_repo_validation(
            fake_app_dir, policy, baseline=stale_baseline
        )

        # Should still work - stale entries just don't match
        # All current violations should be unsuppressed
        for issue in result.issues:
            assert issue.context is not None
            assert issue.context.get("suppressed") == "false"
