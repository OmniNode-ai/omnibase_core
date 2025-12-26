"""
Comprehensive tests for the validate-no-infra-imports.py validation script.

Tests cover:
- InfraImportVisitor AST visitor
- InfraImportValidator file and directory validation
- Happy paths (valid code with no infra imports)
- Violation detection (code that imports from omnibase_infra)
- File exclusions (.pyi files, non-Python files)
- CLI arguments (--verbose, --quiet, paths)
- pass_filenames mode for pre-commit integration
- Edge cases (syntax errors, empty files, encoding issues)
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the validation script components
SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent.parent / "scripts" / "validation"
)
sys.path.insert(0, str(SCRIPTS_DIR))

# Use importlib to avoid issues with hyphenated filename
import importlib.util

spec = importlib.util.spec_from_file_location(
    "validate_no_infra_imports", SCRIPTS_DIR / "validate-no-infra-imports.py"
)
if spec is None:
    raise ImportError(
        f"Could not load spec from {SCRIPTS_DIR / 'validate-no-infra-imports.py'}"
    )
if spec.loader is None:
    raise ImportError(
        f"Spec loader is None for {SCRIPTS_DIR / 'validate-no-infra-imports.py'}"
    )
validate_no_infra_imports = importlib.util.module_from_spec(spec)
# Add to sys.modules before exec to avoid dataclass issues
sys.modules["validate_no_infra_imports"] = validate_no_infra_imports
spec.loader.exec_module(validate_no_infra_imports)

InfraImportViolation = validate_no_infra_imports.InfraImportViolation
InfraImportVisitor = validate_no_infra_imports.InfraImportVisitor
InfraImportValidator = validate_no_infra_imports.InfraImportValidator
main = validate_no_infra_imports.main
TARGET_MODULE = validate_no_infra_imports.TARGET_MODULE
DEFAULT_SCAN_PATH = validate_no_infra_imports.DEFAULT_SCAN_PATH

# Mark all tests in this module as unit tests
pytestmark = [pytest.mark.unit, pytest.mark.timeout(30)]


@pytest.mark.unit
class TestInfraImportViolation:
    """Tests for the InfraImportViolation dataclass."""

    def test_violation_creation(self) -> None:
        """Test that InfraImportViolation can be created with all fields."""
        violation = InfraImportViolation(
            file_path="/test/file.py",
            line_no=10,
            import_statement="from omnibase_infra import kafka",
            import_type="from",
            module_path="omnibase_infra",
        )
        assert violation.file_path == "/test/file.py"
        assert violation.line_no == 10
        assert violation.import_statement == "from omnibase_infra import kafka"
        assert violation.import_type == "from"
        assert violation.module_path == "omnibase_infra"


@pytest.mark.unit
class TestConstants:
    """Tests for module constants."""

    def test_target_module_is_omnibase_infra(self) -> None:
        """Test that TARGET_MODULE is correctly set."""
        assert TARGET_MODULE == "omnibase_infra"

    def test_default_scan_path_is_omnibase_core(self) -> None:
        """Test that DEFAULT_SCAN_PATH is correctly set."""
        assert DEFAULT_SCAN_PATH == "src/omnibase_core"


@pytest.mark.unit
class TestInfraImportVisitorFromImports:
    """Tests for from import detection in InfraImportVisitor."""

    def test_detects_from_omnibase_infra_import(self) -> None:
        """Test detection of 'from omnibase_infra import ...'."""
        import ast

        code = """
from omnibase_infra import kafka
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        visitor = InfraImportVisitor("/test.py", source_lines)
        visitor.visit(tree)

        assert len(visitor.violations) == 1
        assert visitor.violations[0].import_type == "from"
        assert visitor.violations[0].module_path == "omnibase_infra"

    def test_detects_from_omnibase_infra_submodule_import(self) -> None:
        """Test detection of 'from omnibase_infra.module import ...'."""
        import ast

        code = """
from omnibase_infra.kafka import KafkaProducer
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        visitor = InfraImportVisitor("/test.py", source_lines)
        visitor.visit(tree)

        assert len(visitor.violations) == 1
        assert visitor.violations[0].import_type == "from"
        assert visitor.violations[0].module_path == "omnibase_infra.kafka"

    def test_detects_from_omnibase_infra_deep_submodule(self) -> None:
        """Test detection of deeply nested submodule imports."""
        import ast

        code = """
from omnibase_infra.database.postgres import PostgresConnection
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        visitor = InfraImportVisitor("/test.py", source_lines)
        visitor.visit(tree)

        assert len(visitor.violations) == 1
        assert "omnibase_infra.database.postgres" in visitor.violations[0].module_path


@pytest.mark.unit
class TestInfraImportVisitorRegularImports:
    """Tests for regular import detection in InfraImportVisitor."""

    def test_detects_import_omnibase_infra(self) -> None:
        """Test detection of 'import omnibase_infra'."""
        import ast

        code = """
import omnibase_infra
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        visitor = InfraImportVisitor("/test.py", source_lines)
        visitor.visit(tree)

        assert len(visitor.violations) == 1
        assert visitor.violations[0].import_type == "import"
        assert visitor.violations[0].module_path == "omnibase_infra"

    def test_detects_import_omnibase_infra_submodule(self) -> None:
        """Test detection of 'import omnibase_infra.module'."""
        import ast

        code = """
import omnibase_infra.kafka
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        visitor = InfraImportVisitor("/test.py", source_lines)
        visitor.visit(tree)

        assert len(visitor.violations) == 1
        assert visitor.violations[0].import_type == "import"
        assert visitor.violations[0].module_path == "omnibase_infra.kafka"

    def test_detects_aliased_import(self) -> None:
        """Test detection of aliased imports."""
        import ast

        code = """
import omnibase_infra as infra
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        visitor = InfraImportVisitor("/test.py", source_lines)
        visitor.visit(tree)

        assert len(visitor.violations) == 1
        assert visitor.violations[0].module_path == "omnibase_infra"


@pytest.mark.unit
class TestInfraImportVisitorCleanCode:
    """Tests for code that should NOT trigger violations."""

    def test_no_violation_for_omnibase_core_imports(self) -> None:
        """Test that omnibase_core imports don't trigger violations."""
        import ast

        code = """
from omnibase_core import models
from omnibase_core.nodes import NodeCompute
import omnibase_core
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        visitor = InfraImportVisitor("/test.py", source_lines)
        visitor.visit(tree)

        assert len(visitor.violations) == 0

    def test_no_violation_for_standard_library(self) -> None:
        """Test that standard library imports don't trigger violations."""
        import ast

        code = """
import os
from pathlib import Path
import asyncio
from typing import Optional
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        visitor = InfraImportVisitor("/test.py", source_lines)
        visitor.visit(tree)

        assert len(visitor.violations) == 0

    def test_no_violation_for_third_party_libraries(self) -> None:
        """Test that third-party library imports don't trigger violations."""
        import ast

        code = """
import pydantic
from fastapi import FastAPI
import requests
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        visitor = InfraImportVisitor("/test.py", source_lines)
        visitor.visit(tree)

        assert len(visitor.violations) == 0

    def test_no_violation_for_partial_name_match(self) -> None:
        """Test that partial name matches don't trigger false positives."""
        import ast

        code = """
import omnibase_infrastructure  # Different module
from omnibase_infra_utils import helper  # Different module
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        visitor = InfraImportVisitor("/test.py", source_lines)
        visitor.visit(tree)

        assert len(visitor.violations) == 0


@pytest.mark.unit
class TestInfraImportVisitorMultipleViolations:
    """Tests for multiple violation detection."""

    def test_detects_multiple_violations(self) -> None:
        """Test that multiple violations in one file are all detected."""
        import ast

        code = """
import omnibase_infra
from omnibase_infra.kafka import KafkaProducer
from omnibase_infra.database import PostgresConnection
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        visitor = InfraImportVisitor("/test.py", source_lines)
        visitor.visit(tree)

        assert len(visitor.violations) == 3

    def test_captures_correct_line_numbers(self) -> None:
        """Test that line numbers are correctly captured."""
        import ast

        code = """

import omnibase_infra

from omnibase_infra.kafka import KafkaProducer
"""
        source_lines = code.splitlines()
        tree = ast.parse(code)

        visitor = InfraImportVisitor("/test.py", source_lines)
        visitor.visit(tree)

        assert len(visitor.violations) == 2
        line_numbers = {v.line_no for v in visitor.violations}
        assert 3 in line_numbers  # import omnibase_infra
        assert 5 in line_numbers  # from omnibase_infra.kafka


@pytest.mark.unit
class TestInfraImportVisitorSourceLines:
    """Tests for source line retrieval."""

    def test_get_source_line_returns_correct_content(self) -> None:
        """Test that source lines are correctly retrieved."""
        code = """import omnibase_infra"""
        source_lines = code.splitlines()

        visitor = InfraImportVisitor("/test.py", source_lines)
        line = visitor._get_source_line(1)

        assert line == "import omnibase_infra"

    def test_get_source_line_handles_invalid_line(self) -> None:
        """Test handling of invalid line numbers."""
        code = """import omnibase_infra"""
        source_lines = code.splitlines()

        visitor = InfraImportVisitor("/test.py", source_lines)

        assert visitor._get_source_line(0) == "<source unavailable>"
        assert visitor._get_source_line(999) == "<source unavailable>"


@pytest.mark.unit
class TestInfraImportValidator:
    """Tests for the InfraImportValidator class."""

    def test_validates_clean_file(self, tmp_path: Path) -> None:
        """Test validation of a clean file with no infra imports."""
        test_file = tmp_path / "clean.py"
        test_file.write_text(
            """
from omnibase_core import models
import os
"""
        )
        validator = InfraImportValidator()
        is_valid = validator.validate_file(test_file)

        assert is_valid is True
        assert len(validator.violations) == 0
        assert validator.checked_files == 1

    def test_validates_file_with_violations(self, tmp_path: Path) -> None:
        """Test validation of a file with infra imports."""
        test_file = tmp_path / "bad.py"
        test_file.write_text(
            """
from omnibase_infra import kafka
"""
        )
        validator = InfraImportValidator()
        is_valid = validator.validate_file(test_file)

        assert is_valid is False
        assert len(validator.violations) == 1
        assert validator.checked_files == 1

    def test_skips_pyi_files(self, tmp_path: Path) -> None:
        """Test that .pyi type stub files are skipped."""
        test_file = tmp_path / "module.pyi"
        test_file.write_text(
            """
from omnibase_infra import types
"""
        )
        validator = InfraImportValidator()
        is_valid = validator.validate_file(test_file)

        assert is_valid is True
        assert len(validator.violations) == 0
        assert validator.checked_files == 0  # Not counted as checked

    def test_handles_syntax_error_gracefully(self, tmp_path: Path) -> None:
        """Test that syntax errors are handled gracefully."""
        test_file = tmp_path / "syntax_error.py"
        test_file.write_text(
            """
def incomplete(
"""
        )
        validator = InfraImportValidator()
        is_valid = validator.validate_file(test_file)

        # Syntax error files are skipped but logged
        assert is_valid is True
        assert len(validator.errors) == 1
        assert "Syntax error" in validator.errors[0]

    def test_handles_encoding_error_gracefully(self, tmp_path: Path) -> None:
        """Test that encoding errors are handled gracefully."""
        test_file = tmp_path / "encoding_error.py"
        test_file.write_bytes(b"\xff\xfe invalid utf-8")

        validator = InfraImportValidator()
        is_valid = validator.validate_file(test_file)

        assert is_valid is True
        assert len(validator.errors) == 1

    def test_validates_directory(self, tmp_path: Path) -> None:
        """Test validation of an entire directory."""
        clean_file = tmp_path / "clean.py"
        clean_file.write_text("import os")

        bad_file = tmp_path / "bad.py"
        bad_file.write_text("from omnibase_infra import kafka")

        validator = InfraImportValidator()
        is_valid = validator.validate_path(tmp_path)

        assert is_valid is False
        assert validator.checked_files == 2
        assert len(validator.violations) == 1

    def test_validates_nested_directories(self, tmp_path: Path) -> None:
        """Test validation of nested directory structure."""
        subdir = tmp_path / "src" / "models"
        subdir.mkdir(parents=True)

        clean_file = subdir / "model.py"
        clean_file.write_text("import os")

        bad_file = subdir / "infra_model.py"
        bad_file.write_text("from omnibase_infra import database")

        validator = InfraImportValidator()
        is_valid = validator.validate_path(tmp_path)

        assert is_valid is False
        assert len(validator.violations) == 1

    def test_skips_excluded_directories(self, tmp_path: Path) -> None:
        """Test that excluded directories are skipped."""
        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        cache_file = pycache / "module.py"
        cache_file.write_text("from omnibase_infra import kafka")

        venv = tmp_path / ".venv"
        venv.mkdir()
        venv_file = venv / "site.py"
        venv_file.write_text("from omnibase_infra import database")

        validator = InfraImportValidator()
        is_valid = validator.validate_path(tmp_path)

        assert is_valid is True
        assert len(validator.violations) == 0

    def test_handles_nonexistent_path(self, tmp_path: Path) -> None:
        """Test handling of nonexistent paths."""
        nonexistent = tmp_path / "nonexistent"

        validator = InfraImportValidator()
        is_valid = validator.validate_path(nonexistent)

        assert is_valid is False
        assert len(validator.errors) == 1
        assert "does not exist" in validator.errors[0]

    def test_validate_files_mode(self, tmp_path: Path) -> None:
        """Test the validate_files method for pass_filenames mode."""
        clean_file = tmp_path / "clean.py"
        clean_file.write_text("import os")

        bad_file = tmp_path / "bad.py"
        bad_file.write_text("from omnibase_infra import kafka")

        validator = InfraImportValidator()
        is_valid = validator.validate_files([clean_file, bad_file])

        assert is_valid is False
        assert validator.checked_files == 2
        assert len(validator.violations) == 1

    def test_validate_files_skips_non_python(self, tmp_path: Path) -> None:
        """Test that validate_files skips non-Python files."""
        text_file = tmp_path / "readme.txt"
        text_file.write_text("from omnibase_infra import kafka")

        json_file = tmp_path / "config.json"
        json_file.write_text('{"import": "omnibase_infra"}')

        validator = InfraImportValidator()
        is_valid = validator.validate_files([text_file, json_file])

        assert is_valid is True
        assert validator.checked_files == 0


@pytest.mark.unit
class TestInfraImportValidatorReport:
    """Tests for the report generation."""

    def test_generate_report_no_violations(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test report generation when there are no violations."""
        test_file = tmp_path / "clean.py"
        test_file.write_text("import os")

        validator = InfraImportValidator()
        validator.validate_file(test_file)
        validator.generate_report()

        captured = capsys.readouterr()
        assert "SUCCESS" in captured.out
        assert "No omnibase_infra imports found" in captured.out

    def test_generate_report_with_violations(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test report generation when there are violations."""
        test_file = tmp_path / "bad.py"
        test_file.write_text("from omnibase_infra import kafka")

        validator = InfraImportValidator()
        validator.validate_file(test_file)
        validator.generate_report()

        captured = capsys.readouterr()
        assert "FAIL" in captured.out
        assert "violation(s)" in captured.out
        assert "omnibase_infra" in captured.out

    def test_generate_report_shows_errors(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that errors are included in the report."""
        test_file = tmp_path / "syntax_error.py"
        test_file.write_text("def incomplete(")

        validator = InfraImportValidator()
        validator.validate_file(test_file)
        validator.generate_report()

        captured = capsys.readouterr()
        assert "Warnings/Errors" in captured.out

    def test_generate_report_shows_architectural_guidance(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that architectural guidance is shown for violations."""
        test_file = tmp_path / "bad.py"
        test_file.write_text("from omnibase_infra import kafka")

        validator = InfraImportValidator()
        validator.validate_file(test_file)
        validator.generate_report()

        captured = capsys.readouterr()
        assert "Architectural" in captured.out
        assert "How to Fix" in captured.out


@pytest.mark.unit
class TestMainFunction:
    """Tests for the main() entry point."""

    def test_main_returns_zero_for_clean_files(self, tmp_path: Path) -> None:
        """Test that main returns 0 when no violations found."""
        clean_file = tmp_path / "clean.py"
        clean_file.write_text("import os")

        with patch.object(sys, "argv", ["validate-no-infra-imports.py", str(tmp_path)]):
            result = main()
            assert result == 0

    def test_main_returns_one_for_violations(self, tmp_path: Path) -> None:
        """Test that main returns 1 when violations found."""
        bad_file = tmp_path / "bad.py"
        bad_file.write_text("from omnibase_infra import kafka")

        with patch.object(sys, "argv", ["validate-no-infra-imports.py", str(tmp_path)]):
            result = main()
            assert result == 1

    def test_main_quiet_mode(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that --quiet flag suppresses output."""
        clean_file = tmp_path / "clean.py"
        clean_file.write_text("import os")

        with patch.object(
            sys, "argv", ["validate-no-infra-imports.py", "--quiet", str(tmp_path)]
        ):
            main()

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_main_quiet_mode_with_violations(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that --quiet flag suppresses output even with violations.

        Quiet mode suppresses all report output but still returns correct exit code.
        This is useful for pre-commit hooks where only the exit code matters.
        """
        bad_file = tmp_path / "bad.py"
        bad_file.write_text("from omnibase_infra import kafka")

        with patch.object(
            sys, "argv", ["validate-no-infra-imports.py", "--quiet", str(tmp_path)]
        ):
            result = main()

        captured = capsys.readouterr()
        # Quiet mode suppresses all output, including violation reports
        assert captured.out == ""
        # But the exit code should still indicate failure
        assert result == 1

    def test_main_verbose_mode(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that --verbose flag works (currently no additional output)."""
        clean_file = tmp_path / "clean.py"
        clean_file.write_text("import os")

        with patch.object(
            sys, "argv", ["validate-no-infra-imports.py", "--verbose", str(tmp_path)]
        ):
            result = main()

        assert result == 0
        captured = capsys.readouterr()
        assert "SUCCESS" in captured.out

    def test_main_pass_filenames_mode(self, tmp_path: Path) -> None:
        """Test pass_filenames mode (pre-commit integration)."""
        clean_file = tmp_path / "clean.py"
        clean_file.write_text("import os")

        bad_file = tmp_path / "bad.py"
        bad_file.write_text("from omnibase_infra import kafka")

        with patch.object(
            sys,
            "argv",
            ["validate-no-infra-imports.py", str(clean_file), str(bad_file)],
        ):
            result = main()
            assert result == 1

    def test_main_no_python_files(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test handling when no Python files are found."""
        text_file = tmp_path / "readme.txt"
        text_file.write_text("Just a readme")

        with patch.object(
            sys, "argv", ["validate-no-infra-imports.py", str(text_file)]
        ):
            result = main()

        assert result == 0
        captured = capsys.readouterr()
        assert "No Python files" in captured.out

    def test_main_default_path(self) -> None:
        """Test that main uses default path when none specified."""
        with patch.object(sys, "argv", ["validate-no-infra-imports.py"]):
            # Will either find the default dir or return error code 1
            result = main()
            assert result in (0, 1)

    def test_main_nonexistent_default_path(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test handling when default path doesn't exist."""
        # Change to a temp directory where src/omnibase_core doesn't exist
        import os

        original_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            with patch.object(sys, "argv", ["validate-no-infra-imports.py"]):
                result = main()
            assert result == 1
            captured = capsys.readouterr()
            assert "does not exist" in captured.out
        finally:
            os.chdir(original_cwd)


@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_handles_empty_file(self, tmp_path: Path) -> None:
        """Test handling of empty files."""
        empty_file = tmp_path / "empty.py"
        empty_file.write_text("")

        validator = InfraImportValidator()
        is_valid = validator.validate_file(empty_file)

        assert is_valid is True
        assert len(validator.violations) == 0

    def test_handles_comments_only_file(self, tmp_path: Path) -> None:
        """Test handling of files with only comments."""
        comments_file = tmp_path / "comments.py"
        comments_file.write_text(
            """
# This is a comment
# from omnibase_infra import kafka
# import omnibase_infra
"""
        )
        validator = InfraImportValidator()
        is_valid = validator.validate_file(comments_file)

        assert is_valid is True
        assert len(validator.violations) == 0

    def test_handles_string_containing_import(self, tmp_path: Path) -> None:
        """Test that imports in strings don't trigger violations."""
        string_file = tmp_path / "strings.py"
        string_file.write_text(
            '''
message = "from omnibase_infra import kafka"
doc = """
import omnibase_infra
"""
'''
        )
        validator = InfraImportValidator()
        is_valid = validator.validate_file(string_file)

        assert is_valid is True
        assert len(validator.violations) == 0

    def test_handles_conditional_import(self, tmp_path: Path) -> None:
        """Test detection of conditional imports."""
        conditional_file = tmp_path / "conditional.py"
        conditional_file.write_text(
            """
if TYPE_CHECKING:
    from omnibase_infra import types
"""
        )
        validator = InfraImportValidator()
        is_valid = validator.validate_file(conditional_file)

        # Conditional imports are still detected
        assert is_valid is False
        assert len(validator.violations) == 1

    def test_handles_try_except_import(self, tmp_path: Path) -> None:
        """Test detection of imports in try/except blocks."""
        try_file = tmp_path / "try_import.py"
        try_file.write_text(
            """
try:
    from omnibase_infra import kafka
except ImportError:
    kafka = None
"""
        )
        validator = InfraImportValidator()
        is_valid = validator.validate_file(try_file)

        # Imports in try blocks are still detected
        assert is_valid is False
        assert len(validator.violations) == 1

    def test_handles_unicode_file(self, tmp_path: Path) -> None:
        """Test handling of files with Unicode content."""
        unicode_file = tmp_path / "unicode.py"
        unicode_file.write_text(
            """
# This file has Unicode:
from omnibase_infra import kafka
""",
            encoding="utf-8",
        )

        validator = InfraImportValidator()
        is_valid = validator.validate_file(unicode_file)

        assert is_valid is False
        assert len(validator.violations) == 1

    def test_handles_file_read_error(self, tmp_path: Path) -> None:
        """Test handling of file read errors by mocking file open."""
        from unittest.mock import patch

        test_file = tmp_path / "error.py"
        test_file.write_text("# placeholder")

        # Mock the builtin open to raise OSError when reading this file
        original_open = open

        def mock_open_error(path, *args, **kwargs):
            if str(path) == str(test_file):
                raise OSError("Permission denied")
            return original_open(path, *args, **kwargs)

        validator = InfraImportValidator()
        with patch("builtins.open", side_effect=mock_open_error):
            is_valid = validator.validate_file(test_file)

        # Should handle gracefully
        assert is_valid is True
        assert len(validator.errors) == 1
        assert "Permission denied" in validator.errors[0]


@pytest.mark.unit
class TestDiscoveryPatterns:
    """Tests for file discovery patterns."""

    def test_discovers_python_files_recursively(self, tmp_path: Path) -> None:
        """Test that Python files are discovered recursively."""
        (tmp_path / "level1.py").write_text("import os")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "level2.py").write_text("import sys")
        (tmp_path / "subdir" / "deeper").mkdir()
        (tmp_path / "subdir" / "deeper" / "level3.py").write_text("import pathlib")

        validator = InfraImportValidator()
        validator.validate_path(tmp_path)

        assert validator.checked_files == 3

    def test_skips_common_excluded_dirs(self, tmp_path: Path) -> None:
        """Test that common excluded directories are skipped."""
        excluded_dirs = [
            "__pycache__",
            ".git",
            ".pytest_cache",
            ".mypy_cache",
            ".venv",
            "venv",
            ".tox",
            "node_modules",
            "build",
            "dist",
            "archived",
            "archive",
        ]

        for dir_name in excluded_dirs:
            excluded = tmp_path / dir_name
            excluded.mkdir()
            (excluded / "module.py").write_text("from omnibase_infra import kafka")

        # Also create a valid file to check
        (tmp_path / "valid.py").write_text("import os")

        validator = InfraImportValidator()
        is_valid = validator.validate_path(tmp_path)

        assert is_valid is True
        assert validator.checked_files == 1
        assert len(validator.violations) == 0

    def test_handles_single_file_path(self, tmp_path: Path) -> None:
        """Test validation of a single file path."""
        single_file = tmp_path / "module.py"
        single_file.write_text("from omnibase_infra import kafka")

        validator = InfraImportValidator()
        is_valid = validator.validate_path(single_file)

        assert is_valid is False
        assert validator.checked_files == 1
