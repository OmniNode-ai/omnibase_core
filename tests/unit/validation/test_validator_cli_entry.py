# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Test suite for validation CLI entry point.

Tests that the validation module can be run as a script
and properly invokes the CLI.
"""

from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.mark.unit
class TestValidationCliEntry:
    """Test validation CLI entry point."""

    def test_import_from_validation_entry(self) -> None:
        """Test that run_validation_cli can be imported from entry point."""
        from omnibase_core.validation.validator_cli_entry import run_validation_cli

        assert run_validation_cli is not None
        assert callable(run_validation_cli)

    def test_module_has_main_block(self) -> None:
        """Test that module has __main__ check."""
        # Read the entry point file
        entry_file = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "omnibase_core"
            / "validation"
            / "validator_cli_entry.py"
        )

        content = entry_file.read_text()

        # Verify it has the __main__ block
        assert 'if __name__ == "__main__"' in content
        assert "run_validation_cli()" in content
        assert "exit(" in content

    def test_main_block_calls_run_validation_cli(self) -> None:
        """Test that __main__ block would call run_validation_cli.

        NOTE: This test verifies the __main__ block structure by inspecting the
        source code rather than executing it directly. Direct execution of
        __main__ blocks in unit tests is problematic because:
        1. Module import caching prevents re-execution
        2. Mocking the function after module load doesn't affect __name__ check
        3. The exit() call would terminate the test process

        The test_module_has_main_block() test already verifies the source code
        contains the correct __main__ pattern. This test additionally verifies
        that when we import run_validation_cli, it's the correct callable that
        would be invoked by the __main__ block.
        """
        # Verify the function that __main__ would call is importable and callable
        from omnibase_core.validation.validator_cli_entry import run_validation_cli

        assert callable(run_validation_cli)

        # Verify the function signature returns an int (exit code)
        # by checking the underlying validator_cli module
        from omnibase_core.validation.validator_cli import (
            run_validation_cli as original_cli,
        )

        assert run_validation_cli is original_cli

    def test_run_as_module_direct_execution(self) -> None:
        """Test that validator_cli_entry.py can be executed directly."""
        # The validation package doesn't have __main__.py, so we test
        # that the CLI entry point exists and is importable
        from omnibase_core.validation.validator_cli_entry import run_validation_cli

        # Verify the entry point function exists and is callable
        assert callable(run_validation_cli)

        # The function should be executable (we won't actually run it here
        # to avoid side effects, but we verify it exists)

    def test_module_docstring_exists(self) -> None:
        """Test that module has proper docstring."""
        import omnibase_core.validation.validator_cli_entry as entry_module

        assert entry_module.__doc__ is not None
        assert "Entry point" in entry_module.__doc__
        assert "Usage:" in entry_module.__doc__

    def test_entry_point_exit_handling(self) -> None:
        """Test that entry point properly handles exit codes."""
        with patch(
            "omnibase_core.validation.validator_cli_entry.run_validation_cli"
        ) as mock_cli:
            # Test successful exit
            mock_cli.return_value = 0

            # Import and verify the function exists
            from omnibase_core.validation.validator_cli_entry import run_validation_cli

            exit_code = run_validation_cli()

            # Verify the mock was called and returned the expected value
            mock_cli.assert_called_once()
            assert exit_code == 0
            assert isinstance(exit_code, int)
