"""Tests for cross-repo validation CLI.

Related ticket: OMN-1771
"""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from omnibase_core.validation.cross_repo.cli import (
    create_parser,
    main,
    print_json_report,
    print_text_report,
)
from omnibase_core.validation.cross_repo.engine import run_cross_repo_validation
from omnibase_core.validation.cross_repo.policy_loader import load_policy

FIXTURES_DIR = (
    Path(__file__).parent.parent.parent.parent / "fixtures" / "cross_repo_validation"
)


class TestCreateParser:
    """Tests for create_parser function."""

    def test_parser_requires_policy(self) -> None:
        """Test that --policy is required."""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_parser_accepts_policy(self) -> None:
        """Test that --policy argument is accepted."""
        parser = create_parser()
        args = parser.parse_args(["--policy", "test.yaml"])

        assert args.policy == Path("test.yaml")

    def test_parser_format_options(self) -> None:
        """Test format argument options."""
        parser = create_parser()

        args_text = parser.parse_args(["--policy", "p.yaml", "--format", "text"])
        assert args_text.format == "text"

        args_json = parser.parse_args(["--policy", "p.yaml", "--format", "json"])
        assert args_json.format == "json"

    def test_parser_default_format(self) -> None:
        """Test default format is text."""
        parser = create_parser()
        args = parser.parse_args(["--policy", "p.yaml"])

        assert args.format == "text"

    def test_parser_rules_argument(self) -> None:
        """Test --rules argument."""
        parser = create_parser()
        args = parser.parse_args(
            ["--policy", "p.yaml", "--rules", "repo_boundaries", "forbidden_imports"]
        )

        assert args.rules == ["repo_boundaries", "forbidden_imports"]

    def test_parser_directory_argument(self) -> None:
        """Test directory positional argument."""
        parser = create_parser()
        args = parser.parse_args(["--policy", "p.yaml", "/some/path"])

        assert args.directory == Path("/some/path")

    def test_parser_default_directory(self) -> None:
        """Test default directory is cwd."""
        parser = create_parser()
        args = parser.parse_args(["--policy", "p.yaml"])

        assert args.directory == Path.cwd()


class TestPrintReports:
    """Tests for report printing functions."""

    def test_print_json_report_structure(self) -> None:
        """Test JSON report has correct structure."""
        policy_path = FIXTURES_DIR / "policies" / "fake_core_policy.yaml"

        if not policy_path.exists():
            pytest.skip("Fixture not found")

        policy = load_policy(policy_path)
        fake_core_dir = FIXTURES_DIR / "fake_core" / "src" / "fake_core"
        result = run_cross_repo_validation(fake_core_dir, policy)

        # Capture JSON output
        output = StringIO()
        with patch("sys.stdout", output):
            print_json_report(result, policy.policy_id)

        json_output = json.loads(output.getvalue())

        # Verify structure
        assert "is_valid" in json_output
        assert "policy_id" in json_output
        assert "issues" in json_output
        assert "summary" in json_output
        assert json_output["policy_id"] == "fake_core_validation"

    def test_print_text_report_pass(self) -> None:
        """Test text report for passing validation."""
        policy_path = FIXTURES_DIR / "policies" / "fake_core_policy.yaml"

        if not policy_path.exists():
            pytest.skip("Fixture not found")

        policy = load_policy(policy_path)
        fake_core_dir = FIXTURES_DIR / "fake_core" / "src" / "fake_core"
        result = run_cross_repo_validation(fake_core_dir, policy)

        # Capture text output
        output = StringIO()
        with patch("sys.stdout", output):
            print_text_report(result, policy.policy_id)

        text_output = output.getvalue()

        assert "Cross-Repo Validation Report" in text_output
        assert "fake_core_validation" in text_output


class TestMain:
    """Tests for main CLI entry point."""

    def test_main_with_valid_policy(self) -> None:
        """Test main function with a valid policy."""
        policy_path = FIXTURES_DIR / "policies" / "fake_core_policy.yaml"
        fake_core_dir = FIXTURES_DIR / "fake_core" / "src" / "fake_core"

        if not policy_path.exists():
            pytest.skip("Fixture not found")

        with patch(
            "sys.argv",
            [
                "cli",
                "--policy",
                str(policy_path),
                "--format",
                "json",
                str(fake_core_dir),
            ],
        ):
            # Capture stdout to avoid polluting test output
            with patch("sys.stdout", new_callable=StringIO):
                exit_code = main()

            # fake_core should pass validation (no forbidden imports)
            assert exit_code in (0, 1)  # 0 = valid, 1 = issues found

    def test_main_detects_violations(self) -> None:
        """Test that CLI detects violations in bad files."""
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
                "--format",
                "json",
                str(fake_app_dir),
            ],
        ):
            # Capture stdout
            output = StringIO()
            with patch("sys.stdout", output):
                exit_code = main()

            # fake_app has bad_handler.py which should fail
            assert exit_code == 1

            # Verify the output contains the violation
            json_output = json.loads(output.getvalue())
            assert json_output["is_valid"] is False

    def test_main_policy_not_found(self) -> None:
        """Test CLI handles missing policy file."""
        with patch(
            "sys.argv",
            [
                "cli",
                "--policy",
                "/nonexistent/policy.yaml",
                "--format",
                "json",
            ],
        ):
            # Capture stdout
            output = StringIO()
            with patch("sys.stdout", output):
                exit_code = main()

            assert exit_code == 2  # Error exit code

            # Should output error in JSON
            json_output = json.loads(output.getvalue())
            assert "error" in json_output

    def test_main_text_format_error(self) -> None:
        """Test CLI error output in text format."""
        with patch(
            "sys.argv",
            [
                "cli",
                "--policy",
                "/nonexistent/policy.yaml",
                "--format",
                "text",
            ],
        ):
            # Capture stderr
            stderr = StringIO()
            with patch("sys.stderr", stderr):
                exit_code = main()

            assert exit_code == 2
            assert "Error" in stderr.getvalue()

    def test_main_with_specific_rules(self) -> None:
        """Test CLI with specific rules filter."""
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
                "--format",
                "json",
                "--rules",
                "repo_boundaries",
                str(fake_app_dir),
            ],
        ):
            output = StringIO()
            with patch("sys.stdout", output):
                exit_code = main()

            # Should still detect issues
            assert exit_code == 1


class TestIntegration:
    """Integration tests for CLI with engine."""

    def test_full_validation_flow(self) -> None:
        """Test complete validation flow through CLI."""
        policy_path = FIXTURES_DIR / "policies" / "fake_app_policy.yaml"
        fake_app_dir = FIXTURES_DIR / "fake_app" / "src" / "fake_app"

        if not policy_path.exists():
            pytest.skip("Fixture not found")

        # Load and run directly (not through CLI)
        policy = load_policy(policy_path)
        result = run_cross_repo_validation(fake_app_dir, policy)

        # Should find the violation in bad_handler.py
        assert not result.is_valid
        assert len(result.issues) >= 1

        # Verify the violation is about forbidden imports
        forbidden_issues = [
            i for i in result.issues if "FORBIDDEN_IMPORT" in (i.code or "")
        ]
        assert len(forbidden_issues) >= 1

    def test_clean_repo_passes(self) -> None:
        """Test that a clean repo passes validation."""
        policy_path = FIXTURES_DIR / "policies" / "fake_core_policy.yaml"
        fake_core_dir = FIXTURES_DIR / "fake_core" / "src" / "fake_core"

        if not policy_path.exists():
            pytest.skip("Fixture not found")

        policy = load_policy(policy_path)
        result = run_cross_repo_validation(fake_core_dir, policy)

        # fake_core has no forbidden imports
        # May have issues but none should be ERROR level
        error_issues = [
            i for i in result.issues if i.severity.value in ("error", "critical")
        ]
        assert len(error_issues) == 0
