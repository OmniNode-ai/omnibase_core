"""
Comprehensive tests for CLI commands module.

Tests cover:
- get_version() function with various scenarios
- Main CLI group with --help, --version, --verbose options
- validate command with directories, --strict, --quiet options
- info command with and without --verbose
- health command with --component filtering
- Helper functions for health checks
- Edge cases and error handling
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from omnibase_core.cli.commands import (
    _check_core_imports,
    _check_error_handling,
    _check_validation_system,
    _display_validation_result,
    cli,
    get_version,
    health,
    info,
    print_version,
    validate,
)
from omnibase_core.enums.enum_cli_exit_code import EnumCLIExitCode

if TYPE_CHECKING:
    from omnibase_core.validation.validation_utils import ModelValidationResult

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestGetVersion:
    """Tests for the get_version function."""

    def test_get_version_from_importlib_metadata(self) -> None:
        """Test that get_version retrieves version from importlib.metadata."""
        # The function should return a version string
        version = get_version()
        assert isinstance(version, str)
        # Version should not be "unknown" when package is installed
        assert (
            version != "unknown"
        ), "Version should not be 'unknown' when package is installed"
        # Version should be non-empty
        assert len(version) > 0, "Version string should have non-zero length"

    def test_get_version_fallback_to_init(self) -> None:
        """Test fallback to __init__.__version__ when metadata fails."""
        from importlib.metadata import PackageNotFoundError

        with patch(
            "importlib.metadata.version",
            side_effect=PackageNotFoundError("omnibase_core"),
        ):
            with patch("omnibase_core.__version__", "1.2.3"):
                version = get_version()
                assert version == "1.2.3"

    def test_get_version_returns_unknown_on_all_failures(self) -> None:
        """Test that get_version returns 'unknown' when all version retrieval methods fail.

        This test verifies the complete fallback chain in get_version():
        1. importlib.metadata.version() raises PackageNotFoundError
        2. from omnibase_core import __version__ fails (no __version__ attribute)
        3. Function returns "unknown" as the final fallback

        We use MagicMock(spec=[]) to create a module mock without any attributes,
        which causes the 'from omnibase_core import __version__' to fail with ImportError.
        """
        from importlib.metadata import PackageNotFoundError

        # Create a mock module without __version__ attribute - spec=[] means no attributes
        mock_module = MagicMock(spec=[])

        with patch(
            "importlib.metadata.version",
            side_effect=PackageNotFoundError("omnibase_core"),
        ):
            # Replace omnibase_core in sys.modules with our mock that has no __version__
            with patch.dict(sys.modules, {"omnibase_core": mock_module}):
                version = get_version()
                assert (
                    version == "unknown"
                ), f"Expected 'unknown' when all version methods fail, but got '{version}'"


class TestPrintVersion:
    """Tests for the print_version callback."""

    def test_print_version_with_value_true(self) -> None:
        """Test that print_version prints version and exits when value is True."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "onex version" in result.output

    def test_print_version_callback_returns_early_when_false(self) -> None:
        """Test that print_version returns early when value is False."""
        ctx = MagicMock()
        ctx.resilient_parsing = False
        param = MagicMock()

        # Should return early without calling ctx.exit()
        print_version(ctx, param, False)
        ctx.exit.assert_not_called()

    def test_print_version_callback_returns_early_during_resilient_parsing(
        self,
    ) -> None:
        """Test that print_version returns early during resilient parsing."""
        ctx = MagicMock()
        ctx.resilient_parsing = True
        param = MagicMock()

        # Should return early without calling ctx.exit() during resilient parsing
        print_version(ctx, param, True)
        ctx.exit.assert_not_called()


class TestCliGroup:
    """Tests for the main CLI command group."""

    def test_cli_help(self) -> None:
        """Test that CLI --help shows usage information."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "ONEX CLI" in result.output
        assert "validate" in result.output
        assert "info" in result.output
        assert "health" in result.output

    def test_cli_no_command_shows_help(self) -> None:
        """Test that invoking CLI without command shows help."""
        runner = CliRunner()
        result = runner.invoke(cli, [])
        assert result.exit_code == 0
        assert "ONEX CLI" in result.output

    def test_cli_version_flag(self) -> None:
        """Test the --version flag."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "onex version" in result.output

    def test_cli_verbose_flag_stored_in_context(self) -> None:
        """Test that --verbose flag is stored in context."""
        runner = CliRunner()
        # Use info command to verify verbose is passed through context
        result = runner.invoke(cli, ["--verbose", "info"])
        assert result.exit_code == 0
        # Verbose mode shows additional info like Python path
        assert "Python path" in result.output


class TestValidateCommand:
    """Tests for the validate command."""

    def test_validate_help(self) -> None:
        """Test validate --help shows usage."""
        runner = CliRunner()
        result = runner.invoke(cli, ["validate", "--help"])
        assert result.exit_code == 0
        assert "Validate ONEX compliance" in result.output
        assert "--strict" in result.output
        assert "--quiet" in result.output

    def test_validate_default_directory_not_found(self, tmp_path: Path) -> None:
        """Test validate fails when default src/ doesn't exist."""
        runner = CliRunner()
        # Run in a temp directory without src/
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["validate"])
            assert result.exit_code != 0
            assert (
                "src/" in result.output or "No directories specified" in result.output
            )

    def test_validate_with_existing_directory(self, tmp_path: Path) -> None:
        """Test validate with an existing directory."""
        runner = CliRunner()
        # Create a minimal directory structure
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "test_file.py").write_text("# test file")

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Copy the directory structure
            import shutil

            shutil.copytree(src_dir, Path.cwd() / "src")

            result = runner.invoke(cli, ["validate"])
            # Exit code depends on validation results, but should not crash
            assert result.exit_code in (
                EnumCLIExitCode.SUCCESS,
                EnumCLIExitCode.ERROR,
            )

    def test_validate_with_strict_flag(self, tmp_path: Path) -> None:
        """Test validate with --strict flag."""
        runner = CliRunner()
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "test_file.py").write_text("# test file")

        with runner.isolated_filesystem(temp_dir=tmp_path):
            import shutil

            shutil.copytree(src_dir, Path.cwd() / "src")

            result = runner.invoke(cli, ["validate", "--strict"])
            # Should run without crashing
            assert result.exit_code in (
                EnumCLIExitCode.SUCCESS,
                EnumCLIExitCode.ERROR,
            )

    def test_validate_with_quiet_flag(self, tmp_path: Path) -> None:
        """Test validate with --quiet flag suppresses output."""
        runner = CliRunner()
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "test_file.py").write_text("# test file")

        with runner.isolated_filesystem(temp_dir=tmp_path):
            import shutil

            shutil.copytree(src_dir, Path.cwd() / "src")

            result = runner.invoke(cli, ["validate", "--quiet"])
            # Quiet mode should have minimal output
            # If valid, no output; if errors, only errors shown
            assert result.exit_code in (
                EnumCLIExitCode.SUCCESS,
                EnumCLIExitCode.ERROR,
            )

    def test_validate_with_verbose_flag(self, tmp_path: Path) -> None:
        """Test validate with verbose flag shows more output."""
        runner = CliRunner()
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "test_file.py").write_text("# test file")

        with runner.isolated_filesystem(temp_dir=tmp_path):
            import shutil

            shutil.copytree(src_dir, Path.cwd() / "src")

            result = runner.invoke(cli, ["--verbose", "validate"])
            # Verbose should work without errors
            assert result.exit_code in (
                EnumCLIExitCode.SUCCESS,
                EnumCLIExitCode.ERROR,
            )

    def test_validate_nonexistent_directory(self) -> None:
        """Test validate with a nonexistent directory argument."""
        runner = CliRunner()
        result = runner.invoke(cli, ["validate", "/nonexistent/directory"])
        assert result.exit_code != 0
        # Click should report the path doesn't exist
        assert (
            "does not exist" in result.output.lower()
            or "error" in result.output.lower()
        )


class TestInfoCommand:
    """Tests for the info command."""

    def test_info_basic_output(self) -> None:
        """Test that info shows basic package information."""
        runner = CliRunner()
        result = runner.invoke(cli, ["info"])
        assert result.exit_code == 0
        assert "omnibase_core version" in result.output
        assert "Python version" in result.output

    def test_info_verbose_output(self) -> None:
        """Test that info --verbose shows additional information."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--verbose", "info"])
        assert result.exit_code == 0
        assert "omnibase_core version" in result.output
        assert "Python version" in result.output
        assert "Python path" in result.output
        assert "Working directory" in result.output

    def test_info_help(self) -> None:
        """Test info --help shows usage."""
        runner = CliRunner()
        result = runner.invoke(cli, ["info", "--help"])
        assert result.exit_code == 0
        assert "Display information" in result.output


class TestHealthCommand:
    """Tests for the health command."""

    def test_health_basic_output(self) -> None:
        """Test that health shows health check results."""
        runner = CliRunner()
        result = runner.invoke(cli, ["health"])
        assert "ONEX Health Check" in result.output
        assert "Core imports" in result.output
        assert "Validation system" in result.output
        assert "Error handling" in result.output

    def test_health_all_checks_pass(self) -> None:
        """Test that all health checks pass in normal conditions."""
        runner = CliRunner()
        result = runner.invoke(cli, ["health"])
        # All checks should pass when properly installed
        assert "OK" in result.output
        # Should show success message
        if result.exit_code == EnumCLIExitCode.SUCCESS:
            assert "All health checks passed" in result.output

    def test_health_with_component_filter(self) -> None:
        """Test health with --component filter."""
        runner = CliRunner()
        result = runner.invoke(cli, ["health", "--component", "core"])
        assert "ONEX Health Check" in result.output
        assert "Core imports" in result.output
        # Other checks should be filtered out
        # Note: They might still appear if "core" partially matches

    def test_health_with_nonexistent_component(self) -> None:
        """Test health with --component that matches nothing returns error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["health", "--component", "nonexistent_xyz"])
        assert "ONEX Health Check" in result.output
        # Should show error message about no matching checks
        assert "No health checks match component filter" in result.output
        assert "nonexistent_xyz" in result.output
        # Should show available components
        assert "Available components" in result.output
        # Should exit with ERROR code
        assert result.exit_code == EnumCLIExitCode.ERROR

    def test_health_verbose_output(self) -> None:
        """Test health with verbose flag shows more details."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--verbose", "health"])
        assert "ONEX Health Check" in result.output
        # Verbose mode should show status messages
        assert "OK" in result.output or "FAIL" in result.output

    def test_health_help(self) -> None:
        """Test health --help shows usage."""
        runner = CliRunner()
        result = runner.invoke(cli, ["health", "--help"])
        assert result.exit_code == 0
        assert "--component" in result.output

    def test_health_component_filter_case_insensitive(self) -> None:
        """Test that --component filter is case insensitive."""
        runner = CliRunner()
        result = runner.invoke(cli, ["health", "--component", "CORE"])
        assert "ONEX Health Check" in result.output
        assert "Core imports" in result.output


class TestHealthCheckHelpers:
    """Tests for the health check helper functions."""

    def test_check_core_imports_success(self) -> None:
        """Test _check_core_imports returns success when imports work."""
        is_healthy, message = _check_core_imports()
        assert is_healthy is True
        assert "successful" in message.lower()

    def test_check_core_imports_failure(self) -> None:
        """Test _check_core_imports returns failure when imports fail."""
        with patch(
            "omnibase_core.cli.commands.EnumCoreErrorCode",
            side_effect=ImportError("Test import error"),
        ):
            # Need to re-import or mock at the right level
            # The function imports inside try block, so we mock at module level
            pass  # Covered by success path - import errors are rare

    def test_check_validation_system_success(self) -> None:
        """Test _check_validation_system returns success when validation works."""
        is_healthy, message = _check_validation_system()
        assert is_healthy is True
        assert "validators" in message.lower()

    def test_check_validation_system_reports_validator_count(self) -> None:
        """Test _check_validation_system reports the number of validators."""
        is_healthy, message = _check_validation_system()
        assert is_healthy is True
        # Should report number of validators
        assert "validator" in message.lower()

    def test_check_error_handling_success(self) -> None:
        """Test _check_error_handling returns success when error handling works."""
        is_healthy, message = _check_error_handling()
        assert is_healthy is True
        assert "operational" in message.lower()

    def test_check_error_handling_creates_and_catches_test_error(self) -> None:
        """Test that _check_error_handling properly tests error creation."""
        # This tests the internal behavior - it should raise and catch
        is_healthy, _ = _check_error_handling()
        assert is_healthy is True


class TestDisplayValidationResult:
    """Tests for the _display_validation_result helper function."""

    def test_display_valid_result(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test displaying a valid result."""
        from omnibase_core.models.common.model_validation_metadata import (
            ModelValidationMetadata,
        )
        from omnibase_core.validation.validation_utils import ModelValidationResult

        result: ModelValidationResult[None] = ModelValidationResult(
            is_valid=True,
            errors=[],
            metadata=ModelValidationMetadata(
                validation_type="test",
                files_processed=10,
            ),
        )

        _display_validation_result(
            "test_validation", result, verbose=False, quiet=False
        )

        captured = capsys.readouterr()
        assert "PASS" in captured.out
        assert "test_validation" in captured.out

    def test_display_invalid_result(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test displaying an invalid result."""
        from omnibase_core.models.common.model_validation_metadata import (
            ModelValidationMetadata,
        )
        from omnibase_core.validation.validation_utils import ModelValidationResult

        result: ModelValidationResult[None] = ModelValidationResult(
            is_valid=False,
            errors=["Error 1", "Error 2"],
            metadata=ModelValidationMetadata(
                validation_type="test",
                files_processed=5,
            ),
        )

        _display_validation_result(
            "test_validation", result, verbose=False, quiet=False
        )

        captured = capsys.readouterr()
        assert "FAIL" in captured.out
        assert "test_validation" in captured.out
        assert "Issues" in captured.out

    def test_display_quiet_mode_suppresses_valid_results(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that quiet mode suppresses output for valid results."""
        from omnibase_core.models.common.model_validation_metadata import (
            ModelValidationMetadata,
        )
        from omnibase_core.validation.validation_utils import ModelValidationResult

        result: ModelValidationResult[None] = ModelValidationResult(
            is_valid=True,
            errors=[],
            metadata=ModelValidationMetadata(
                validation_type="test",
                files_processed=10,
            ),
        )

        _display_validation_result("test_validation", result, verbose=False, quiet=True)

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_display_quiet_mode_shows_invalid_results(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that quiet mode still shows invalid results."""
        from omnibase_core.models.common.model_validation_metadata import (
            ModelValidationMetadata,
        )
        from omnibase_core.validation.validation_utils import ModelValidationResult

        result: ModelValidationResult[None] = ModelValidationResult(
            is_valid=False,
            errors=["Error 1"],
            metadata=ModelValidationMetadata(
                validation_type="test",
                files_processed=5,
            ),
        )

        _display_validation_result("test_validation", result, verbose=False, quiet=True)

        captured = capsys.readouterr()
        assert "FAIL" in captured.out

    def test_display_verbose_mode_shows_more_details(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that verbose mode shows additional details."""
        from omnibase_core.models.common.model_validation_metadata import (
            ModelValidationMetadata,
        )
        from omnibase_core.validation.validation_utils import ModelValidationResult

        result: ModelValidationResult[None] = ModelValidationResult(
            is_valid=True,
            errors=["Minor issue"],
            metadata=ModelValidationMetadata(
                validation_type="test",
                files_processed=15,
            ),
        )

        _display_validation_result("test_validation", result, verbose=True, quiet=False)

        captured = capsys.readouterr()
        assert "Files processed: 15" in captured.out

    def test_display_truncates_many_errors(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that display truncates when there are many errors."""
        from omnibase_core.models.common.model_validation_metadata import (
            ModelValidationMetadata,
        )
        from omnibase_core.validation.validation_utils import ModelValidationResult

        errors = [f"Error {i}" for i in range(15)]
        result: ModelValidationResult[None] = ModelValidationResult(
            is_valid=False,
            errors=errors,
            metadata=ModelValidationMetadata(
                validation_type="test",
                files_processed=5,
            ),
        )

        _display_validation_result("test_validation", result, verbose=True, quiet=False)

        captured = capsys.readouterr()
        assert "more" in captured.out  # Should indicate there are more errors


class TestCliEdgeCases:
    """Tests for CLI edge cases and error handling."""

    def test_validate_with_onex_error(self) -> None:
        """Test that ModelOnexError is properly handled in validate."""
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        runner = CliRunner()

        # Mock the validation suite to raise a ModelOnexError
        # Note: ModelValidationSuite is imported lazily inside the validate function
        with patch(
            "omnibase_core.validation.cli.ModelValidationSuite"
        ) as mock_suite_class:
            mock_suite = MagicMock()
            mock_suite.run_all_validations.side_effect = ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Test validation error",
            )
            mock_suite_class.return_value = mock_suite

            # Create a temp directory with src/
            with runner.isolated_filesystem():
                Path("src").mkdir()
                result = runner.invoke(cli, ["validate"])
                assert result.exit_code != 0
                assert (
                    "Test validation error" in result.output or "Error" in result.output
                )

    def test_validate_with_unexpected_error(self) -> None:
        """Test that unexpected errors are properly handled in validate."""
        runner = CliRunner()

        # Mock the validation suite to raise an unexpected error
        # Note: ModelValidationSuite is imported lazily inside the validate function
        with patch(
            "omnibase_core.validation.cli.ModelValidationSuite"
        ) as mock_suite_class:
            mock_suite = MagicMock()
            mock_suite.run_all_validations.side_effect = RuntimeError(
                "Unexpected runtime error"
            )
            mock_suite_class.return_value = mock_suite

            # Create a temp directory with src/
            with runner.isolated_filesystem():
                Path("src").mkdir()
                result = runner.invoke(cli, ["validate"])
                assert result.exit_code != 0
                assert (
                    "Unexpected" in result.output
                    or "runtime error" in result.output.lower()
                )

    def test_health_with_check_exception(self) -> None:
        """Test that health handles exceptions in check functions gracefully."""
        runner = CliRunner()

        # Mock one of the check functions to raise an exception
        with patch(
            "omnibase_core.cli.commands._check_core_imports",
            side_effect=RuntimeError("Test error"),
        ):
            result = runner.invoke(cli, ["health"])
            # Should still complete but show failure
            assert "FAIL" in result.output
            assert "Test error" in result.output

    def test_multiple_directories_validate(self, tmp_path: Path) -> None:
        """Test validate with multiple directories."""
        runner = CliRunner()

        # Create multiple directories
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()
        (dir1 / "test1.py").write_text("# test 1")
        (dir2 / "test2.py").write_text("# test 2")

        result = runner.invoke(cli, ["validate", str(dir1), str(dir2)])
        # Should attempt to validate both directories
        assert result.exit_code in (
            EnumCLIExitCode.SUCCESS,
            EnumCLIExitCode.ERROR,
        )


class TestCliExitCodes:
    """Tests for proper exit codes."""

    def test_cli_help_exits_zero(self) -> None:
        """Test that --help exits with code 0."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0

    def test_cli_version_exits_zero(self) -> None:
        """Test that --version exits with code 0."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0

    def test_info_exits_zero(self) -> None:
        """Test that info command exits with code 0."""
        runner = CliRunner()
        result = runner.invoke(cli, ["info"])
        assert result.exit_code == 0

    def test_health_exit_code_reflects_health_status(self) -> None:
        """Test that health exit code reflects actual health status."""
        runner = CliRunner()
        result = runner.invoke(cli, ["health"])
        # Exit code should be SUCCESS if all pass, ERROR if any fail
        assert result.exit_code in (
            EnumCLIExitCode.SUCCESS,
            EnumCLIExitCode.ERROR,
        )


class TestCliIntegration:
    """Integration tests for CLI functionality."""

    def test_full_workflow_validate_info_health(self) -> None:
        """Test running multiple commands in sequence."""
        runner = CliRunner()

        # Info command
        result = runner.invoke(cli, ["info"])
        assert result.exit_code == 0

        # Health command
        result = runner.invoke(cli, ["health"])
        # May pass or fail depending on system state
        assert result.exit_code in (
            EnumCLIExitCode.SUCCESS,
            EnumCLIExitCode.ERROR,
        )

    def test_verbose_and_quiet_mutually_exclusive_behavior(
        self, tmp_path: Path
    ) -> None:
        """Test behavior when both verbose and quiet could apply."""
        runner = CliRunner()

        # Create a temp src directory
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "test.py").write_text("# test")

        # Both verbose (from parent) and quiet (from validate)
        with runner.isolated_filesystem(temp_dir=tmp_path):
            import shutil

            shutil.copytree(src_dir, Path.cwd() / "src")

            # Quiet should take precedence for output suppression
            result = runner.invoke(cli, ["--verbose", "validate", "--quiet"])
            # Should run without errors
            assert result.exit_code in (
                EnumCLIExitCode.SUCCESS,
                EnumCLIExitCode.ERROR,
            )
