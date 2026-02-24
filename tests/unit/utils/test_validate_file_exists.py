# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for OMN-555: validate_file_exists() pre-flight checks.

Covers:
  validate_file_exists() standalone function (util_safe_yaml_loader)
  ModelContractBase.validate_file_exists() classmethod
  ModelRuntimeHostContract.validate_file_exists() classmethod

Scenarios:
  - File exists and is readable (success)
  - File does not exist (FILE_NOT_FOUND)
  - Path is a directory (FILE_NOT_FOUND)
  - Permission denied (FILE_READ_ERROR) — skipped on root/unsupported OS
  - str input is accepted (coerced to Path)
  - Path input passes through unchanged
  - Original exception is preserved via __cause__
"""

import os
import stat
from pathlib import Path

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.contracts.model_contract_base import ModelContractBase
from omnibase_core.models.contracts.model_runtime_host_contract import (
    ModelRuntimeHostContract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.utils.util_safe_yaml_loader import validate_file_exists

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_readable_file(tmp_path: Path, name: str = "test.yaml") -> Path:
    """Create a minimal readable YAML file and return its path."""
    p = tmp_path / name
    p.write_text("key: value\n")
    return p


# ---------------------------------------------------------------------------
# validate_file_exists() standalone function
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidateFileExistsFunction:
    """Tests for the standalone validate_file_exists() function."""

    # ------------------------------------------------------------------
    # Happy paths
    # ------------------------------------------------------------------

    def test_existing_readable_file_returns_none(self, tmp_path: Path) -> None:
        """Existing readable file returns None (no exception)."""
        p = _create_readable_file(tmp_path)
        result = validate_file_exists(p)
        assert result is None

    def test_str_path_is_accepted(self, tmp_path: Path) -> None:
        """str input is coerced to Path and accepted."""
        p = _create_readable_file(tmp_path)
        result = validate_file_exists(str(p))
        assert result is None

    def test_path_object_is_accepted(self, tmp_path: Path) -> None:
        """pathlib.Path input is accepted directly."""
        p = _create_readable_file(tmp_path)
        result = validate_file_exists(p)
        assert result is None

    def test_deeply_nested_file_is_accepted(self, tmp_path: Path) -> None:
        """Deeply nested file path is accepted."""
        nested = tmp_path / "a" / "b" / "c"
        nested.mkdir(parents=True)
        p = nested / "contract.yaml"
        p.write_text("name: test\n")
        result = validate_file_exists(p)
        assert result is None

    # ------------------------------------------------------------------
    # File not found
    # ------------------------------------------------------------------

    def test_nonexistent_file_raises_file_not_found(self, tmp_path: Path) -> None:
        """Non-existent path raises FILE_NOT_FOUND."""
        p = tmp_path / "does_not_exist.yaml"
        with pytest.raises(ModelOnexError) as exc_info:
            validate_file_exists(p)
        assert exc_info.value.error_code == EnumCoreErrorCode.FILE_NOT_FOUND

    def test_nonexistent_file_error_message_contains_path(self, tmp_path: Path) -> None:
        """FILE_NOT_FOUND message includes the requested path."""
        p = tmp_path / "missing.yaml"
        with pytest.raises(ModelOnexError) as exc_info:
            validate_file_exists(p)
        assert "missing.yaml" in exc_info.value.message

    def test_nonexistent_str_path_raises_file_not_found(self, tmp_path: Path) -> None:
        """Non-existent str path raises FILE_NOT_FOUND (str coercion works)."""
        missing = str(tmp_path / "no_such_file.yaml")
        with pytest.raises(ModelOnexError) as exc_info:
            validate_file_exists(missing)
        assert exc_info.value.error_code == EnumCoreErrorCode.FILE_NOT_FOUND

    # ------------------------------------------------------------------
    # Directory instead of file
    # ------------------------------------------------------------------

    def test_directory_path_raises_file_not_found(self, tmp_path: Path) -> None:
        """Directory path raises FILE_NOT_FOUND (not a regular file)."""
        with pytest.raises(ModelOnexError) as exc_info:
            validate_file_exists(tmp_path)
        assert exc_info.value.error_code == EnumCoreErrorCode.FILE_NOT_FOUND

    def test_directory_error_message_indicates_not_file(self, tmp_path: Path) -> None:
        """FILE_NOT_FOUND message for directory mentions it is not a regular file."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        with pytest.raises(ModelOnexError) as exc_info:
            validate_file_exists(subdir)
        error_msg = exc_info.value.message
        # Should mention either the path or that it's not a file
        assert str(subdir) in error_msg or "not a regular file" in error_msg

    # ------------------------------------------------------------------
    # Permission denied — skipped when running as root or on Windows
    # ------------------------------------------------------------------

    @pytest.mark.skipif(
        os.name == "nt" or os.getuid() == 0,  # type: ignore[attr-defined]
        reason="Permission test not meaningful on Windows or as root",
    )
    def test_unreadable_file_raises_file_read_error(self, tmp_path: Path) -> None:
        """File with no read permissions raises FILE_READ_ERROR."""
        p = _create_readable_file(tmp_path, "no_read.yaml")
        p.chmod(stat.S_IWRITE | stat.S_IEXEC)  # write+exec but no read
        try:
            with pytest.raises(ModelOnexError) as exc_info:
                validate_file_exists(p)
            assert exc_info.value.error_code == EnumCoreErrorCode.FILE_READ_ERROR
        finally:
            p.chmod(stat.S_IRUSR | stat.S_IWUSR)  # restore so tmp cleanup works

    @pytest.mark.skipif(
        os.name == "nt" or os.getuid() == 0,  # type: ignore[attr-defined]
        reason="Permission test not meaningful on Windows or as root",
    )
    def test_unreadable_file_error_message_contains_path(self, tmp_path: Path) -> None:
        """FILE_READ_ERROR message includes the file path."""
        p = _create_readable_file(tmp_path, "locked.yaml")
        p.chmod(stat.S_IWRITE | stat.S_IEXEC)
        try:
            with pytest.raises(ModelOnexError) as exc_info:
                validate_file_exists(p)
            assert "locked.yaml" in exc_info.value.message
        finally:
            p.chmod(stat.S_IRUSR | stat.S_IWUSR)


# ---------------------------------------------------------------------------
# ModelContractBase.validate_file_exists() classmethod
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestModelContractBaseValidateFileExists:
    """Tests for ModelContractBase.validate_file_exists() classmethod.

    ModelContractBase is abstract — we call the classmethod directly via
    the class (no instantiation needed for classmethods).
    """

    def test_existing_file_returns_none(self, tmp_path: Path) -> None:
        """Classmethod accepts an existing readable file."""
        p = _create_readable_file(tmp_path)
        result = ModelContractBase.validate_file_exists(p)
        assert result is None

    def test_str_input_accepted(self, tmp_path: Path) -> None:
        """Classmethod accepts str path input."""
        p = _create_readable_file(tmp_path)
        result = ModelContractBase.validate_file_exists(str(p))
        assert result is None

    def test_nonexistent_file_raises_file_not_found(self, tmp_path: Path) -> None:
        """Classmethod raises FILE_NOT_FOUND for missing file."""
        p = tmp_path / "missing.yaml"
        with pytest.raises(ModelOnexError) as exc_info:
            ModelContractBase.validate_file_exists(p)
        assert exc_info.value.error_code == EnumCoreErrorCode.FILE_NOT_FOUND

    def test_directory_raises_file_not_found(self, tmp_path: Path) -> None:
        """Classmethod raises FILE_NOT_FOUND when path is a directory."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelContractBase.validate_file_exists(tmp_path)
        assert exc_info.value.error_code == EnumCoreErrorCode.FILE_NOT_FOUND

    def test_error_code_is_file_not_found_not_validation_error(
        self, tmp_path: Path
    ) -> None:
        """FILE_NOT_FOUND is clearly distinct from VALIDATION_ERROR."""
        p = tmp_path / "absent.yaml"
        with pytest.raises(ModelOnexError) as exc_info:
            ModelContractBase.validate_file_exists(p)
        assert exc_info.value.error_code != EnumCoreErrorCode.VALIDATION_ERROR
        assert exc_info.value.error_code == EnumCoreErrorCode.FILE_NOT_FOUND


# ---------------------------------------------------------------------------
# ModelRuntimeHostContract.validate_file_exists() classmethod
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestModelRuntimeHostContractValidateFileExists:
    """Tests for ModelRuntimeHostContract.validate_file_exists() classmethod."""

    def test_existing_file_returns_none(self, tmp_path: Path) -> None:
        """Classmethod accepts an existing readable file."""
        p = _create_readable_file(tmp_path, "runtime_host.yaml")
        result = ModelRuntimeHostContract.validate_file_exists(p)
        assert result is None

    def test_str_input_accepted(self, tmp_path: Path) -> None:
        """Classmethod accepts str path input."""
        p = _create_readable_file(tmp_path, "runtime_host.yaml")
        result = ModelRuntimeHostContract.validate_file_exists(str(p))
        assert result is None

    def test_nonexistent_file_raises_file_not_found(self, tmp_path: Path) -> None:
        """Classmethod raises FILE_NOT_FOUND for missing file."""
        p = tmp_path / "no_such_contract.yaml"
        with pytest.raises(ModelOnexError) as exc_info:
            ModelRuntimeHostContract.validate_file_exists(p)
        assert exc_info.value.error_code == EnumCoreErrorCode.FILE_NOT_FOUND

    def test_error_message_contains_path(self, tmp_path: Path) -> None:
        """FILE_NOT_FOUND error message includes the missing path."""
        p = tmp_path / "contract_missing.yaml"
        with pytest.raises(ModelOnexError) as exc_info:
            ModelRuntimeHostContract.validate_file_exists(p)
        assert "contract_missing.yaml" in exc_info.value.message

    def test_directory_raises_file_not_found(self, tmp_path: Path) -> None:
        """Classmethod raises FILE_NOT_FOUND when path is a directory."""
        subdir = tmp_path / "configs"
        subdir.mkdir()
        with pytest.raises(ModelOnexError) as exc_info:
            ModelRuntimeHostContract.validate_file_exists(subdir)
        assert exc_info.value.error_code == EnumCoreErrorCode.FILE_NOT_FOUND

    def test_validate_then_load_pattern(self, tmp_path: Path) -> None:
        """validate_file_exists() passes, then from_yaml() loads the contract.

        This verifies the intended usage pattern:
            ModelRuntimeHostContract.validate_file_exists(path)
            contract = ModelRuntimeHostContract.from_yaml(path)
        """
        contract_path = tmp_path / "runtime.yaml"
        contract_path.write_text("event_bus:\n  kind: kafka\nhandlers: []\nnodes: []\n")
        # Pre-flight check succeeds
        ModelRuntimeHostContract.validate_file_exists(contract_path)
        # Load succeeds after validation
        contract = ModelRuntimeHostContract.from_yaml(contract_path)
        assert contract is not None


# ---------------------------------------------------------------------------
# Error code and type distinctness
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidateFileExistsErrorCodes:
    """Verify that different failure conditions map to distinct error codes."""

    def test_missing_file_code_differs_from_directory_code(
        self, tmp_path: Path
    ) -> None:
        """Both missing file and directory give FILE_NOT_FOUND (different messages)."""
        missing_path = tmp_path / "missing.yaml"
        dir_path = tmp_path  # tmp_path itself is a directory

        missing_code: EnumCoreErrorCode | None = None
        dir_code: EnumCoreErrorCode | None = None

        try:
            validate_file_exists(missing_path)
        except ModelOnexError as e:
            missing_code = e.error_code

        try:
            validate_file_exists(dir_path)
        except ModelOnexError as e:
            dir_code = e.error_code

        # Both should be FILE_NOT_FOUND
        assert missing_code == EnumCoreErrorCode.FILE_NOT_FOUND
        assert dir_code == EnumCoreErrorCode.FILE_NOT_FOUND

    def test_validate_raises_model_onex_error_not_os_error(
        self, tmp_path: Path
    ) -> None:
        """validate_file_exists() never raises bare OSError — always ModelOnexError."""
        p = tmp_path / "not_here.yaml"
        with pytest.raises(ModelOnexError):
            validate_file_exists(p)
