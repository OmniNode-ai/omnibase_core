# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

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
        # Should pass (exit 0) since the codebase has no transport violations
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
        assert "allowlisted_files" not in summary

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

    def test_json_summary_has_no_allowlist_fields(self, project_root: Path) -> None:
        """Test that the JSON summary contains no exemption metadata."""
        result = subprocess.run(
            ["uv", "run", "python", "scripts/check_transport_imports.py", "--json"],
            check=False,
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)

        summary = data["summary"]
        assert "allowlisted_files" not in summary
        assert "allowlist_expiration_warning" not in summary

    def test_src_dir_violation_fails_with_json_result(
        self, project_root: Path, tmp_path: Path
    ) -> None:
        """Test that a planted transport import fails and appears in JSON results."""
        planted_file = tmp_path / "planted_transport.py"
        planted_file.write_text("import httpx\n", encoding="utf-8")
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "scripts/check_transport_imports.py",
                "--src-dir",
                str(tmp_path),
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode == 1, result.stdout + result.stderr
        data = json.loads(result.stdout)
        assert data["summary"]["files_with_violations"] == 1
        assert data["summary"]["total_violations"] == 1
        assert len(data["results"]) == 1
        file_result = data["results"][0]
        assert file_result["file"] == str(planted_file.resolve())
        assert file_result["is_clean"] is False
        assert file_result["skip_reason"] is None
        assert len(file_result["violations"]) == 1
        violation = file_result["violations"][0]
        assert violation["type"] == "banned_transport_import"
        assert violation["severity"] == "error"
        assert violation["line"] == 1
        assert "httpx" in violation["message"]

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
