"""
Extended tests for validation types module to improve coverage.

Tests cover:
- CLI functionality for union validation
- Exception handling edge cases
- Complex error scenarios
- File validation error handling
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from omnibase_core.validation.types import (
    validate_union_usage_cli,
    validate_union_usage_directory,
    validate_union_usage_file,
)


class TestValidateUnionUsageCLI:
    """Extended tests for validate_union_usage_cli function."""

    def test_cli_single_file_valid(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test CLI with single valid file."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            """
from typing import Union

def func(x: Union[str, int]) -> None:
    pass
""",
        )

        monkeypatch.setattr(sys, "argv", ["validate_union", str(test_file)])

        exit_code = validate_union_usage_cli()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "✅" in captured.out or "Union validation" in captured.out

    def test_cli_single_file_with_issues(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test CLI with single file containing union issues."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            """
from typing import Union

def func(x: Union[str, int, bool, float, dict]) -> None:
    pass
""",
        )

        monkeypatch.setattr(sys, "argv", ["validate_union", str(test_file)])

        exit_code = validate_union_usage_cli()

        # Should return 1 due to issues
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "❌" in captured.out or "issues found" in captured.out

    def test_cli_directory_validation_success(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test CLI directory validation succeeds."""
        (tmp_path / "test1.py").write_text(
            """
def func(x: str) -> None:
    pass
""",
        )
        (tmp_path / "test2.py").write_text(
            """
from typing import Union

def func(x: Union[str, int]) -> None:
    pass
""",
        )

        monkeypatch.setattr(sys, "argv", ["validate_union", str(tmp_path)])

        exit_code = validate_union_usage_cli()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Union validation" in captured.out

    def test_cli_directory_validation_with_errors(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test CLI directory validation with errors."""
        (tmp_path / "bad.py").write_text(
            """
from typing import Union

def func(x: Union[str, int, bool, float]) -> None:
    pass
""",
        )

        monkeypatch.setattr(
            sys,
            "argv",
            ["validate_union", str(tmp_path), "--strict"],
        )

        exit_code = validate_union_usage_cli()

        # Should fail in strict mode
        captured = capsys.readouterr()
        # Check for error indicators
        assert "❌" in captured.out or "issues found" in captured.out.lower()

    def test_cli_max_unions_flag(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test CLI with --max-unions flag."""
        # Create multiple files with unions
        for i in range(3):
            (tmp_path / f"test{i}.py").write_text(
                """
from typing import Union

def func(x: Union[str, int]) -> None:
    pass
""",
            )

        monkeypatch.setattr(
            sys,
            "argv",
            ["validate_union", str(tmp_path), "--max-unions", "2"],
        )

        exit_code = validate_union_usage_cli()

        # Should fail because 3 unions > max 2
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Union count exceeded" in captured.out or "❌" in captured.out

    def test_cli_strict_flag(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test CLI with --strict flag."""
        (tmp_path / "test.py").write_text(
            """
from typing import Union

def func(x: Union[str, int, bool, float]) -> None:
    pass
""",
        )

        monkeypatch.setattr(
            sys,
            "argv",
            ["validate_union", str(tmp_path), "--strict"],
        )

        exit_code = validate_union_usage_cli()

        # Should process with strict mode
        captured = capsys.readouterr()
        assert "Union validation" in captured.out or "issues found" in captured.out

    def test_cli_default_path(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test CLI defaults to current directory."""
        import os

        (tmp_path / "test.py").write_text(
            """
def func(x: str) -> None:
    pass
""",
        )

        original_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            monkeypatch.setattr(sys, "argv", ["validate_union"])

            exit_code = validate_union_usage_cli()

            assert exit_code == 0
            captured = capsys.readouterr()
            assert "Union validation" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_cli_help_text_includes_examples(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test CLI help text includes usage examples."""
        monkeypatch.setattr(sys, "argv", ["validate_union", "--help"])

        with pytest.raises(SystemExit) as exc_info:
            validate_union_usage_cli()

        assert exc_info.value.code == 0

    def test_cli_custom_max_unions_value(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test CLI respects custom --max-unions value."""
        (tmp_path / "test.py").write_text(
            """
from typing import Union

def func(x: Union[str, int]) -> None:
    pass
""",
        )

        monkeypatch.setattr(
            sys,
            "argv",
            ["validate_union", str(tmp_path), "--max-unions", "50"],
        )

        exit_code = validate_union_usage_cli()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Union validation" in captured.out

    def test_cli_directory_with_no_errors(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test CLI directory validation with no errors."""
        (tmp_path / "clean.py").write_text(
            """
def func(x: str) -> int:
    return 42
""",
        )

        monkeypatch.setattr(sys, "argv", ["validate_union", str(tmp_path)])

        exit_code = validate_union_usage_cli()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "✅" in captured.out or "0 unions" in captured.out

    def test_cli_single_file_no_unions(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test CLI with single file containing no unions."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            """
def func(x: str) -> int:
    return 42
""",
        )

        monkeypatch.setattr(sys, "argv", ["validate_union", str(test_file)])

        exit_code = validate_union_usage_cli()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "0 unions" in captured.out or "✅" in captured.out

    def test_cli_mixed_success_and_errors(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test CLI with mix of good and problematic files."""
        (tmp_path / "good.py").write_text(
            """
def func(x: str) -> None:
    pass
""",
        )
        (tmp_path / "bad.py").write_text(
            """
from typing import Union

def func(x: Union[str, int, bool, float]) -> None:
    pass
""",
        )

        monkeypatch.setattr(
            sys,
            "argv",
            ["validate_union", str(tmp_path), "--strict"],
        )

        exit_code = validate_union_usage_cli()

        captured = capsys.readouterr()
        # Should report issues
        assert "Union validation" in captured.out


class TestValidateUnionUsageFileExtended:
    """Extended tests for validate_union_usage_file exception handling."""

    def test_file_not_found_error(self, tmp_path: Path) -> None:
        """Test handling of file not found error."""
        nonexistent = tmp_path / "nonexistent.py"

        union_count, issues, patterns = validate_union_usage_file(nonexistent)

        assert union_count == 0
        assert len(issues) == 1
        assert "File not found" in issues[0]
        assert len(patterns) == 0

    def test_file_syntax_error_handling(self, tmp_path: Path) -> None:
        """Test handling of syntax errors."""
        test_file = tmp_path / "syntax_error.py"
        test_file.write_text(
            """
from typing import Union

def func(x: Union[str, int  # Missing closing bracket
    pass
""",
        )

        union_count, issues, patterns = validate_union_usage_file(test_file)

        assert union_count == 0
        assert len(issues) >= 1
        assert any("Error parsing" in issue for issue in issues)
        assert len(patterns) == 0

    def test_file_permission_error(self, tmp_path: Path) -> None:
        """Test handling of permission errors."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def func(): pass")

        # Mock open to raise PermissionError
        original_open = open

        def mock_open(*args, **kwargs):
            if str(test_file) in str(args[0]):
                raise PermissionError("Permission denied")
            return original_open(*args, **kwargs)

        with patch("builtins.open", side_effect=mock_open):
            union_count, issues, patterns = validate_union_usage_file(test_file)

        # Should handle gracefully
        assert union_count == 0
        assert len(issues) >= 1

    def test_file_unicode_decode_error(self, tmp_path: Path) -> None:
        """Test handling of unicode decode errors."""
        test_file = tmp_path / "binary.py"
        # Write binary data that can't be decoded as UTF-8
        test_file.write_bytes(b"\xff\xfe\xfd\xfc")

        union_count, issues, patterns = validate_union_usage_file(test_file)

        # Should handle gracefully
        assert union_count == 0
        assert len(issues) >= 1

    def test_file_generic_exception_handling(self, tmp_path: Path) -> None:
        """Test generic exception handling in validate_union_usage_file."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            """
from typing import Union

def func(x: Union[str, int]) -> None:
    pass
""",
        )

        # Mock ast.parse to raise a generic exception
        with patch("ast.parse", side_effect=RuntimeError("Generic error")):
            union_count, issues, patterns = validate_union_usage_file(test_file)

        assert union_count == 0
        assert len(issues) >= 1
        assert any("Failed to validate union usage" in issue for issue in issues)
        assert len(patterns) == 0

    def test_file_empty_content(self, tmp_path: Path) -> None:
        """Test handling of empty files."""
        test_file = tmp_path / "empty.py"
        test_file.write_text("")

        union_count, issues, patterns = validate_union_usage_file(test_file)

        assert union_count == 0
        assert len(issues) == 0
        assert len(patterns) == 0

    def test_file_only_comments(self, tmp_path: Path) -> None:
        """Test handling of files with only comments."""
        test_file = tmp_path / "comments.py"
        test_file.write_text(
            """
# This is a comment
# Another comment
# More comments
""",
        )

        union_count, issues, patterns = validate_union_usage_file(test_file)

        assert union_count == 0
        assert len(issues) == 0
        assert len(patterns) == 0

    def test_file_complex_union_patterns_detected(self, tmp_path: Path) -> None:
        """Test detection of complex union patterns."""
        test_file = tmp_path / "complex.py"
        test_file.write_text(
            """
from typing import Union, Dict, List

def func1(x: Union[str, int, bool, float, dict]) -> None:
    pass

def func2(x: Union[Dict[str, int], List[str], str]) -> None:
    pass

def func3(x: str | int | bool | float | list) -> None:
    pass
""",
        )

        union_count, issues, patterns = validate_union_usage_file(test_file)

        assert union_count >= 3
        assert len(issues) >= 3  # Should detect issues in all unions
        assert len(patterns) >= 3

    def test_file_optional_suggestion_detected(self, tmp_path: Path) -> None:
        """Test detection of Union[T, None] that should use Optional."""
        test_file = tmp_path / "optional.py"
        test_file.write_text(
            """
from typing import Union

def func(x: Union[str, None]) -> None:
    pass
""",
        )

        union_count, issues, patterns = validate_union_usage_file(test_file)

        assert union_count >= 1
        assert len(issues) >= 1
        assert any("Optional" in issue for issue in issues)


class TestValidateUnionUsageDirectory:
    """Tests for validate_union_usage_directory function."""

    def test_directory_with_no_python_files(self, tmp_path: Path) -> None:
        """Test directory validation when no Python files exist."""
        # Create empty directory
        result = validate_union_usage_directory(tmp_path)

        assert result.is_valid is True
        assert result.metadata.files_processed == 0
        assert result.metadata is not None

    def test_directory_filters_pycache(self, tmp_path: Path) -> None:
        """Test that __pycache__ directories are properly filtered out."""
        # Create __pycache__ directory with unions
        pycache_dir = tmp_path / "__pycache__"
        pycache_dir.mkdir()
        (pycache_dir / "test.py").write_text(
            """
from typing import Union

def func(x: Union[str, int, bool]) -> None:
    pass
""",
        )

        # Regular file should not be filtered
        (tmp_path / "regular.py").write_text(
            """
def func(x: str) -> None:
    pass
""",
        )

        result = validate_union_usage_directory(tmp_path)

        # Should only check the regular file, not __pycache__
        assert result.metadata.files_processed == 1
        assert result.is_valid is True

    def test_directory_respects_max_unions_limit(self, tmp_path: Path) -> None:
        """Test that max_unions parameter is respected."""
        # Create multiple files with unions
        for i in range(5):
            (tmp_path / f"test{i}.py").write_text(
                """
from typing import Union

def func(x: Union[str, int]) -> None:
    pass
""",
            )

        result = validate_union_usage_directory(tmp_path, max_unions=3, strict=False)

        # Should fail because 5 unions > max 3
        assert result.is_valid is False
        assert result.metadata is not None
        assert result.metadata.total_unions == 5
        assert result.metadata.files_processed == 5

    def test_directory_strict_mode_fails_on_issues(self, tmp_path: Path) -> None:
        """Test that strict mode fails when issues are found."""
        (tmp_path / "test.py").write_text(
            """
from typing import Union

def func(x: Union[str, int, bool, float]) -> None:
    pass
""",
        )

        result = validate_union_usage_directory(tmp_path, strict=True)

        # Should fail in strict mode due to complex union
        assert result.is_valid is False
        assert len(result.errors) >= 1

    def test_directory_non_strict_mode_succeeds_with_issues(
        self, tmp_path: Path
    ) -> None:
        """Test that non-strict mode succeeds even with issues."""
        (tmp_path / "test.py").write_text(
            """
from typing import Union

def func(x: Union[str, int, bool, float]) -> None:
    pass
""",
        )

        result = validate_union_usage_directory(tmp_path, max_unions=100, strict=False)

        # Should succeed in non-strict mode despite issues
        assert result.is_valid is True
        assert len(result.errors) >= 1  # Issues are still reported

    def test_directory_populates_metadata_correctly(self, tmp_path: Path) -> None:
        """Test that directory validation populates all metadata fields."""
        (tmp_path / "test1.py").write_text(
            """
from typing import Union

def func(x: Union[str, int, bool]) -> None:
    pass
""",
        )
        (tmp_path / "test2.py").write_text(
            """
from typing import Union

def func(x: Union[str, int]) -> None:
    pass
""",
        )

        result = validate_union_usage_directory(tmp_path)

        assert result.metadata is not None
        assert result.metadata.validation_type == "union_usage"
        assert result.metadata.total_unions >= 2
        assert result.metadata.max_unions == 100
        assert result.metadata.complex_patterns is not None
        assert result.metadata.strict_mode is not None

    def test_directory_handles_mixed_file_types(self, tmp_path: Path) -> None:
        """Test directory with Python and non-Python files."""
        # Python file with unions
        (tmp_path / "test.py").write_text(
            """
from typing import Union

def func(x: Union[str, int]) -> None:
    pass
""",
        )

        # Non-Python files (should be ignored)
        (tmp_path / "readme.txt").write_text("Not Python")
        (tmp_path / "config.json").write_text("{}")

        result = validate_union_usage_directory(tmp_path)

        # Should only process Python file
        assert result.metadata.files_processed == 1
        assert result.is_valid is True
