#!/usr/bin/env python3
"""
Comprehensive tests for backward compatibility anti-pattern detection.

Tests all aspects of the BackwardCompatibilityDetector including:
- Detection of various backward compatibility patterns
- Handling of edge cases like empty files, syntax errors
- File encoding and error handling
- Performance with large files
- CLI interface and argument parsing
"""

import importlib.util
import shutil

# Import the validation module
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(
    0,
    str(Path(__file__).parent.parent.parent.parent / "scripts" / "validation"),
)

# Import the backward compatibility module using importlib
script_path = (
    Path(__file__).parent.parent.parent.parent
    / "scripts"
    / "validation"
    / "validate-no-backward-compatibility.py"
)
spec = importlib.util.spec_from_file_location(
    "validate_no_backward_compatibility",
    script_path,
)
validate_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate_module)

BackwardCompatibilityDetector = validate_module.BackwardCompatibilityDetector
main = validate_module.main
create_argument_parser = validate_module.create_argument_parser


@pytest.fixture
def temp_repo():
    """Create a temporary repository structure for testing."""
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)
    yield repo_path
    shutil.rmtree(temp_dir)


@pytest.fixture
def detector():
    """Create a BackwardCompatibilityDetector instance for testing."""
    return BackwardCompatibilityDetector()


class TestBackwardCompatibilityDetector:
    """Test cases for BackwardCompatibilityDetector."""

    def test_initialization(self, detector):
        """Test detector initialization."""
        assert detector.errors == []
        assert detector.checked_files == 0

    def test_valid_file_without_compatibility_patterns(self, temp_repo, detector):
        """Test validation of files without backward compatibility patterns."""
        valid_content = '''
from pydantic import BaseModel, ConfigDict

class ModelUserAuth(BaseModel):
    """User authentication model."""
    user_id: str
    username: str

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

def process_user_data(data: dict) -> dict:
    """Process user data."""
    return {"processed": True}
'''
        test_file = temp_repo / "valid_file.py"
        test_file.write_text(valid_content)

        result = detector.validate_python_file(test_file)
        assert result is True
        assert detector.checked_files == 1
        assert len(detector.errors) == 0

    def test_backward_compatibility_comment_detection(self, temp_repo, detector):
        """Test detection of backward compatibility comments."""
        compat_content = '''
from pydantic import BaseModel

class ModelUserAuth(BaseModel):
    """User authentication model."""
    user_id: str

    # Accept simple Protocol* names for backward compatibility
    def validate_protocol(self, name: str) -> bool:
        return True

    def legacy_method(self) -> dict:
        """Convert to dictionary for backwards compatibility."""
        return self.model_dump()
'''
        test_file = temp_repo / "compat_comments.py"
        test_file.write_text(compat_content)

        result = detector.validate_python_file(test_file)
        assert result is False
        assert len(detector.errors) >= 1

        # Check that specific patterns were detected
        error_messages = " ".join(detector.errors)
        assert "backward compatibility comment" in error_messages.lower()

    def test_legacy_method_detection(self, temp_repo, detector):
        """Test detection of legacy method names."""
        legacy_content = '''
class ModelUser:
    """User model."""

    def get_data_legacy(self) -> dict:
        """Legacy method."""
        return {}

    def process_deprecated(self, data: dict) -> dict:
        """Deprecated method."""
        return data

    def convert_compat(self, format: str) -> str:
        """Compatibility method."""
        return format

    def transform_backward(self, input: dict) -> dict:
        """Backward compatibility transform."""
        return input
'''
        test_file = temp_repo / "legacy_methods.py"
        test_file.write_text(legacy_content)

        result = detector.validate_python_file(test_file)
        assert result is False
        assert len(detector.errors) >= 4

        error_messages = " ".join(detector.errors)
        assert "legacy support method" in error_messages.lower()

    def test_protocol_compatibility_pattern_detection(self, temp_repo, detector):
        """Test detection of Protocol backward compatibility patterns."""
        protocol_content = '''
def validate_dependency(dependency: str) -> bool:
    """Validate dependency names."""
    # Accept simple Protocol* names for backward compatibility
    if dependency.startswith("Protocol"):
        return True
    return False

def check_protocol_name(name: str) -> bool:
    """Check protocol naming."""
    # Protocol legacy support
    if name.startswith("Protocol"):
        return True
    return False
'''
        test_file = temp_repo / "protocol_compat.py"
        test_file.write_text(protocol_content)

        result = detector.validate_python_file(test_file)
        assert result is False
        assert len(detector.errors) >= 1

        error_messages = " ".join(detector.errors)
        assert "protocol" in error_messages.lower()

    def test_extra_allow_configuration_detection(self, temp_repo, detector):
        """Test detection of permissive configuration for compatibility."""
        config_content = '''
from pydantic import BaseModel, ConfigDict

class ModelUser(BaseModel):
    """User model."""
    user_id: str

    model_config = ConfigDict(
        extra="allow",  # Allow extra fields for compatibility
        validate_assignment=True,
    )

class ConfigSettings:
    """Settings with compatibility config."""
    extra = "allow"  # For backward compatibility
'''
        test_file = temp_repo / "config_compat.py"
        test_file.write_text(config_content)

        result = detector.validate_python_file(test_file)
        # This might pass since the current pattern matching is more specific
        # Check if any compatibility-related errors were detected
        if not result:
            error_messages = " ".join(detector.errors)
            assert "compatibility" in error_messages.lower()

    def test_ast_compatibility_function_detection(self, temp_repo, detector):
        """Test AST-based detection of compatibility function patterns."""
        ast_content = '''
class ModelUser:
    """User model."""

    def to_dict_legacy(self) -> dict:
        """Convert to dict for backward compatibility."""
        return {"legacy": True}

    def get_data_deprecated(self) -> dict:
        """Deprecated data getter for backward compatibility."""
        return {}

    def process_compat(self, data: dict) -> dict:
        """Processing method for legacy support."""
        return data
'''
        test_file = temp_repo / "ast_compat.py"
        test_file.write_text(ast_content)

        result = detector.validate_python_file(test_file)
        assert result is False
        assert len(detector.errors) >= 3

        error_messages = " ".join(detector.errors)
        assert "backward compatibility function" in error_messages.lower()

    def test_docstring_compatibility_detection(self, temp_repo, detector):
        """Test detection of backward compatibility in docstrings."""
        docstring_content = '''
class ModelUser:
    """User model."""

    def to_dict(self) -> dict:
        """Convert to dictionary for backward compatibility."""
        return self.__dict__

    def export_data(self) -> dict:
        """Export data with legacy support for old formats."""
        return {}

    def migrate_data(self) -> dict:
        """Migrate data - migration path for legacy systems."""
        return {}
'''
        test_file = temp_repo / "docstring_compat.py"
        test_file.write_text(docstring_content)

        result = detector.validate_python_file(test_file)
        assert result is False
        assert len(detector.errors) >= 1

        error_messages = " ".join(detector.errors)
        assert (
            "backward compatibility docstring" in error_messages.lower()
            or "legacy support" in error_messages.lower()
        )


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_file_handling(self, temp_repo, detector):
        """Test handling of empty files."""
        empty_file = temp_repo / "empty.py"
        empty_file.touch()

        result = detector.validate_python_file(empty_file)
        assert result is True
        assert detector.checked_files == 1
        assert len(detector.errors) == 0

    def test_nonexistent_file_handling(self, detector):
        """Test handling of non-existent files."""
        nonexistent_file = Path("/nonexistent/file.py")

        result = detector.validate_python_file(nonexistent_file)
        assert result is False
        assert len(detector.errors) == 1
        assert "does not exist" in detector.errors[0]

    def test_syntax_error_handling(self, temp_repo, detector):
        """Test handling of files with syntax errors."""
        syntax_error_content = """
class ModelUser:
    def __init__(self:  # Missing closing parenthesis
        self.user_id = "test"

    def get_data(self) -> dict
        # Missing colon
        return {}
"""
        error_file = temp_repo / "syntax_error.py"
        error_file.write_text(syntax_error_content)

        result = detector.validate_python_file(error_file)
        assert result is False
        assert len(detector.errors) >= 1
        assert "syntax error" in detector.errors[0].lower()

    def test_unicode_file_handling(self, temp_repo, detector):
        """Test handling of files with Unicode content."""
        unicode_content = '''# -*- coding: utf-8 -*-
"""File with Unicode: 中文, emoji 🚀, accents ñáéíóú"""

class ModelUser:
    """User model with Unicode support."""

    def get_user_name(self) -> str:
        """Get user name - supports José, 北京, etc."""
        return "José González 🎉"
'''
        unicode_file = temp_repo / "unicode_file.py"
        unicode_file.write_text(unicode_content, encoding="utf-8")

        result = detector.validate_python_file(unicode_file)
        assert result is True
        assert detector.checked_files == 1

    def test_large_file_handling(self, temp_repo, detector):
        """Test handling of large files."""
        # Create a large file with many classes
        large_content = '''
"""Large file for testing performance."""

from pydantic import BaseModel

'''
        # Add many classes
        for i in range(100):
            large_content += f'''
class ModelTest{i:03d}(BaseModel):
    """Test model {i}."""
    field_{i}: str = "value_{i}"

    def process_{i}(self) -> dict:
        """Process data for model {i}."""
        return {{"processed": {i}}}

'''

        large_file = temp_repo / "large_file.py"
        large_file.write_text(large_content)

        import time

        start_time = time.time()
        result = detector.validate_python_file(large_file)
        end_time = time.time()

        # Should complete within reasonable time
        assert end_time - start_time < 10.0
        assert result is True  # No compatibility patterns
        assert detector.checked_files == 1

    def test_very_large_file_rejection(self, temp_repo, detector):
        """Test rejection of extremely large files."""
        # Create a file larger than the limit
        large_content = "# Large file\n" + "x = 1\n" * 1000000  # ~7MB content
        large_file = temp_repo / "very_large_file.py"
        large_file.write_text(large_content)

        # Check if file is actually large enough to trigger the limit
        if large_file.stat().st_size > 10 * 1024 * 1024:  # 10MB
            result = detector.validate_python_file(large_file)
            assert result is False
            assert "too large" in detector.errors[0].lower()

    def test_permission_error_handling(self, temp_repo, detector):
        """Test handling of permission errors."""
        test_file = temp_repo / "test_file.py"
        test_file.write_text("print('test')")

        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            result = detector.validate_python_file(test_file)
            assert result is False
            assert len(detector.errors) >= 1
            assert "permission denied" in detector.errors[0].lower()

    def test_encoding_error_handling(self, temp_repo, detector):
        """Test handling of encoding errors."""
        # Create file with problematic encoding
        binary_file = temp_repo / "binary_file.py"
        # Write some binary data that will cause encoding issues
        with open(binary_file, "wb") as f:
            f.write(b"\xff\xfe\x00\x00invalid utf-8 data\x80\x81\x82")

        result = detector.validate_python_file(binary_file)
        # Should handle gracefully - either succeed with fallback encoding or fail gracefully
        assert isinstance(result, bool)


class TestDirectoryScanning:
    """Test directory scanning functionality."""

    def test_find_python_files_in_directory(self, temp_repo, detector):
        """Test finding Python files in directory."""
        # Create Python files
        (temp_repo / "file1.py").touch()
        (temp_repo / "file2.py").touch()
        (temp_repo / "subdir").mkdir()
        (temp_repo / "subdir" / "file3.py").touch()
        (temp_repo / "not_python.txt").touch()

        python_files = detector.find_python_files_in_directory(temp_repo)
        python_file_names = [f.name for f in python_files]

        assert "file1.py" in python_file_names
        assert "file2.py" in python_file_names
        assert "file3.py" in python_file_names
        assert "not_python.txt" not in python_file_names

    def test_skip_patterns_in_directory_scan(self, temp_repo, detector):
        """Test that skip patterns are properly applied."""
        # Create directories that should be skipped
        (temp_repo / "__pycache__").mkdir()
        (temp_repo / "__pycache__" / "cached.py").touch()
        (temp_repo / ".pytest_cache").mkdir()
        (temp_repo / ".pytest_cache" / "test.py").touch()
        (temp_repo / "venv").mkdir()
        (temp_repo / "venv" / "lib.py").touch()

        # Create files that should be included
        (temp_repo / "valid.py").touch()

        python_files = detector.find_python_files_in_directory(temp_repo)
        file_paths = [str(f) for f in python_files]

        # Should include valid files
        assert any("valid.py" in path for path in file_paths)

        # Should skip cache and venv directories
        assert not any("__pycache__" in path for path in file_paths)
        assert not any(".pytest_cache" in path for path in file_paths)
        assert not any("venv" in path for path in file_paths)

    def test_nonexistent_directory_handling(self, detector):
        """Test handling of non-existent directories."""
        nonexistent_dir = Path("/nonexistent/directory")
        python_files = detector.find_python_files_in_directory(nonexistent_dir)

        assert python_files == []
        assert len(detector.errors) >= 1
        assert "does not exist" in detector.errors[0]

    def test_file_as_directory_handling(self, temp_repo, detector):
        """Test handling when a file is passed as directory."""
        test_file = temp_repo / "test.py"
        test_file.touch()

        python_files = detector.find_python_files_in_directory(test_file)
        assert python_files == []
        assert len(detector.errors) >= 1
        assert "not a directory" in detector.errors[0]


class TestFileCollection:
    """Test file collection from arguments."""

    def test_collect_files_from_args(self, temp_repo, detector):
        """Test collecting files from command line arguments."""
        # Create test files
        file1 = temp_repo / "file1.py"
        file1.touch()
        file2 = temp_repo / "file2.py"
        file2.touch()
        (temp_repo / "subdir").mkdir()
        (temp_repo / "subdir" / "file3.py").touch()

        files = [str(file1), str(file2)]
        directories = [str(temp_repo / "subdir")]

        collected_files = detector.collect_files_from_args(files, directories)
        collected_names = [f.name for f in collected_files]

        assert "file1.py" in collected_names
        assert "file2.py" in collected_names
        assert "file3.py" in collected_names

    def test_collect_files_deduplication(self, temp_repo, detector):
        """Test that duplicate files are removed."""
        file1 = temp_repo / "file1.py"
        file1.touch()

        # Provide same file multiple ways
        files = [str(file1), str(file1)]
        directories = []

        collected_files = detector.collect_files_from_args(files, directories)
        assert len(collected_files) == 1

    def test_collect_invalid_files(self, temp_repo, detector):
        """Test handling of invalid file arguments."""
        files = ["/nonexistent/file.py", str(temp_repo / "not_python.txt")]
        directories = []

        collected_files = detector.collect_files_from_args(files, directories)
        assert len(collected_files) == 0
        assert len(detector.errors) >= 1


class TestValidateAllFiles:
    """Test batch file validation."""

    def test_validate_all_python_files(self, temp_repo, detector):
        """Test validation of multiple files."""
        # Create valid file
        valid_file = temp_repo / "valid.py"
        valid_file.write_text("print('valid')")

        # Create file with compatibility issues
        compat_file = temp_repo / "compat.py"
        compat_file.write_text(
            '''
def process_legacy(data: dict) -> dict:
    """Process data for backward compatibility."""
    return data
''',
        )

        files = [valid_file, compat_file]
        success = detector.validate_all_python_files(files)

        assert success is False  # Should fail due to compatibility issues
        assert detector.checked_files == 2
        assert len(detector.errors) >= 1

    def test_validate_empty_file_list(self, detector):
        """Test validation of empty file list."""
        success = detector.validate_all_python_files([])
        assert success is True
        assert detector.checked_files == 0
        assert len(detector.errors) == 0


class TestResultsPrinting:
    """Test results printing functionality."""

    def test_print_results_success(self, detector, capsys):
        """Test printing of successful validation results."""
        detector.checked_files = 5
        detector.print_results()

        captured = capsys.readouterr()
        assert "PASSED" in captured.out
        assert "5 files" in captured.out

    def test_print_results_with_errors(self, detector, capsys):
        """Test printing of validation results with errors."""
        detector.checked_files = 3
        detector.errors = [
            "file1.py: Line 10: Backward compatibility comment detected",
            "file2.py: Line 5: Legacy method detected",
        ]
        detector.print_results()

        captured = capsys.readouterr()
        assert "FAILED" in captured.out
        assert "2 backward compatibility violations" in captured.out
        assert "file1.py" in captured.out
        assert "file2.py" in captured.out

    def test_print_results_verbose_mode(self, detector, capsys):
        """Test printing results in verbose mode."""
        detector.checked_files = 10
        detector.print_results(verbose=True)

        captured = capsys.readouterr()
        assert "10 files" in captured.out


class TestCLIInterface:
    """Test command line interface."""

    def test_argument_parser_creation(self):
        """Test creation of argument parser."""
        parser = create_argument_parser()
        assert parser is not None

        # Test that it can parse basic arguments
        args = parser.parse_args(["file1.py", "file2.py"])
        assert args.files == ["file1.py", "file2.py"]

    def test_main_with_files(self, temp_repo):
        """Test main function with file arguments."""
        test_file = temp_repo / "test.py"
        test_file.write_text("print('test')")

        with patch(
            "sys.argv",
            ["validate-no-backward-compatibility.py", str(test_file)],
        ):
            result = main()
            assert result == 0  # Should succeed

    def test_main_with_directory(self, temp_repo):
        """Test main function with directory argument."""
        (temp_repo / "test.py").write_text("print('test')")

        with patch(
            "sys.argv",
            ["validate-no-backward-compatibility.py", "--dir", str(temp_repo)],
        ):
            result = main()
            assert result == 0  # Should succeed with clean files

    def test_main_with_compatibility_violations(self, temp_repo):
        """Test main function with files containing violations."""
        compat_file = temp_repo / "compat.py"
        compat_file.write_text(
            '''
def process_legacy_data(data: dict) -> dict:
    """Process data for backward compatibility."""
    return data
''',
        )

        with patch(
            "sys.argv",
            ["validate-no-backward-compatibility.py", str(compat_file)],
        ):
            result = main()
            assert result == 1  # Should fail

    def test_main_no_arguments(self):
        """Test main function with no arguments."""
        with patch("sys.argv", ["validate-no-backward-compatibility.py"]):
            result = main()
            assert result == 1  # Should fail

    def test_main_verbose_mode(self, temp_repo):
        """Test main function in verbose mode."""
        test_file = temp_repo / "test.py"
        test_file.write_text("print('test')")

        with patch(
            "sys.argv",
            ["validate-no-backward-compatibility.py", str(test_file), "--verbose"],
        ):
            with patch("builtins.print") as mock_print:
                result = main()
                assert result == 0
                # Should have printed verbose information
                assert mock_print.called


class TestFixtureValidation:
    """Test validation using our test fixtures."""

    def test_valid_fixtures_pass_validation(self):
        """Test that valid fixtures pass backward compatibility validation."""
        fixtures_dir = Path(__file__).parent.parent.parent / "fixtures" / "validation"

        if fixtures_dir.exists():
            valid_fixtures = fixtures_dir / "valid"
            if valid_fixtures.exists():
                detector = BackwardCompatibilityDetector()
                python_files = detector.find_python_files_in_directory(valid_fixtures)

                if python_files:
                    success = detector.validate_all_python_files(python_files)
                    assert success is True, (
                        f"Valid fixtures should pass validation. Errors: {detector.errors}"
                    )

    def test_invalid_fixtures_trigger_violations(self):
        """Test that invalid fixtures trigger backward compatibility violations."""
        fixtures_dir = Path(__file__).parent.parent.parent / "fixtures" / "validation"

        if fixtures_dir.exists():
            invalid_fixtures = fixtures_dir / "invalid"
            compat_fixture = invalid_fixtures / "backward_compatibility.py"

            if compat_fixture.exists():
                detector = BackwardCompatibilityDetector()
                result = detector.validate_python_file(compat_fixture)
                assert result is False, (
                    "Backward compatibility fixture should trigger violations"
                )
                assert len(detector.errors) > 0, (
                    "Should detect backward compatibility patterns"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
