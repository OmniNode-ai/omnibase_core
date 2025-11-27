"""
Test suite for CircularImportValidator.

Tests circular import detection, file discovery, module name conversion,
and validation reporting functionality.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_import_status import EnumImportStatus
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.model_import_validation_result import ModelValidationResult
from omnibase_core.models.model_module_import_result import ModelModuleImportResult
from omnibase_core.validation.circular_import_validator import CircularImportValidator


class TestCircularImportValidatorInitialization:
    """Test CircularImportValidator initialization."""

    def test_initialization_with_valid_path(self, tmp_path: Path) -> None:
        """Test initialization with valid source path."""
        validator = CircularImportValidator(source_path=tmp_path)

        assert validator.source_path == tmp_path
        assert validator.include_patterns == ["*.py"]
        assert validator.exclude_patterns == ["__pycache__", "archived"]
        assert validator.verbose is False
        assert validator.progress_callback is None

    def test_initialization_with_custom_patterns(self, tmp_path: Path) -> None:
        """Test initialization with custom include/exclude patterns."""
        validator = CircularImportValidator(
            source_path=tmp_path,
            include_patterns=["*.py", "*.pyx"],
            exclude_patterns=["test_*.py", "archived", "__pycache__"],
        )

        assert validator.include_patterns == ["*.py", "*.pyx"]
        assert validator.exclude_patterns == ["test_*.py", "archived", "__pycache__"]

    def test_initialization_with_verbose_mode(self, tmp_path: Path) -> None:
        """Test initialization with verbose mode enabled."""
        validator = CircularImportValidator(source_path=tmp_path, verbose=True)

        assert validator.verbose is True

    def test_initialization_with_progress_callback(self, tmp_path: Path) -> None:
        """Test initialization with progress callback."""
        callback = Mock()
        validator = CircularImportValidator(
            source_path=tmp_path, progress_callback=callback
        )

        assert validator.progress_callback is callback

    def test_initialization_with_string_path(self, tmp_path: Path) -> None:
        """Test initialization with string path (converts to Path)."""
        validator = CircularImportValidator(source_path=str(tmp_path))

        assert validator.source_path == tmp_path
        assert isinstance(validator.source_path, Path)

    def test_initialization_with_nonexistent_path(self) -> None:
        """Test initialization with nonexistent path raises error."""
        nonexistent_path = Path("/nonexistent/path/that/does/not/exist")

        with pytest.raises(ModelOnexError) as exc_info:
            CircularImportValidator(source_path=nonexistent_path)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "does not exist" in str(exc_info.value.message)


class TestCircularImportValidatorFileDiscovery:
    """Test file discovery functionality."""

    def test_discover_python_files_basic(self, tmp_path: Path) -> None:
        """Test discovering basic Python files."""
        # Create test files
        (tmp_path / "module1.py").touch()
        (tmp_path / "module2.py").touch()
        (tmp_path / "README.md").touch()  # Should be ignored

        validator = CircularImportValidator(source_path=tmp_path)
        files = validator._discover_python_files()

        assert len(files) == 2
        assert all(f.suffix == ".py" for f in files)

    def test_discover_python_files_with_subdirectories(self, tmp_path: Path) -> None:
        """Test discovering Python files in subdirectories."""
        # Create nested structure
        (tmp_path / "module1.py").touch()
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "module2.py").touch()
        (subdir / "module3.py").touch()

        validator = CircularImportValidator(source_path=tmp_path)
        files = validator._discover_python_files()

        assert len(files) == 3

    def test_discover_python_files_excludes_pycache(self, tmp_path: Path) -> None:
        """Test that __pycache__ directories are excluded."""
        # Create files
        (tmp_path / "module1.py").touch()
        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "module1.cpython-312.pyc").touch()

        validator = CircularImportValidator(source_path=tmp_path)
        files = validator._discover_python_files()

        # Should only find module1.py, not the .pyc file
        assert len(files) == 1
        assert files[0].name == "module1.py"

    def test_discover_python_files_custom_exclude_pattern(self, tmp_path: Path) -> None:
        """Test custom exclude pattern."""
        # Create test files
        (tmp_path / "module1.py").touch()
        (tmp_path / "skip_module.py").touch()
        (tmp_path / "module2.py").touch()

        validator = CircularImportValidator(
            source_path=tmp_path, exclude_patterns=["skip_"]
        )
        files = validator._discover_python_files()

        # skip_module.py should be excluded
        assert len(files) == 2
        assert all("skip_" not in f.name for f in files)

    def test_should_exclude_method(self, tmp_path: Path) -> None:
        """Test _should_exclude method."""
        validator = CircularImportValidator(
            source_path=tmp_path, exclude_patterns=["skip_", "archived"]
        )

        assert validator._should_exclude(Path("/path/skip_something.py")) is True
        assert validator._should_exclude(Path("/path/archived/file.py")) is True
        assert validator._should_exclude(Path("/path/regular_file.py")) is False


class TestCircularImportValidatorModuleNameConversion:
    """Test module name conversion functionality."""

    def test_path_to_module_name_basic(self, tmp_path: Path) -> None:
        """Test basic path to module name conversion."""
        # Create file
        file_path = tmp_path / "mymodule.py"
        file_path.touch()

        validator = CircularImportValidator(source_path=tmp_path)
        module_name = validator._path_to_module_name(file_path)

        assert module_name == "mymodule"

    def test_path_to_module_name_nested(self, tmp_path: Path) -> None:
        """Test nested path to module name conversion."""
        # Create nested structure
        subdir = tmp_path / "package" / "subpackage"
        subdir.mkdir(parents=True)
        file_path = subdir / "module.py"
        file_path.touch()

        validator = CircularImportValidator(source_path=tmp_path)
        module_name = validator._path_to_module_name(file_path)

        assert module_name == "package.subpackage.module"

    def test_path_to_module_name_init_file(self, tmp_path: Path) -> None:
        """Test __init__.py conversion."""
        # Create package with __init__.py
        package_dir = tmp_path / "mypackage"
        package_dir.mkdir()
        init_file = package_dir / "__init__.py"
        init_file.touch()

        validator = CircularImportValidator(source_path=tmp_path)
        module_name = validator._path_to_module_name(init_file)

        assert module_name == "mypackage"

    def test_path_to_module_name_root_init(self, tmp_path: Path) -> None:
        """Test __init__.py at root returns None."""
        init_file = tmp_path / "__init__.py"
        init_file.touch()

        validator = CircularImportValidator(source_path=tmp_path)
        module_name = validator._path_to_module_name(init_file)

        assert module_name is None

    def test_path_to_module_name_outside_source(self, tmp_path: Path) -> None:
        """Test path outside source directory returns None."""
        other_path = Path("/some/other/path/module.py")

        validator = CircularImportValidator(source_path=tmp_path)
        module_name = validator._path_to_module_name(other_path)

        assert module_name is None

    def test_path_to_module_name_preserves_py_in_middle(self, tmp_path: Path) -> None:
        """Test that 'py' in middle of path is preserved."""
        # Create path with 'py' in directory name
        subdir = tmp_path / "pydantic_models"
        subdir.mkdir()
        file_path = subdir / "schema.py"
        file_path.touch()

        validator = CircularImportValidator(source_path=tmp_path)
        module_name = validator._path_to_module_name(file_path)

        # Should be "pydantic_models.schema", not "dantic_models.schema"
        assert module_name == "pydantic_models.schema"


class TestCircularImportValidatorImportTesting:
    """Test import testing functionality."""

    def test_test_import_success(self, tmp_path: Path) -> None:
        """Test successful import."""
        validator = CircularImportValidator(source_path=tmp_path)

        # Use a real module that exists
        with patch("importlib.import_module") as mock_import:
            mock_import.return_value = None
            result = validator._test_import("json", tmp_path / "json.py")

        assert result.module_name == "json"
        assert result.status == EnumImportStatus.SUCCESS
        assert result.file_path == str(tmp_path / "json.py")
        assert result.error_message is None

    def test_test_import_circular_import_error(self, tmp_path: Path) -> None:
        """Test detection of circular import."""
        validator = CircularImportValidator(source_path=tmp_path)

        with patch("importlib.import_module") as mock_import:
            mock_import.side_effect = ImportError("circular import detected")
            result = validator._test_import("bad_module", tmp_path / "bad_module.py")

        assert result.module_name == "bad_module"
        assert result.status == EnumImportStatus.CIRCULAR_IMPORT
        assert "circular import" in result.error_message.lower()

    def test_test_import_regular_import_error(self, tmp_path: Path) -> None:
        """Test regular import error (not circular)."""
        validator = CircularImportValidator(source_path=tmp_path)

        with patch("importlib.import_module") as mock_import:
            mock_import.side_effect = ImportError("No module named 'nonexistent'")
            result = validator._test_import("nonexistent", tmp_path / "nonexistent.py")

        assert result.module_name == "nonexistent"
        assert result.status == EnumImportStatus.IMPORT_ERROR
        assert "No module named" in result.error_message

    def test_test_import_unexpected_error(self, tmp_path: Path) -> None:
        """Test unexpected error during import."""
        validator = CircularImportValidator(source_path=tmp_path)

        with patch("importlib.import_module") as mock_import:
            mock_import.side_effect = RuntimeError("Unexpected error")
            result = validator._test_import("broken", tmp_path / "broken.py")

        assert result.module_name == "broken"
        assert result.status == EnumImportStatus.UNEXPECTED_ERROR
        assert "RuntimeError" in result.error_message

    def test_test_import_clears_existing_module(self, tmp_path: Path) -> None:
        """Test that existing modules are cleared before import."""
        validator = CircularImportValidator(source_path=tmp_path)

        # Add module to sys.modules
        test_module = "test_clear_module"
        sys.modules[test_module] = Mock()

        with patch("importlib.import_module") as mock_import:
            mock_import.return_value = None
            validator._test_import(test_module, tmp_path / f"{test_module}.py")

        # Verify module was cleared
        mock_import.assert_called_once_with(test_module)


class TestCircularImportValidatorLoggingAndProgress:
    """Test logging and progress callback functionality."""

    def test_log_verbose_enabled(self, tmp_path: Path, capsys) -> None:
        """Test logging when verbose is enabled."""
        validator = CircularImportValidator(source_path=tmp_path, verbose=True)
        validator._log("Test message")

        captured = capsys.readouterr()
        assert "Test message" in captured.out

    def test_log_verbose_disabled(self, tmp_path: Path, capsys) -> None:
        """Test logging when verbose is disabled."""
        validator = CircularImportValidator(source_path=tmp_path, verbose=False)
        validator._log("Test message")

        captured = capsys.readouterr()
        assert "Test message" not in captured.out

    def test_notify_progress_with_callback(self, tmp_path: Path) -> None:
        """Test progress notification with callback."""
        callback = Mock()
        validator = CircularImportValidator(
            source_path=tmp_path, progress_callback=callback
        )

        validator._notify_progress("Progress update")

        callback.assert_called_once_with("Progress update")

    def test_notify_progress_without_callback(self, tmp_path: Path) -> None:
        """Test progress notification without callback (should not error)."""
        validator = CircularImportValidator(
            source_path=tmp_path, progress_callback=None
        )

        # Should not raise
        validator._notify_progress("Progress update")


class TestCircularImportValidatorValidate:
    """Test validate method."""

    def test_validate_empty_directory(self, tmp_path: Path) -> None:
        """Test validation of empty directory."""
        validator = CircularImportValidator(source_path=tmp_path)
        result = validator.validate()

        assert isinstance(result, ModelValidationResult)
        assert result.total_files == 0
        assert result.success_count == 0
        assert result.failure_count == 0

    def test_validate_with_python_files(self, tmp_path: Path) -> None:
        """Test validation with Python files."""
        # Create test files
        (tmp_path / "module1.py").write_text("# Simple module")
        (tmp_path / "module2.py").write_text("# Another module")

        validator = CircularImportValidator(source_path=tmp_path)

        with patch.object(validator, "_test_import") as mock_test:
            mock_test.side_effect = [
                ModelModuleImportResult(
                    module_name="module1",
                    status=EnumImportStatus.SUCCESS,
                    file_path=str(tmp_path / "module1.py"),
                ),
                ModelModuleImportResult(
                    module_name="module2",
                    status=EnumImportStatus.SUCCESS,
                    file_path=str(tmp_path / "module2.py"),
                ),
            ]

            result = validator.validate()

        assert result.total_files == 2
        assert result.success_count == 2
        assert result.success_rate == 100.0

    def test_validate_with_circular_import(self, tmp_path: Path) -> None:
        """Test validation detecting circular import."""
        # Create test file
        (tmp_path / "circular.py").write_text("# Module with circular import")

        validator = CircularImportValidator(source_path=tmp_path)

        with patch.object(validator, "_test_import") as mock_test:
            mock_test.return_value = ModelModuleImportResult(
                module_name="circular",
                status=EnumImportStatus.CIRCULAR_IMPORT,
                error_message="circular import detected",
                file_path=str(tmp_path / "circular.py"),
            )

            result = validator.validate()

        assert result.has_circular_imports is True
        assert len(result.circular_imports) == 1

    def test_validate_with_skipped_files(self, tmp_path: Path) -> None:
        """Test validation with files that get skipped."""
        # Create __init__.py at root (should be skipped)
        (tmp_path / "__init__.py").write_text("# Root init")

        validator = CircularImportValidator(source_path=tmp_path)
        result = validator.validate()

        # Should have 1 file, but it gets skipped
        assert result.total_files == 1
        assert len(result.skipped) == 1
        assert result.skipped[0].status == EnumImportStatus.SKIPPED

    def test_validate_calls_progress_callback(self, tmp_path: Path) -> None:
        """Test that validate calls progress callback."""
        (tmp_path / "module1.py").write_text("# Module")

        callback = Mock()
        validator = CircularImportValidator(
            source_path=tmp_path, progress_callback=callback
        )

        with patch.object(validator, "_test_import") as mock_test:
            mock_test.return_value = ModelModuleImportResult(
                module_name="module1",
                status=EnumImportStatus.SUCCESS,
                file_path=str(tmp_path / "module1.py"),
            )

            validator.validate()

        # Callback should be called at least once
        assert callback.call_count > 0

    def test_validate_verbose_output(self, tmp_path: Path, capsys) -> None:
        """Test validate produces verbose output when enabled."""
        (tmp_path / "module1.py").write_text("# Module")

        validator = CircularImportValidator(source_path=tmp_path, verbose=True)

        with patch.object(validator, "_test_import") as mock_test:
            mock_test.return_value = ModelModuleImportResult(
                module_name="module1",
                status=EnumImportStatus.SUCCESS,
                file_path=str(tmp_path / "module1.py"),
            )

            validator.validate()

        captured = capsys.readouterr()
        assert "Found" in captured.out
        assert "Python files to test" in captured.out


class TestCircularImportValidatorValidateAndReport:
    """Test validate_and_report method."""

    def test_validate_and_report_no_circular_imports(
        self, tmp_path: Path, capsys
    ) -> None:
        """Test validate_and_report with no circular imports."""
        (tmp_path / "module1.py").write_text("# Clean module")

        validator = CircularImportValidator(source_path=tmp_path)

        with patch.object(validator, "_test_import") as mock_test:
            mock_test.return_value = ModelModuleImportResult(
                module_name="module1",
                status=EnumImportStatus.SUCCESS,
                file_path=str(tmp_path / "module1.py"),
            )

            exit_code = validator.validate_and_report()

        assert exit_code == 0

        captured = capsys.readouterr()
        assert "No circular imports detected" in captured.out
        assert "RESULTS" in captured.out

    def test_validate_and_report_with_circular_imports(
        self, tmp_path: Path, capsys
    ) -> None:
        """Test validate_and_report with circular imports detected."""
        (tmp_path / "circular.py").write_text("# Circular import")

        validator = CircularImportValidator(source_path=tmp_path)

        with patch.object(validator, "_test_import") as mock_test:
            mock_test.return_value = ModelModuleImportResult(
                module_name="circular",
                status=EnumImportStatus.CIRCULAR_IMPORT,
                error_message="circular import detected",
                file_path=str(tmp_path / "circular.py"),
            )

            exit_code = validator.validate_and_report()

        assert exit_code == 1

        captured = capsys.readouterr()
        assert "CIRCULAR IMPORT FAILURES" in captured.out
        assert "circular" in captured.out

    def test_validate_and_report_shows_summary(self, tmp_path: Path, capsys) -> None:
        """Test validate_and_report shows comprehensive summary."""
        # Create multiple test files
        (tmp_path / "success.py").write_text("# Success")
        (tmp_path / "error.py").write_text("# Error")

        validator = CircularImportValidator(source_path=tmp_path)

        with patch.object(validator, "_test_import") as mock_test:
            mock_test.side_effect = [
                ModelModuleImportResult(
                    module_name="success",
                    status=EnumImportStatus.SUCCESS,
                    file_path=str(tmp_path / "success.py"),
                ),
                ModelModuleImportResult(
                    module_name="error",
                    status=EnumImportStatus.IMPORT_ERROR,
                    error_message="Import failed",
                    file_path=str(tmp_path / "error.py"),
                ),
            ]

            validator.validate_and_report()

        captured = capsys.readouterr()
        assert "Total files:" in captured.out
        assert "Successful imports:" in captured.out
        assert "Success rate:" in captured.out


class TestCircularImportValidatorEdgeCases:
    """Test edge cases and error conditions."""

    def test_validate_with_mixed_results(self, tmp_path: Path) -> None:
        """Test validation with mixed success, errors, and circular imports."""
        # Create test files
        (tmp_path / "success.py").write_text("# Success")
        (tmp_path / "circular.py").write_text("# Circular")
        (tmp_path / "error.py").write_text("# Error")
        (tmp_path / "unexpected.py").write_text("# Unexpected")

        validator = CircularImportValidator(source_path=tmp_path)

        with patch.object(validator, "_test_import") as mock_test:
            mock_test.side_effect = [
                ModelModuleImportResult(
                    module_name="success",
                    status=EnumImportStatus.SUCCESS,
                    file_path=str(tmp_path / "success.py"),
                ),
                ModelModuleImportResult(
                    module_name="circular",
                    status=EnumImportStatus.CIRCULAR_IMPORT,
                    error_message="circular import",
                    file_path=str(tmp_path / "circular.py"),
                ),
                ModelModuleImportResult(
                    module_name="error",
                    status=EnumImportStatus.IMPORT_ERROR,
                    error_message="import error",
                    file_path=str(tmp_path / "error.py"),
                ),
                ModelModuleImportResult(
                    module_name="unexpected",
                    status=EnumImportStatus.UNEXPECTED_ERROR,
                    error_message="unexpected error",
                    file_path=str(tmp_path / "unexpected.py"),
                ),
            ]

            result = validator.validate()

        assert result.total_files == 4
        assert result.success_count == 1
        assert result.failure_count == 3

        summary = result.get_summary()
        assert summary["successful"] == 1
        assert summary["circular_imports"] == 1
        assert summary["import_errors"] == 1
        assert summary["unexpected_errors"] == 1

    def test_validate_with_empty_module_name(self, tmp_path: Path) -> None:
        """Test handling of files that convert to empty module names."""
        (tmp_path / "test.py").write_text("# Test")

        validator = CircularImportValidator(source_path=tmp_path)

        with patch.object(validator, "_path_to_module_name", return_value=None):
            result = validator.validate()

        # Should produce skipped result
        assert len(result.skipped) == 1
        assert result.skipped[0].status == EnumImportStatus.SKIPPED

    def test_multiple_include_patterns(self, tmp_path: Path) -> None:
        """Test with multiple include patterns."""
        (tmp_path / "module.py").write_text("# Python")
        (tmp_path / "cython.pyx").write_text("# Cython")

        validator = CircularImportValidator(
            source_path=tmp_path, include_patterns=["*.py", "*.pyx"]
        )

        files = validator._discover_python_files()
        # Should find both .py and .pyx files
        assert len(files) == 2
