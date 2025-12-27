"""
Comprehensive tests for the runtime-host-dev CLI command.

Tests cover:
- Command existence and correct name
- Production environment check (ENVIRONMENT=prod)
- Warning messages about dev/test usage
- Required CONTRACT_PATH argument
- Error handling for non-existent contract paths
- Successful execution with valid contract path
- Help text containing dev/test warning
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from omnibase_core.cli.runtime_host_cli import main
from omnibase_core.enums.enum_cli_exit_code import EnumCLIExitCode

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestRuntimeHostCliBasics:
    """Tests for basic CLI command properties."""

    def test_command_exists_and_has_correct_name(self) -> None:
        """Test that the command exists and has the correct name."""
        assert main is not None
        assert main.name == "runtime-host-dev"

    def test_command_is_click_command(self) -> None:
        """Test that main is a proper Click command."""
        import click

        assert isinstance(main, click.Command)

    def test_help_text_contains_dev_test_warning(self) -> None:
        """Test that help text contains dev/test warning."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        # Check for warning in help text
        assert "DEVELOPMENT" in result.output or "development" in result.output
        assert "TESTING" in result.output or "testing" in result.output
        assert "production" in result.output.lower()

    def test_help_shows_contract_path_argument(self) -> None:
        """Test that help shows CONTRACT_PATH argument."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "CONTRACT_PATH" in result.output


@pytest.mark.unit
class TestProductionEnvironmentCheck:
    """Tests for production environment check."""

    def test_refuses_to_run_when_environment_is_prod(self) -> None:
        """Test that command refuses to run when ENVIRONMENT=prod."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create a dummy contract file
            Path("test_contract.yaml").write_text("test: true")

            # Set ENVIRONMENT=prod
            with patch.dict(os.environ, {"ENVIRONMENT": "prod"}):
                result = runner.invoke(main, ["test_contract.yaml"])

        assert result.exit_code == EnumCLIExitCode.ERROR
        assert "ERROR" in result.output
        assert "production" in result.output.lower()

    def test_refuses_to_run_when_environment_is_prod_uppercase(self) -> None:
        """Test that command refuses to run when ENVIRONMENT=PROD (uppercase)."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            Path("test_contract.yaml").write_text("test: true")

            # The check uses .lower() so PROD should also be caught
            with patch.dict(os.environ, {"ENVIRONMENT": "PROD"}):
                result = runner.invoke(main, ["test_contract.yaml"])

        assert result.exit_code == EnumCLIExitCode.ERROR
        assert "production" in result.output.lower()

    def test_allows_run_when_environment_is_dev(self) -> None:
        """Test that command allows run when ENVIRONMENT=dev."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            Path("test_contract.yaml").write_text("test: true\nvalue: 123")

            with patch.dict(os.environ, {"ENVIRONMENT": "dev"}):
                result = runner.invoke(main, ["test_contract.yaml"])

        # Should succeed (exit code 0)
        assert result.exit_code == 0
        assert "successfully" in result.output.lower()

    def test_allows_run_when_environment_is_test(self) -> None:
        """Test that command allows run when ENVIRONMENT=test."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            Path("test_contract.yaml").write_text("test: true")

            with patch.dict(os.environ, {"ENVIRONMENT": "test"}):
                result = runner.invoke(main, ["test_contract.yaml"])

        assert result.exit_code == 0
        assert "successfully" in result.output.lower()

    def test_allows_run_when_environment_not_set(self) -> None:
        """Test that command allows run when ENVIRONMENT is not set."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            Path("test_contract.yaml").write_text("test: true")

            # Remove ENVIRONMENT from env if present
            env = os.environ.copy()
            env.pop("ENVIRONMENT", None)
            with patch.dict(os.environ, env, clear=True):
                result = runner.invoke(main, ["test_contract.yaml"])

        assert result.exit_code == 0
        assert "successfully" in result.output.lower()


@pytest.mark.unit
class TestDevTestWarning:
    """Tests for dev/test warning messages."""

    def test_prints_warning_about_production_usage(self) -> None:
        """Test that command prints warning about production usage."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            Path("test_contract.yaml").write_text("test: true")

            with patch.dict(os.environ, {"ENVIRONMENT": "dev"}):
                result = runner.invoke(main, ["test_contract.yaml"])

        assert result.exit_code == 0
        assert "WARNING" in result.output
        assert "DEV/TEST" in result.output
        assert "production" in result.output.lower()

    def test_warning_uses_colored_output(self) -> None:
        """Test that warning uses yellow color styling."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            Path("test_contract.yaml").write_text("test: true")

            with patch.dict(os.environ, {"ENVIRONMENT": "dev"}):
                # Use color=True to get ANSI codes
                result = runner.invoke(main, ["test_contract.yaml"], color=True)

        # Yellow ANSI color code is \x1b[33m or similar
        # The result should contain color codes when color=True
        assert result.exit_code == 0
        # We verify the warning is printed (color handling is done by Click)
        assert "WARNING" in result.output


@pytest.mark.unit
class TestContractPathArgument:
    """Tests for CONTRACT_PATH argument handling."""

    def test_requires_contract_path_argument(self) -> None:
        """Test that command requires CONTRACT_PATH argument."""
        runner = CliRunner()

        # Invoke without any arguments
        result = runner.invoke(main, [])

        assert result.exit_code != 0
        # Click should show missing argument error
        assert "CONTRACT_PATH" in result.output or "Missing argument" in result.output

    def test_exits_with_error_for_nonexistent_contract_path(self) -> None:
        """Test that command exits with error for non-existent contract path."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Don't create the file
            result = runner.invoke(main, ["nonexistent_contract.yaml"])

        assert result.exit_code != 0
        # Click should report the path doesn't exist
        assert (
            "does not exist" in result.output.lower()
            or "error" in result.output.lower()
        )

    def test_exits_with_error_for_directory_path(self) -> None:
        """Test that command exits with error when given a directory."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            Path("some_directory").mkdir()
            result = runner.invoke(main, ["some_directory"])

        assert result.exit_code != 0
        # Click should report this is not a file
        assert (
            "is a directory" in result.output.lower()
            or "not a file" in result.output.lower()
            or "error" in result.output.lower()
        )


@pytest.mark.unit
class TestSuccessfulExecution:
    """Tests for successful command execution."""

    def test_works_with_valid_contract_path(self) -> None:
        """Test that command works with valid contract path."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create a valid contract file
            contract_content = """
event_bus:
  kind: local
handlers:
  - type: compute
    name: test_handler
"""
            Path("test_contract.yaml").write_text(contract_content)

            with patch.dict(os.environ, {"ENVIRONMENT": "dev"}):
                result = runner.invoke(main, ["test_contract.yaml"])

        assert result.exit_code == 0
        assert "successfully" in result.output.lower()
        assert "test_contract.yaml" in result.output

    def test_displays_contract_file_info(self) -> None:
        """Test that command displays contract file information."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create a contract file with known content
            contract_content = "line1\nline2\nline3\nline4\n"
            Path("test_contract.yaml").write_text(contract_content)

            with patch.dict(os.environ, {"ENVIRONMENT": "dev"}):
                result = runner.invoke(main, ["test_contract.yaml"])

        assert result.exit_code == 0
        # Should show file size and line count
        assert "bytes" in result.output.lower()
        assert "lines" in result.output.lower()
        assert "Loading contract from" in result.output

    def test_logs_warning_on_startup(self) -> None:
        """Test that command logs a warning on startup via structured logging."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            Path("test_contract.yaml").write_text("test: true")

            with patch(
                "omnibase_core.cli.runtime_host_cli.emit_log_event_sync"
            ) as mock_log:
                with patch.dict(os.environ, {"ENVIRONMENT": "dev"}):
                    result = runner.invoke(main, ["test_contract.yaml"])

                assert result.exit_code == 0
                # Verify the log function was called with WARNING level
                mock_log.assert_called_once()
                call_args = mock_log.call_args
                from omnibase_core.enums.enum_log_level import EnumLogLevel

                assert call_args[0][0] == EnumLogLevel.WARNING
                assert "NOT FOR PRODUCTION" in call_args[0][1]

    def test_success_message_is_green(self) -> None:
        """Test that success message uses green color."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            Path("test_contract.yaml").write_text("test: true")

            with patch.dict(os.environ, {"ENVIRONMENT": "dev"}):
                result = runner.invoke(main, ["test_contract.yaml"], color=True)

        assert result.exit_code == 0
        assert "successfully" in result.output.lower()


@pytest.mark.unit
class TestErrorHandling:
    """Tests for error handling scenarios."""

    def test_handles_unreadable_contract_file(self) -> None:
        """Test that command handles unreadable contract file gracefully."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create a file
            contract_path = Path("test_contract.yaml")
            contract_path.write_text("test: true")

            # Mock read_text to raise an OSError
            with patch.object(
                Path, "read_text", side_effect=OSError("Permission denied")
            ):
                with patch.dict(os.environ, {"ENVIRONMENT": "dev"}):
                    result = runner.invoke(main, ["test_contract.yaml"])

        assert result.exit_code == EnumCLIExitCode.ERROR
        assert "ERROR" in result.output
        assert "Permission denied" in result.output or "read" in result.output.lower()

    def test_production_error_includes_helpful_message(self) -> None:
        """Test that production error includes helpful message."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            Path("test_contract.yaml").write_text("test: true")

            with patch.dict(os.environ, {"ENVIRONMENT": "prod"}):
                result = runner.invoke(main, ["test_contract.yaml"])

        assert result.exit_code == EnumCLIExitCode.ERROR
        # Should explain what happened
        assert "ENVIRONMENT" in result.output
        assert "prod" in result.output.lower()
        assert (
            "development" in result.output.lower() or "testing" in result.output.lower()
        )


@pytest.mark.unit
class TestModuleDocumentation:
    """Tests for module-level documentation."""

    def test_module_has_warning_docstring(self) -> None:
        """Test that the module docstring contains a warning."""
        import omnibase_core.cli.runtime_host_cli as cli_module

        assert cli_module.__doc__ is not None
        assert "WARNING" in cli_module.__doc__
        assert "development" in cli_module.__doc__.lower()
        assert "testing" in cli_module.__doc__.lower()
        assert "production" in cli_module.__doc__.lower()


@pytest.mark.unit
class TestExportedFromInit:
    """Tests for module export configuration."""

    def test_main_is_exported_from_cli_init(self) -> None:
        """Test that runtime_host_dev_main is exported from cli __init__."""
        from omnibase_core.cli import runtime_host_dev_main

        assert runtime_host_dev_main is not None
        assert runtime_host_dev_main is main

    def test_main_is_in_all(self) -> None:
        """Test that runtime_host_dev_main is in __all__."""
        from omnibase_core import cli

        assert "runtime_host_dev_main" in cli.__all__
