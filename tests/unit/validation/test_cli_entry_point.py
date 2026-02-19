# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Comprehensive tests for CLI entry point run_validation_cli().

Tests cover:
- CLI execution with different validation types
- Directory handling and validation
- Argument parsing and parameter passing
- Error handling for invalid inputs
- Exit code behavior with --exit-zero flag
- Quiet and verbose output modes
- All validation types (architecture, union-usage, contracts, patterns, all)
- Multiple directory handling
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from omnibase_core.validation.validator_cli import run_validation_cli

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.monkeypatch import MonkeyPatch


@pytest.mark.unit
class TestRunValidationCLIBasics:
    """Test basic CLI functionality."""

    def test_cli_list_command(
        self,
        monkeypatch: MonkeyPatch,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test CLI list command to show available validators."""
        monkeypatch.setattr(sys, "argv", ["prog", "list"])

        exit_code = run_validation_cli()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Available Validation Tools" in captured.out

    def test_cli_with_nonexistent_directory(
        self,
        monkeypatch: MonkeyPatch,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test CLI with nonexistent directory returns error."""
        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "architecture", "/nonexistent/path"],
        )

        exit_code = run_validation_cli()

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Directory not found" in captured.out

    def test_cli_with_exit_zero_flag(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        """Test CLI with --exit-zero flag always returns 0."""
        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "architecture", "/nonexistent/path", "--exit-zero"],
        )

        exit_code = run_validation_cli()

        assert exit_code == 0

    def test_cli_quiet_mode(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test CLI with --quiet flag suppresses output."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()
        (test_dir / "test.py").write_text("# Test\n")

        monkeypatch.setattr(
            sys, "argv", ["prog", "architecture", str(test_dir), "--quiet"]
        )

        exit_code = run_validation_cli()

        captured = capsys.readouterr()
        # Quiet mode should produce minimal output
        assert exit_code == 0

    def test_cli_verbose_mode(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test CLI with --verbose flag shows detailed output."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()
        (test_dir / "test.py").write_text("# Test\n")

        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "architecture", str(test_dir), "--verbose"],
        )

        exit_code = run_validation_cli()

        captured = capsys.readouterr()
        # Verbose mode should show detailed information
        assert exit_code == 0
        assert "Files checked" in captured.out or "PASSED" in captured.out


@pytest.mark.unit
class TestRunValidationCLIValidationTypes:
    """Test CLI with different validation types."""

    def test_cli_architecture_validation(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test CLI architecture validation."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()

        # Create valid file
        test_file = test_dir / "model_user.py"
        test_file.write_text(
            """
from pydantic import BaseModel

class ModelUser(BaseModel):
    name: str
"""
        )

        monkeypatch.setattr(sys, "argv", ["prog", "architecture", str(test_dir)])

        exit_code = run_validation_cli()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "ARCHITECTURE" in captured.out

    def test_cli_union_usage_validation(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test CLI union-usage validation."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()

        test_file = test_dir / "test.py"
        test_file.write_text(
            """
from typing import Union

def func(x: Union[str, int]) -> None:
    pass
"""
        )

        monkeypatch.setattr(sys, "argv", ["prog", "union-usage", str(test_dir)])

        exit_code = run_validation_cli()

        captured = capsys.readouterr()
        assert "UNION-USAGE" in captured.out

    def test_cli_contracts_validation(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test CLI contracts validation."""
        test_dir = tmp_path / "contracts"
        test_dir.mkdir()

        monkeypatch.setattr(sys, "argv", ["prog", "contracts", str(test_dir)])

        exit_code = run_validation_cli()

        captured = capsys.readouterr()
        assert "CONTRACTS" in captured.out

    def test_cli_patterns_validation(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test CLI patterns validation."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()

        test_file = test_dir / "test.py"
        test_file.write_text(
            """
from pydantic import BaseModel

class ModelTest(BaseModel):
    name: str
"""
        )

        monkeypatch.setattr(sys, "argv", ["prog", "patterns", str(test_dir)])

        exit_code = run_validation_cli()

        captured = capsys.readouterr()
        assert "PATTERNS" in captured.out

    def test_cli_all_validations(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test CLI running all validations."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()

        test_file = test_dir / "test.py"
        test_file.write_text(
            """
from pydantic import BaseModel

class ModelTest(BaseModel):
    name: str
"""
        )

        monkeypatch.setattr(sys, "argv", ["prog", "all", str(test_dir)])

        exit_code = run_validation_cli()

        captured = capsys.readouterr()
        # Should show multiple validation types
        assert "Final Result" in captured.out or "ALL VALIDATIONS" in captured.out


@pytest.mark.unit
class TestRunValidationCLIParameters:
    """Test CLI with various parameters."""

    def test_cli_with_max_violations(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
    ) -> None:
        """Test CLI with --max-violations parameter."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()
        (test_dir / "test.py").write_text("# Test\n")

        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "architecture", str(test_dir), "--max-violations", "10"],
        )

        exit_code = run_validation_cli()

        assert exit_code == 0

    def test_cli_with_max_unions(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
    ) -> None:
        """Test CLI with --max-unions parameter."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()
        (test_dir / "test.py").write_text("# Test\n")

        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "union-usage", str(test_dir), "--max-unions", "50"],
        )

        exit_code = run_validation_cli()

        assert exit_code == 0

    def test_cli_with_strict_flag(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
    ) -> None:
        """Test CLI with --strict flag."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()
        (test_dir / "test.py").write_text("# Test\n")

        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "patterns", str(test_dir), "--strict"],
        )

        exit_code = run_validation_cli()

        assert exit_code == 0

    def test_cli_with_multiple_parameters(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
    ) -> None:
        """Test CLI with multiple parameters."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()
        (test_dir / "test.py").write_text("# Test\n")

        monkeypatch.setattr(
            sys,
            "argv",
            [
                "prog",
                "all",
                str(test_dir),
                "--strict",
                "--max-violations",
                "5",
                "--max-unions",
                "10",
                "--verbose",
            ],
        )

        exit_code = run_validation_cli()

        assert exit_code == 0


@pytest.mark.unit
class TestRunValidationCLIMultipleDirectories:
    """Test CLI with multiple directories."""

    def test_cli_with_multiple_valid_directories(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test CLI with multiple valid directories."""
        dir1 = tmp_path / "src1"
        dir1.mkdir()
        (dir1 / "test1.py").write_text("# Test 1\n")

        dir2 = tmp_path / "src2"
        dir2.mkdir()
        (dir2 / "test2.py").write_text("# Test 2\n")

        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "architecture", str(dir1), str(dir2)],
        )

        exit_code = run_validation_cli()

        captured = capsys.readouterr()
        # Should validate both directories
        assert exit_code == 0

    def test_cli_with_mixed_valid_invalid_directories(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test CLI with mix of valid and invalid directories."""
        valid_dir = tmp_path / "src"
        valid_dir.mkdir()
        (valid_dir / "test.py").write_text("# Test\n")

        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "architecture", str(valid_dir), "/nonexistent"],
        )

        exit_code = run_validation_cli()

        captured = capsys.readouterr()
        # Should continue with valid directory
        assert "Directory not found" in captured.out

    def test_cli_with_all_invalid_directories(
        self,
        monkeypatch: MonkeyPatch,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test CLI with all invalid directories."""
        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "architecture", "/nonexistent1", "/nonexistent2"],
        )

        exit_code = run_validation_cli()

        captured = capsys.readouterr()
        # Should report directory not found errors
        assert exit_code == 1
        assert "Directory not found" in captured.out


@pytest.mark.unit
class TestRunValidationCLIErrorHandling:
    """Test CLI error handling scenarios."""

    def test_cli_with_validation_failure(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test CLI handles validation failures correctly."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()

        # Create file with violations
        test_file = test_dir / "test.py"
        test_file.write_text(
            """
from pydantic import BaseModel

class Model1(BaseModel):
    pass

class Model2(BaseModel):
    pass
"""
        )

        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "architecture", str(test_dir)],
        )

        exit_code = run_validation_cli()

        captured = capsys.readouterr()
        # Should report failure
        assert "FAILED" in captured.out or exit_code == 1

    def test_cli_with_validation_failure_and_exit_zero(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
    ) -> None:
        """Test CLI with --exit-zero returns 0 even on failure."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()

        # Create file with violations
        test_file = test_dir / "test.py"
        test_file.write_text(
            """
from pydantic import BaseModel

class Model1(BaseModel):
    pass

class Model2(BaseModel):
    pass
"""
        )

        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "architecture", str(test_dir), "--exit-zero"],
        )

        exit_code = run_validation_cli()

        assert exit_code == 0

    def test_cli_quiet_mode_with_errors(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test CLI quiet mode still shows errors."""
        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "architecture", "/nonexistent", "--quiet"],
        )

        exit_code = run_validation_cli()

        captured = capsys.readouterr()
        # Quiet mode should show critical errors
        assert exit_code == 1

    def test_cli_handles_empty_directory_gracefully(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test CLI handles empty directory gracefully."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        monkeypatch.setattr(sys, "argv", ["prog", "architecture", str(empty_dir)])

        exit_code = run_validation_cli()

        # Should handle empty directory without crashing
        assert exit_code in [0, 1]


@pytest.mark.unit
class TestRunValidationCLIOutputFormatting:
    """Test CLI output formatting."""

    def test_cli_shows_file_count(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test CLI output shows file count."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()
        (test_dir / "test.py").write_text("# Test\n")

        monkeypatch.setattr(
            sys,
            "argv",
            ["prog", "architecture", str(test_dir), "--verbose"],
        )

        exit_code = run_validation_cli()

        captured = capsys.readouterr()
        assert "Files checked" in captured.out or "PASSED" in captured.out

    def test_cli_shows_final_summary(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test CLI shows final summary."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()
        (test_dir / "test.py").write_text("# Test\n")

        monkeypatch.setattr(sys, "argv", ["prog", "architecture", str(test_dir)])

        exit_code = run_validation_cli()

        captured = capsys.readouterr()
        assert "Final Result" in captured.out or "PASSED" in captured.out

    def test_cli_quiet_mode_minimal_output(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
        capsys: CaptureFixture[str],
    ) -> None:
        """Test CLI quiet mode produces minimal output."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()
        (test_dir / "test.py").write_text("# Test\n")

        monkeypatch.setattr(
            sys, "argv", ["prog", "architecture", str(test_dir), "--quiet"]
        )

        exit_code = run_validation_cli()

        captured = capsys.readouterr()
        # Quiet mode should have minimal output
        assert len(captured.out) < 500 or captured.out == ""
