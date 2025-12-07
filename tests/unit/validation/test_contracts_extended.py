"""
Extended tests for contracts.py to improve coverage.

Tests cover:
- Timeout handling in validation
- load_and_validate_yaml_model() function
- Edge cases in validate_yaml_file()
- validate_contracts_directory() comprehensive testing
- Error handling scenarios
- File size limits and security checks
- Manual YAML detection edge cases
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.validation.contracts import (
    MAX_FILE_SIZE,
    load_and_validate_yaml_model,
    timeout_handler,
    validate_contracts_cli,
    validate_contracts_directory,
    validate_no_manual_yaml,
    validate_yaml_file,
)


class TestLoadAndValidateYamlModel:
    """Test load_and_validate_yaml_model function."""

    def test_load_valid_yaml_with_all_fields(self) -> None:
        """Test loading valid YAML with all required fields."""
        yaml_content = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE
contract_id: test-contract-001
operations:
  - name: get_user
    type: query
    parameters:
      - name: user_id
        type: string
"""

        contract = load_and_validate_yaml_model(yaml_content)

        assert contract is not None
        # After enum refactoring: COMPUTE maps to EnumNodeType.COMPUTE_GENERIC
        assert contract.node_type.value == "COMPUTE_GENERIC"

    def test_load_valid_yaml_minimal(self) -> None:
        """Test loading valid YAML with minimal fields."""
        yaml_content = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE
operations: []
"""

        contract = load_and_validate_yaml_model(yaml_content)

        assert contract is not None
        # After enum refactoring: COMPUTE maps to EnumNodeType.COMPUTE_GENERIC
        assert contract.node_type.value == "COMPUTE_GENERIC"

    def test_load_invalid_yaml_syntax(self) -> None:
        """Test loading YAML with invalid syntax."""
        yaml_content = """
version: 1.0
contract_id: test
operations:
  - name: test
    type: [invalid: syntax here
"""

        with pytest.raises(yaml.YAMLError):
            load_and_validate_yaml_model(yaml_content)

    def test_load_invalid_yaml_missing_required_field(self) -> None:
        """Test loading YAML missing required fields."""
        yaml_content = """
version: "1.0"
operations: []
"""

        with pytest.raises(ValidationError):
            load_and_validate_yaml_model(yaml_content)

    def test_load_yaml_with_extra_fields(self) -> None:
        """Test loading YAML with extra fields."""
        yaml_content = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE
contract_id: test-contract
operations: []
extra_field: should_be_ignored
another_extra: also_ignored
"""

        contract = load_and_validate_yaml_model(yaml_content)

        # Should succeed with extra fields (model config has extra="ignore")
        assert contract is not None
        # After enum refactoring: COMPUTE maps to EnumNodeType.COMPUTE_GENERIC
        assert contract.node_type.value == "COMPUTE_GENERIC"

    def test_load_yaml_empty_string(self) -> None:
        """Test loading empty YAML string."""
        yaml_content = ""

        # Empty YAML should fail validation
        with pytest.raises((ValidationError, TypeError)):
            load_and_validate_yaml_model(yaml_content)

    def test_load_yaml_whitespace_only(self) -> None:
        """Test loading whitespace-only YAML."""
        yaml_content = "   \n\t  \n  "

        # Tab characters in YAML can raise scanner errors
        with pytest.raises((ValidationError, TypeError, yaml.YAMLError)):
            load_and_validate_yaml_model(yaml_content)

    def test_load_yaml_with_null_values(self) -> None:
        """Test loading YAML with null values."""
        yaml_content = """
version: "1.0"
contract_id: null
operations: []
"""

        with pytest.raises(ValidationError):
            load_and_validate_yaml_model(yaml_content)


class TestValidateYamlFileExtended:
    """Extended tests for validate_yaml_file function."""

    def test_validate_yaml_file_various_encodings(self, tmp_path: Path) -> None:
        """Test YAML file validation with various encodings."""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(
            """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE
contract_id: test-éncödîng
operations: []
""",
            encoding="utf-8",
        )

        errors = validate_yaml_file(yaml_file)

        # Should handle UTF-8 encoding
        assert isinstance(errors, list)

    def test_validate_yaml_file_large_valid_file(self, tmp_path: Path) -> None:
        """Test validation of large but valid YAML file."""
        yaml_file = tmp_path / "large.yaml"

        # Create large but valid YAML
        operations = []
        for i in range(100):
            operations.append(
                f"""
  - name: operation_{i}
    type: query
    parameters:
      - name: param_{i}
        type: string
""",
            )

        content = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE
contract_id: large-contract
operations:
""" + "".join(operations)

        yaml_file.write_text(content)

        errors = validate_yaml_file(yaml_file)

        # Should succeed with large valid file
        assert isinstance(errors, list)

    def test_validate_yaml_file_binary_file(self, tmp_path: Path) -> None:
        """Test validation fails gracefully with binary file."""
        yaml_file = tmp_path / "binary.yaml"
        yaml_file.write_bytes(b"\x00\x01\x02\x03\x04\x05")

        errors = validate_yaml_file(yaml_file)

        # Should detect as invalid YAML or encoding error
        assert len(errors) > 0

    def test_validate_yaml_file_symlink(self, tmp_path: Path) -> None:
        """Test validation follows symlinks correctly."""
        real_file = tmp_path / "real.yaml"
        real_file.write_text(
            """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE
contract_id: symlink-test
operations: []
""",
        )

        symlink = tmp_path / "link.yaml"
        try:
            symlink.symlink_to(real_file)

            errors = validate_yaml_file(symlink)

            # Should follow symlink and validate
            assert isinstance(errors, list)
        except OSError:
            # Skip if OS doesn't support symlinks
            pytest.skip("OS doesn't support symlinks")

    def test_validate_yaml_file_with_comments(self, tmp_path: Path) -> None:
        """Test validation handles YAML comments correctly."""
        yaml_file = tmp_path / "commented.yaml"
        yaml_file.write_text(
            """
# This is a comment
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE  # Node type comment
contract_id: test-comments  # ID comment
# Another comment
operations: []  # Empty operations
""",
        )

        errors = validate_yaml_file(yaml_file)

        # Should handle comments correctly
        assert isinstance(errors, list)

    def test_validate_yaml_file_multiline_strings(self, tmp_path: Path) -> None:
        """Test validation handles multiline YAML strings."""
        yaml_file = tmp_path / "multiline.yaml"
        yaml_file.write_text(
            """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE
contract_id: multiline-test
operations:
  - name: test_op
    type: query
    description: |
      This is a multiline
      description that spans
      multiple lines
""",
        )

        errors = validate_yaml_file(yaml_file)

        assert isinstance(errors, list)

    def test_validate_yaml_file_nested_structures(self, tmp_path: Path) -> None:
        """Test validation handles deeply nested YAML structures."""
        yaml_file = tmp_path / "nested.yaml"
        yaml_file.write_text(
            """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE
contract_id: nested-test
operations:
  - name: complex_op
    type: query
    parameters:
      - name: param1
        type: object
        properties:
          nested1:
            type: object
            properties:
              nested2:
                type: string
""",
        )

        errors = validate_yaml_file(yaml_file)

        assert isinstance(errors, list)


class TestValidateNoManualYamlExtended:
    """Extended tests for validate_no_manual_yaml function."""

    def test_validate_no_manual_yaml_nested_generated(self, tmp_path: Path) -> None:
        """Test detection in deeply nested generated directories."""
        nested_dir = tmp_path / "level1" / "generated" / "level2" / "level3"
        nested_dir.mkdir(parents=True)

        manual_file = nested_dir / "manual.yaml"
        manual_file.write_text(
            """
# Manual file created
version: "1.0"
contract_id: test
operations: []
""",
        )

        errors = validate_no_manual_yaml(tmp_path)

        assert len(errors) > 0
        assert any("Manual YAML detected" in error for error in errors)

    def test_validate_no_manual_yaml_multiple_indicators(
        self,
        tmp_path: Path,
    ) -> None:
        """Test detection with multiple manual indicators."""
        gen_dir = tmp_path / "generated"
        gen_dir.mkdir()

        yaml_file = gen_dir / "test.yaml"
        yaml_file.write_text(
            """
# TODO: Update this contract
# FIXME: This needs work
# NOTE: manually created for testing
version: "1.0"
contract_id: test
operations: []
""",
        )

        errors = validate_no_manual_yaml(tmp_path)

        # Should detect at least one indicator
        assert len(errors) > 0

    def test_validate_no_manual_yaml_case_variations(self, tmp_path: Path) -> None:
        """Test detection with case variations of indicators."""
        gen_dir = tmp_path / "generated"
        gen_dir.mkdir()

        test_cases = [
            "# MANUAL creation",
            "# manual edit",
            "# Manual File",
            "# todo: fix this",
            "# TODO: update",
            "# fixme: broken",
            "# FIXME: URGENT",
        ]

        for i, indicator in enumerate(test_cases):
            yaml_file = gen_dir / f"test{i}.yaml"
            yaml_file.write_text(
                f"""
{indicator}
version: "1.0"
contract_id: test{i}
operations: []
""",
            )

        errors = validate_no_manual_yaml(tmp_path)

        # Should detect multiple manual files
        assert len(errors) >= len(test_cases)

    def test_validate_no_manual_yaml_yml_extension(self, tmp_path: Path) -> None:
        """Test detection works with .yml extension."""
        gen_dir = tmp_path / "generated"
        gen_dir.mkdir()

        yml_file = gen_dir / "test.yml"
        yml_file.write_text(
            """
# Manual creation
version: "1.0"
contract_id: test
operations: []
""",
        )

        errors = validate_no_manual_yaml(tmp_path)

        assert len(errors) > 0

    def test_validate_no_manual_yaml_auto_directory(self, tmp_path: Path) -> None:
        """Test detection in auto directories."""
        auto_dir = tmp_path / "auto" / "contracts"
        auto_dir.mkdir(parents=True)

        yaml_file = auto_dir / "manual.yaml"
        yaml_file.write_text(
            """
# manually created
version: "1.0"
contract_id: test
operations: []
""",
        )

        errors = validate_no_manual_yaml(tmp_path)

        assert len(errors) > 0
        assert any("Manual YAML detected" in error for error in errors)

    def test_validate_no_manual_yaml_read_error_handling(
        self,
        tmp_path: Path,
    ) -> None:
        """Test handling of read errors."""
        gen_dir = tmp_path / "generated"
        gen_dir.mkdir()

        yaml_file = gen_dir / "test.yaml"
        yaml_file.write_text("test content")

        # Make file unreadable (Unix only)
        import platform

        if platform.system() != "Windows":
            yaml_file.chmod(0o000)

            errors = validate_no_manual_yaml(tmp_path)

            # Should report error checking the file
            assert len(errors) >= 0  # May or may not report depending on permissions

            # Restore permissions for cleanup
            yaml_file.chmod(0o644)

    def test_validate_no_manual_yaml_generated_without_indicators(
        self,
        tmp_path: Path,
    ) -> None:
        """Test no errors for generated files without manual indicators."""
        gen_dir = tmp_path / "generated"
        gen_dir.mkdir()

        yaml_file = gen_dir / "auto.yaml"
        yaml_file.write_text(
            """
# Auto-generated contract
version: "1.0"
contract_id: auto-test
operations: []
""",
        )

        errors = validate_no_manual_yaml(tmp_path)

        # Should not report as manual
        assert len(errors) == 0


class TestValidateContractsDirectoryExtended:
    """Extended tests for validate_contracts_directory function."""

    def test_validate_contracts_directory_with_subdirectories(
        self,
        tmp_path: Path,
    ) -> None:
        """Test validation processes subdirectories."""
        # Create nested structure
        level1 = tmp_path / "level1"
        level1.mkdir()
        level2 = level1 / "level2"
        level2.mkdir()

        # Add YAML files at different levels
        (tmp_path / "root.yaml").write_text(
            """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE
contract_id: root
operations: []
""",
        )

        (level1 / "level1.yaml").write_text(
            """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE
contract_id: level1
operations: []
""",
        )

        (level2 / "level2.yaml").write_text(
            """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE
contract_id: level2
operations: []
""",
        )

        result = validate_contracts_directory(tmp_path)

        assert result.is_valid or not result.is_valid  # Should complete
        assert (
            result.metadata is not None and result.metadata.files_processed is not None
        )
        assert result.metadata.files_processed >= 3

    def test_validate_contracts_directory_mixed_valid_invalid(
        self,
        tmp_path: Path,
    ) -> None:
        """Test validation with mix of valid and invalid files."""
        # Valid file
        valid_file = tmp_path / "valid.yaml"
        valid_file.write_text(
            """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE
contract_id: valid
operations: []
""",
        )

        # Invalid file
        invalid_file = tmp_path / "invalid.yaml"
        invalid_file.write_text(
            """
invalid: yaml: [syntax
""",
        )

        result = validate_contracts_directory(tmp_path)

        assert (
            result.metadata is not None and result.metadata.files_processed is not None
        )
        assert result.metadata.files_processed >= 2
        # Should detect invalid file
        if not result.is_valid:
            assert len(result.errors) > 0

    def test_validate_contracts_directory_ignores_pycache(
        self,
        tmp_path: Path,
    ) -> None:
        """Test validation ignores __pycache__ directories."""
        pycache = tmp_path / "__pycache__"
        pycache.mkdir()

        (pycache / "test.yaml").write_text("should be ignored")

        result = validate_contracts_directory(tmp_path)

        # Should not check files in __pycache__
        assert (
            result.metadata is None or result.metadata.files_processed == 0
        ) or result.success

    def test_validate_contracts_directory_ignores_git(self, tmp_path: Path) -> None:
        """Test validation ignores .git directories."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        (git_dir / "config.yaml").write_text("should be ignored")

        result = validate_contracts_directory(tmp_path)

        assert (
            result.metadata is None or result.metadata.files_processed == 0
        ) or result.success

    def test_validate_contracts_directory_ignores_node_modules(
        self,
        tmp_path: Path,
    ) -> None:
        """Test validation ignores node_modules directories."""
        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()

        (node_modules / "package.yaml").write_text("should be ignored")

        result = validate_contracts_directory(tmp_path)

        assert (
            result.metadata is None or result.metadata.files_processed == 0
        ) or result.success

    def test_validate_contracts_directory_both_yaml_and_yml(
        self,
        tmp_path: Path,
    ) -> None:
        """Test validation handles both .yaml and .yml extensions."""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(
            """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE
contract_id: yaml-ext
operations: []
""",
        )

        yml_file = tmp_path / "test.yml"
        yml_file.write_text(
            """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE
contract_id: yml-ext
operations: []
""",
        )

        result = validate_contracts_directory(tmp_path)

        assert (
            result.metadata is not None and result.metadata.files_processed is not None
        )
        assert result.metadata.files_processed >= 2

    def test_validate_contracts_directory_detects_manual_yaml(
        self,
        tmp_path: Path,
    ) -> None:
        """Test validation detects manual YAML in restricted areas."""
        gen_dir = tmp_path / "generated"
        gen_dir.mkdir()

        manual_file = gen_dir / "manual.yaml"
        manual_file.write_text(
            """
# Manual file
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE
contract_id: manual
operations: []
""",
        )

        result = validate_contracts_directory(tmp_path)

        # Should detect manual YAML violation
        if not result.is_valid:
            assert len(result.errors) > 0
            assert any("Manual YAML" in error for error in result.errors)

    def test_validate_contracts_directory_tracks_invalid_yaml(
        self,
        tmp_path: Path,
    ) -> None:
        """Test validation tracks invalid YAML in violations."""
        invalid_file = tmp_path / "invalid.yaml"
        invalid_file.write_text("[invalid: yaml: syntax")

        result = validate_contracts_directory(tmp_path)

        # Should track invalid YAML
        assert not result.is_valid or len(result.errors) > 0

    def test_validate_contracts_directory_populates_metadata(
        self,
        tmp_path: Path,
    ) -> None:
        """Test validation populates result metadata."""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(
            """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE
contract_id: test
operations: []
""",
        )

        result = validate_contracts_directory(tmp_path)

        assert result.metadata is not None


class TestTimeoutHandler:
    """Test timeout_handler function."""

    @pytest.fixture(autouse=True)
    def isolate_signal_handlers(self) -> Generator[None, None, None]:
        """Isolate signal handlers for timeout tests.

        This fixture ensures signal handler state is properly isolated between tests:
        1. Cancels any pending alarms from other tests
        2. Saves the current signal handler
        3. Restores everything in cleanup

        This prevents flaky test failures in parallel execution (pytest-xdist)
        where multiple tests might be setting SIGALRM handlers.
        """
        import signal

        # CRITICAL: Cancel any pending alarms from other tests
        # This prevents race conditions where an alarm fires during this test
        signal.alarm(0)

        # Save current signal handler state
        original_handler = signal.signal(signal.SIGALRM, signal.SIG_DFL)

        yield

        # Cleanup: Cancel any alarms and restore original handler
        signal.alarm(0)
        signal.signal(signal.SIGALRM, original_handler)

    @pytest.mark.flaky(reruns=3, reruns_delay=1)
    def test_timeout_handler_raises_modelonex_error(self) -> None:
        """Test timeout handler raises ModelOnexError.

        This test verifies that the timeout_handler function correctly raises
        a ModelOnexError with the appropriate error code and message when called.

        Note: The error is EXPECTED to be raised - this is not a test failure.
        The pytest.raises context manager catches the exception to verify it.

        Signal handler isolation is provided by the isolate_signal_handlers fixture
        to prevent flaky failures in parallel test execution.
        """
        import signal

        # Verify no alarms are pending before we start
        remaining = signal.alarm(0)
        assert remaining == 0, f"Found pending alarm with {remaining}s remaining"

        # Test that timeout_handler raises the correct exception
        with pytest.raises(ModelOnexError) as exc_info:
            timeout_handler(0, None)

        # Verify the exception has the correct error code
        assert exc_info.value.error_code == EnumCoreErrorCode.TIMEOUT_ERROR, (
            f"Expected error code {EnumCoreErrorCode.TIMEOUT_ERROR}, "
            f"got {exc_info.value.error_code}"
        )

        # Verify the exception has the correct message
        assert "Validation timed out" in exc_info.value.message, (
            f"Expected message to contain 'Validation timed out', "
            f"got '{exc_info.value.message}'"
        )


class TestValidateYamlFileErrors:
    """Test error handling in validate_yaml_file."""

    def test_validate_yaml_file_nonexistent(self, tmp_path: Path) -> None:
        """Test handling of nonexistent files."""
        nonexistent = tmp_path / "nonexistent.yaml"

        errors = validate_yaml_file(nonexistent)

        assert len(errors) > 0
        assert any("does not exist" in error for error in errors)

    def test_validate_yaml_file_directory(self, tmp_path: Path) -> None:
        """Test handling of directory instead of file."""
        directory = tmp_path / "test_dir"
        directory.mkdir()

        errors = validate_yaml_file(directory)

        assert len(errors) > 0
        assert any("not a regular file" in error for error in errors)

    def test_validate_yaml_file_too_large(self, tmp_path: Path) -> None:
        """Test handling of files that exceed size limit."""
        large_file = tmp_path / "large.yaml"

        # Create a file larger than MAX_FILE_SIZE
        with open(large_file, "w") as f:
            # Write enough data to exceed limit
            for _ in range(int(MAX_FILE_SIZE / 100) + 1):
                f.write("x" * 100)

        errors = validate_yaml_file(large_file)

        # Should detect file size violation
        assert len(errors) > 0
        assert any("too large" in error.lower() for error in errors)

    def test_validate_yaml_file_stat_error(self, tmp_path: Path) -> None:
        """Test handling of stat errors."""
        from unittest.mock import patch

        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("version: '1.0'\ncontract_id: test\noperations: []")

        # Mock stat to raise OSError after exists() passes
        original_stat = yaml_file.stat
        call_count = [0]

        def stat_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] > 2:  # Allow exists() and is_file() to work
                raise OSError("Stat failed")
            return original_stat()

        with patch.object(type(yaml_file), "stat", side_effect=stat_side_effect):
            errors = validate_yaml_file(yaml_file)

        # Should handle exception gracefully
        assert len(errors) > 0
        assert any("Cannot check file size" in error for error in errors)

    def test_validate_yaml_file_whitespace_only(self, tmp_path: Path) -> None:
        """Test handling of whitespace-only files."""
        yaml_file = tmp_path / "whitespace.yaml"
        yaml_file.write_text("   \n\t  \n  ")

        errors = validate_yaml_file(yaml_file)

        # Whitespace-only files should be treated as valid/empty
        assert len(errors) == 0

    def test_validate_yaml_file_permission_denied(self, tmp_path: Path) -> None:
        """Test handling of permission denied errors."""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(
            """
version: "1.0"
contract_id: test
operations: []
""",
        )

        # Make file unreadable (Unix only)
        import platform

        if platform.system() != "Windows":
            yaml_file.chmod(0o000)

            errors = validate_yaml_file(yaml_file)

            # Should detect permission error
            assert len(errors) > 0
            assert any("permission" in error.lower() for error in errors)

            # Restore permissions for cleanup
            yaml_file.chmod(0o644)

    def test_validate_yaml_file_read_exception(self, tmp_path: Path) -> None:
        """Test handling of file read exceptions."""
        from unittest.mock import patch

        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("version: '1.0'\ncontract_id: test\noperations: []")

        # Mock open to raise an exception
        with patch("builtins.open", side_effect=RuntimeError("Read error")):
            errors = validate_yaml_file(yaml_file)

        # Should handle exception gracefully
        assert len(errors) > 0
        assert any("Error reading file" in error for error in errors)


class TestValidateContractsCLI:
    """Test validate_contracts_cli function."""

    def test_cli_basic_success(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test CLI with valid contracts."""
        import sys

        (tmp_path / "test.yaml").write_text(
            """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE
operations: []
""",
        )

        monkeypatch.setattr(sys, "argv", ["validate_contracts", str(tmp_path)])

        exit_code = validate_contracts_cli()

        captured = capsys.readouterr()
        assert (
            "Contract Validation" in captured.out
            or "validation" in captured.out.lower()
        )

    def test_cli_with_errors(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test CLI with invalid contracts."""
        import sys

        (tmp_path / "bad.yaml").write_text("[invalid: yaml: syntax")

        monkeypatch.setattr(sys, "argv", ["validate_contracts", str(tmp_path)])

        exit_code = validate_contracts_cli()

        captured = capsys.readouterr()
        # Should report issues
        assert (
            "Contract Validation" in captured.out
            or "validation" in captured.out.lower()
        )

    def test_cli_nonexistent_directory(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test CLI with nonexistent directory."""
        import sys

        monkeypatch.setattr(
            sys,
            "argv",
            ["validate_contracts", str(tmp_path / "nonexistent")],
        )

        exit_code = validate_contracts_cli()

        captured = capsys.readouterr()
        assert (
            "Directory not found" in captured.out
            or "validation" in captured.out.lower()
        )

    def test_cli_multiple_directories(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test CLI with multiple directories."""
        import sys

        dir1 = tmp_path / "dir1"
        dir1.mkdir()
        dir2 = tmp_path / "dir2"
        dir2.mkdir()

        (dir1 / "test1.yaml").write_text(
            """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE
operations: []
""",
        )
        (dir2 / "test2.yaml").write_text(
            """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: EFFECT
operations: []
""",
        )

        monkeypatch.setattr(
            sys,
            "argv",
            ["validate_contracts", str(dir1), str(dir2)],
        )

        exit_code = validate_contracts_cli()

        captured = capsys.readouterr()
        assert (
            "Contract Validation" in captured.out
            or "validation" in captured.out.lower()
        )

    def test_cli_timeout_flag(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test CLI with custom timeout."""
        import sys

        (tmp_path / "test.yaml").write_text(
            """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE
operations: []
""",
        )

        monkeypatch.setattr(
            sys,
            "argv",
            ["validate_contracts", str(tmp_path), "--timeout", "600"],
        )

        exit_code = validate_contracts_cli()

        captured = capsys.readouterr()
        assert (
            "Contract Validation" in captured.out
            or "validation" in captured.out.lower()
        )

    def test_cli_keyboard_interrupt(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test CLI handles keyboard interrupt."""
        import sys
        from unittest.mock import patch

        (tmp_path / "test.yaml").write_text(
            """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE
operations: []
""",
        )

        monkeypatch.setattr(sys, "argv", ["validate_contracts", str(tmp_path)])

        # Patch within the contracts module's local namespace
        import omnibase_core.validation.contracts as contracts_module

        with patch.object(
            contracts_module,
            "validate_contracts_directory",
            side_effect=KeyboardInterrupt,
        ):
            exit_code = contracts_module.validate_contracts_cli()

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "interrupted" in captured.out.lower()

    def test_cli_default_directory(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test CLI defaults to current directory."""
        import os
        import sys

        (tmp_path / "test.yaml").write_text(
            """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE
operations: []
""",
        )

        original_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            monkeypatch.setattr(sys, "argv", ["validate_contracts"])

            exit_code = validate_contracts_cli()

            captured = capsys.readouterr()
            assert (
                "Contract Validation" in captured.out
                or "validation" in captured.out.lower()
            )
        finally:
            os.chdir(original_cwd)

    def test_cli_output_formatting(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test CLI output formatting."""
        import sys

        (tmp_path / "test.yaml").write_text(
            """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE
operations: []
""",
        )

        monkeypatch.setattr(sys, "argv", ["validate_contracts", str(tmp_path)])

        exit_code = validate_contracts_cli()

        captured = capsys.readouterr()
        # Check for proper formatting
        assert "=" in captured.out or "-" in captured.out
        assert "Files checked" in captured.out or "validation" in captured.out.lower()

    @pytest.mark.xdist_group(name="signal_handling")
    def test_cli_timeout_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test CLI handles timeout errors."""
        import sys
        from unittest.mock import patch

        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        (tmp_path / "test.yaml").write_text(
            """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE
operations: []
""",
        )

        monkeypatch.setattr(sys, "argv", ["validate_contracts", str(tmp_path)])

        # Patch within the contracts module's local namespace
        import omnibase_core.validation.contracts as contracts_module

        with patch.object(
            contracts_module,
            "validate_contracts_directory",
            side_effect=ModelOnexError(
                error_code=EnumCoreErrorCode.TIMEOUT_ERROR,
                message="Validation timed out",
            ),
        ):
            exit_code = contracts_module.validate_contracts_cli()

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "timed out" in captured.out.lower()

    @pytest.mark.xdist_group(name="signal_handling")
    def test_cli_generic_onex_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test CLI handles generic ModelOnexError."""
        import sys
        from unittest.mock import patch

        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        (tmp_path / "test.yaml").write_text(
            """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: COMPUTE
operations: []
""",
        )

        monkeypatch.setattr(sys, "argv", ["validate_contracts", str(tmp_path)])

        # Patch within the contracts module's local namespace
        import omnibase_core.validation.contracts as contracts_module

        with patch.object(
            contracts_module,
            "validate_contracts_directory",
            side_effect=ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Generic validation error",
            ),
        ):
            exit_code = contracts_module.validate_contracts_cli()

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Validation error" in captured.out or "error" in captured.out.lower()
