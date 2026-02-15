# SPDX-License-Identifier: Apache-2.0
"""
Integration tests for transport import checker script.

These tests run the actual script against the real codebase to verify
end-to-end functionality.

Linear ticket: OMN-220
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.timeout(60)]


class TestTransportImportCheckerIntegration:
    """Integration tests running the actual script."""

    @pytest.fixture
    def project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent.parent

    def test_script_runs_successfully_on_codebase(self, project_root: Path) -> None:
        """Test that the script runs without errors on the actual codebase."""
        result = subprocess.run(
            ["uv", "run", "python", "scripts/check_transport_imports.py"],
            check=False,
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        # Should pass (exit 0) since allowlisted violations are suppressed
        assert result.returncode == 0, f"Script failed with stderr: {result.stderr}"

    def test_json_output_is_valid(self, project_root: Path) -> None:
        """Test that --json produces valid JSON output."""
        result = subprocess.run(
            ["uv", "run", "python", "scripts/check_transport_imports.py", "--json"],
            check=False,
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode == 0, f"Script failed with stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert "summary" in data
        assert "results" in data

    def test_json_output_contains_expected_fields(self, project_root: Path) -> None:
        """Test that JSON output contains all expected summary fields."""
        result = subprocess.run(
            ["uv", "run", "python", "scripts/check_transport_imports.py", "--json"],
            check=False,
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)

        # Verify summary structure matches actual script output
        summary = data["summary"]
        assert "total_files_in_src" in summary
        assert "files_checked" in summary
        assert "changed_files_mode" in summary
        assert "clean_files" in summary
        assert "files_with_violations" in summary
        assert "total_violations" in summary
        assert "allowlisted_files" in summary

        # Verify results is a list
        assert isinstance(data["results"], list)

    def test_verbose_mode_shows_details(self, project_root: Path) -> None:
        """Test that --verbose shows additional information."""
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "scripts/check_transport_imports.py",
                "--verbose",
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode == 0, f"Script failed with stderr: {result.stderr}"
        assert "Analyzing" in result.stdout

    def test_changed_files_mode(self, project_root: Path) -> None:
        """Test --changed-files mode runs without error."""
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "scripts/check_transport_imports.py",
                "--changed-files",
                "--verbose",
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        # Should succeed regardless of whether there are changed files
        assert result.returncode == 0, f"Script failed with stderr: {result.stderr}"

    def test_help_output(self, project_root: Path) -> None:
        """Test that --help produces help text."""
        result = subprocess.run(
            ["uv", "run", "python", "scripts/check_transport_imports.py", "--help"],
            check=False,
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode == 0
        assert "usage:" in result.stdout.lower() or "transport" in result.stdout.lower()

    def test_script_reports_allowlisted_files_count(self, project_root: Path) -> None:
        """Test that the script correctly reports allowlisted file count in summary."""
        result = subprocess.run(
            ["uv", "run", "python", "scripts/check_transport_imports.py", "--json"],
            check=False,
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)

        # The allowlisted_files field should be present and non-negative
        summary = data["summary"]
        assert "allowlisted_files" in summary
        assert summary["allowlisted_files"] >= 0

        # When allowlist is empty, count should be 0 (all violations fixed!)
        # When allowlist has items, count should match the number of files with violations
        assert isinstance(summary["allowlisted_files"], int)

    def test_exit_code_zero_with_only_allowlisted_violations(
        self, project_root: Path
    ) -> None:
        """Test that exit code is 0 when only allowlisted violations exist."""
        result = subprocess.run(
            ["uv", "run", "python", "scripts/check_transport_imports.py", "--json"],
            check=False,
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        data = json.loads(result.stdout)

        # If there are no new violations (files_with_violations == 0), exit code should be 0
        if data["summary"]["files_with_violations"] == 0:
            assert result.returncode == 0

    def test_combined_json_and_verbose_flags(self, project_root: Path) -> None:
        """Test that --json and --verbose can be used together."""
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "scripts/check_transport_imports.py",
                "--json",
                "--verbose",
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode == 0, f"Script failed with stderr: {result.stderr}"
        # JSON output should still be valid even with verbose flag
        data = json.loads(result.stdout)
        assert "summary" in data

    def test_results_contain_allowlisted_file_info_when_present(
        self, project_root: Path
    ) -> None:
        """Test that results include information about allowlisted files when present."""
        result = subprocess.run(
            ["uv", "run", "python", "scripts/check_transport_imports.py", "--json"],
            check=False,
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)

        # Find allowlisted files in results
        results = data["results"]
        allowlisted_results = [
            r for r in results if "Allowlisted" in r.get("skip_reason", "")
        ]

        # Allowlisted count in summary should match results with "Allowlisted" skip_reason
        summary = data["summary"]
        assert len(allowlisted_results) == summary["allowlisted_files"]

        # If there are allowlisted files, they should have proper skip_reason
        for allowlisted in allowlisted_results:
            assert "Allowlisted" in allowlisted["skip_reason"]
            assert allowlisted["is_clean"] is True  # Allowlisted files are marked clean
            assert allowlisted["violations"] == []  # Violations are suppressed
