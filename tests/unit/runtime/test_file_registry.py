# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for FileRegistry (OMN-229).

TDD tests for FileRegistry class that loads YAML contract files.
These tests are written BEFORE the implementation exists.

Test Categories:
    - Basic Loading: Single file load with load() method
    - Directory Loading: Multiple files with load_all() method
    - File Not Found: Contract file does not exist
    - Invalid YAML: Malformed YAML syntax
    - Unknown Fields: YAML contains unknown fields (extra="forbid")
    - Unknown Handler Type: Invalid handler_type enum value
    - Missing Required Fields: Required fields not present
    - Schema Version Mismatch: Contract version incompatibility
    - Duplicate Handler Types: Same handler_type appears twice
    - Edge Cases: Empty directories, non-YAML files, nested directories

Error Messages:
    All errors must include:
    - File path (for debugging and error reporting)
    - Relevant context (field name, expected vs actual values, etc.)

Related:
    - src/omnibase_core/runtime/runtime_file_registry.py: Implementation target
    - src/omnibase_core/models/contracts/model_runtime_host_contract.py: Contract model
    - src/omnibase_core/models/errors/model_onex_error.py: Error class
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_handler_type import EnumHandlerType
from omnibase_core.models.contracts.model_runtime_host_contract import (
    ModelRuntimeHostContract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError

if TYPE_CHECKING:
    from omnibase_core.runtime.runtime_file_registry import FileRegistry


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def file_registry() -> FileRegistry:
    """
    Create a FileRegistry instance for testing.

    Returns:
        FileRegistry: New file registry instance.
    """
    from omnibase_core.runtime.runtime_file_registry import FileRegistry

    return FileRegistry()


@pytest.fixture
def valid_contract_yaml() -> str:
    """
    Provide valid YAML content for a RuntimeHostContract.

    Returns:
        str: Valid YAML content with all required fields.
    """
    return """
event_bus:
  kind: kafka

handlers:
  - handler_type: http
  - handler_type: database

nodes:
  - slug: node-compute-transformer
  - slug: node-effect-api-gateway
"""


@pytest.fixture
def valid_contract_minimal_yaml() -> str:
    """
    Provide minimal valid YAML content (only required fields).

    Returns:
        str: Valid YAML with only event_bus (required field).
    """
    return """
event_bus:
  kind: local
"""


@pytest.fixture
def invalid_yaml_syntax() -> str:
    """
    Provide YAML content with syntax errors.

    Returns:
        str: Invalid YAML content (malformed indentation, missing colon).
    """
    return """
event_bus:
  kind: kafka
handlers
  - handler_type: http
    invalid indentation here
"""


@pytest.fixture
def yaml_with_unknown_fields() -> str:
    """
    Provide YAML content with unknown fields.

    ModelRuntimeHostContract has extra="forbid", so unknown fields should error.

    Returns:
        str: YAML with unknown_field that should be rejected.
    """
    return """
event_bus:
  kind: kafka
unknown_field: this_should_fail
another_unknown: 12345
"""


@pytest.fixture
def yaml_with_unknown_handler_type() -> str:
    """
    Provide YAML content with invalid handler_type enum value.

    Returns:
        str: YAML with handler_type that doesn't exist in EnumHandlerType.
    """
    return """
event_bus:
  kind: kafka
handlers:
  - handler_type: invalid_handler_type_xyz
"""


@pytest.fixture
def yaml_missing_required_fields() -> str:
    """
    Provide YAML content missing required event_bus field.

    Returns:
        str: YAML missing the required event_bus field.
    """
    return """
handlers:
  - handler_type: http
nodes:
  - slug: test-node
"""


@pytest.fixture
def yaml_with_duplicate_handlers() -> str:
    """
    Provide YAML content with duplicate handler_type values.

    Returns:
        str: YAML with the same handler_type appearing twice.
    """
    return """
event_bus:
  kind: kafka
handlers:
  - handler_type: http
  - handler_type: database
  - handler_type: http
"""


@pytest.fixture
def yaml_with_nested_unknown_fields() -> str:
    """
    Provide YAML content with unknown fields in nested models.

    Returns:
        str: YAML with unknown fields in handler config.
    """
    return """
event_bus:
  kind: kafka
  unknown_event_bus_field: should_fail
handlers:
  - handler_type: http
    unknown_handler_field: should_fail
"""


@pytest.fixture
def yaml_empty_list() -> str:
    """
    Provide YAML content that parses to a list instead of dict.

    Returns:
        str: YAML that parses to a list.
    """
    return """
- item1
- item2
- item3
"""


@pytest.fixture
def yaml_scalar_value() -> str:
    """
    Provide YAML content that parses to a scalar value.

    Returns:
        str: YAML that parses to a string.
    """
    return "just a plain string"


# =============================================================================
# Basic Loading Tests
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestFileRegistryBasicLoading:
    """Test basic file loading functionality."""

    def test_load_valid_contract(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        valid_contract_yaml: str,
    ) -> None:
        """Test loading a valid YAML contract file."""
        # Arrange
        contract_file = tmp_path / "runtime_host.yaml"
        contract_file.write_text(valid_contract_yaml)

        # Act
        contract = file_registry.load(contract_file)

        # Assert
        assert isinstance(contract, ModelRuntimeHostContract)
        assert contract.event_bus.kind == "kafka"
        assert len(contract.handlers) == 2
        assert contract.handlers[0].handler_type == EnumHandlerType.HTTP
        assert contract.handlers[1].handler_type == EnumHandlerType.DATABASE
        assert len(contract.nodes) == 2
        assert contract.nodes[0].slug == "node-compute-transformer"
        assert contract.nodes[1].slug == "node-effect-api-gateway"

    def test_load_minimal_valid_contract(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        valid_contract_minimal_yaml: str,
    ) -> None:
        """Test loading a contract with only required fields."""
        # Arrange
        contract_file = tmp_path / "minimal.yaml"
        contract_file.write_text(valid_contract_minimal_yaml)

        # Act
        contract = file_registry.load(contract_file)

        # Assert
        assert isinstance(contract, ModelRuntimeHostContract)
        assert contract.event_bus.kind == "local"
        assert contract.handlers == []
        assert contract.nodes == []

    def test_load_returns_correct_type(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        valid_contract_yaml: str,
    ) -> None:
        """Test that load() returns ModelRuntimeHostContract type."""
        # Arrange
        contract_file = tmp_path / "contract.yaml"
        contract_file.write_text(valid_contract_yaml)

        # Act
        result = file_registry.load(contract_file)

        # Assert
        assert type(result) is ModelRuntimeHostContract

    def test_load_accepts_path_object(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        valid_contract_yaml: str,
    ) -> None:
        """Test that load() accepts pathlib.Path objects."""
        # Arrange
        contract_file = tmp_path / "contract.yaml"
        contract_file.write_text(valid_contract_yaml)

        # Act
        contract = file_registry.load(Path(contract_file))

        # Assert
        assert isinstance(contract, ModelRuntimeHostContract)


# =============================================================================
# Directory Loading Tests
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestFileRegistryDirectoryLoading:
    """Test loading multiple files from a directory."""

    def test_load_all_from_directory(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        valid_contract_yaml: str,
        valid_contract_minimal_yaml: str,
    ) -> None:
        """Test loading all YAML contracts from a directory."""
        # Arrange
        (tmp_path / "contract1.yaml").write_text(valid_contract_yaml)
        (tmp_path / "contract2.yaml").write_text(valid_contract_minimal_yaml)

        # Act
        contracts = file_registry.load_all(tmp_path)

        # Assert
        assert isinstance(contracts, list)
        assert len(contracts) == 2
        assert all(isinstance(c, ModelRuntimeHostContract) for c in contracts)

    def test_load_all_empty_directory(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
    ) -> None:
        """Test loading from empty directory returns empty list."""
        # Arrange - tmp_path is already empty

        # Act
        contracts = file_registry.load_all(tmp_path)

        # Assert
        assert contracts == []

    def test_load_all_ignores_non_yaml_files(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        valid_contract_yaml: str,
    ) -> None:
        """Test that load_all() ignores non-YAML files."""
        # Arrange
        (tmp_path / "contract.yaml").write_text(valid_contract_yaml)
        (tmp_path / "readme.txt").write_text("This is not a YAML file")
        (tmp_path / "config.json").write_text('{"key": "value"}')
        (tmp_path / "script.py").write_text("print('hello')")

        # Act
        contracts = file_registry.load_all(tmp_path)

        # Assert
        assert len(contracts) == 1
        assert isinstance(contracts[0], ModelRuntimeHostContract)

    def test_load_all_handles_yml_extension(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        valid_contract_yaml: str,
    ) -> None:
        """Test that load_all() handles both .yaml and .yml extensions."""
        # Arrange
        (tmp_path / "contract1.yaml").write_text(valid_contract_yaml)
        (tmp_path / "contract2.yml").write_text(valid_contract_yaml)

        # Act
        contracts = file_registry.load_all(tmp_path)

        # Assert
        assert len(contracts) == 2

    def test_load_all_does_not_recurse_into_subdirectories(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        valid_contract_yaml: str,
    ) -> None:
        """Test that load_all() does not recurse into nested directories."""
        # Arrange
        (tmp_path / "contract.yaml").write_text(valid_contract_yaml)
        subdir = tmp_path / "nested"
        subdir.mkdir()
        (subdir / "nested_contract.yaml").write_text(valid_contract_yaml)

        # Act
        contracts = file_registry.load_all(tmp_path)

        # Assert - only root level file should be loaded
        assert len(contracts) == 1

    def test_load_all_single_file(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        valid_contract_yaml: str,
    ) -> None:
        """Test loading from directory with single file."""
        # Arrange
        (tmp_path / "only_contract.yaml").write_text(valid_contract_yaml)

        # Act
        contracts = file_registry.load_all(tmp_path)

        # Assert
        assert len(contracts) == 1


# =============================================================================
# File Not Found Tests
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestFileRegistryFileNotFound:
    """Test file not found error handling."""

    def test_load_nonexistent_file_raises_error(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
    ) -> None:
        """Test that loading nonexistent file raises ModelOnexError."""
        # Arrange
        nonexistent = tmp_path / "does_not_exist.yaml"

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(nonexistent)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.FILE_NOT_FOUND

    def test_load_nonexistent_file_includes_path_in_error(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
    ) -> None:
        """Test that file not found error includes the file path in structured context."""
        # Arrange
        nonexistent = tmp_path / "missing_file.yaml"

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(nonexistent)

        error = exc_info.value
        # Verify error code
        assert error.error_code == EnumCoreErrorCode.FILE_NOT_FOUND
        # Verify file_path is in structured context
        context = error.context
        assert "file_path" in context
        assert str(nonexistent) in context.get("file_path", "")

    def test_load_all_nonexistent_directory_raises_error(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
    ) -> None:
        """Test that load_all() on nonexistent directory raises ModelOnexError."""
        # Arrange
        nonexistent_dir = tmp_path / "nonexistent_directory"

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load_all(nonexistent_dir)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.DIRECTORY_NOT_FOUND

    def test_load_all_nonexistent_directory_includes_path_in_error(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
    ) -> None:
        """Test that directory not found error includes path in structured context."""
        # Arrange
        nonexistent_dir = tmp_path / "missing_directory"

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load_all(nonexistent_dir)

        error = exc_info.value
        # Verify error code
        assert error.error_code == EnumCoreErrorCode.DIRECTORY_NOT_FOUND
        # Verify file_path is in structured context
        context = error.context
        assert "file_path" in context
        assert str(nonexistent_dir) in context.get("file_path", "")


# =============================================================================
# Invalid YAML Syntax Tests
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestFileRegistryInvalidYaml:
    """Test invalid YAML syntax and root type error handling.

    INTENTIONAL DESIGN: Contract files MUST have a YAML mapping (dict) at root.

    This validation is by design for three reasons:
    1. Pydantic model_validate() requires dict input for field mapping
    2. RuntimeHostContract has named fields (event_bus, handlers, nodes)
       which only make semantic sense as a YAML mapping, not list/scalar
    3. Fail-fast: reject invalid root types with clear errors rather than
       letting them cause cryptic failures in model_validate()

    See: ModelRuntimeHostContract.from_yaml() docstring for full documentation.
    """

    def test_load_invalid_yaml_raises_error(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        invalid_yaml_syntax: str,
    ) -> None:
        """Test that invalid YAML syntax raises ModelOnexError."""
        # Arrange
        bad_yaml_file = tmp_path / "bad_syntax.yaml"
        bad_yaml_file.write_text(invalid_yaml_syntax)

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(bad_yaml_file)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR

    def test_load_invalid_yaml_includes_file_path(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        invalid_yaml_syntax: str,
    ) -> None:
        """Test that YAML syntax error includes file path in structured context."""
        # Arrange
        bad_yaml_file = tmp_path / "syntax_error.yaml"
        bad_yaml_file.write_text(invalid_yaml_syntax)

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(bad_yaml_file)

        error = exc_info.value
        # Verify error code
        assert error.error_code == EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR
        # Verify file_path is in structured context
        context = error.context
        assert "file_path" in context
        assert str(bad_yaml_file) in context.get("file_path", "")

    def test_load_invalid_yaml_includes_line_info_if_available(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
    ) -> None:
        """Test that YAML syntax error includes line number if available."""
        # Arrange - YAML with clear syntax error on specific line
        bad_yaml = """
event_bus:
  kind: kafka
handlers:
  - handler_type: http
  invalid_indentation: should_error
"""
        bad_yaml_file = tmp_path / "line_error.yaml"
        bad_yaml_file.write_text(bad_yaml)

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(bad_yaml_file)

        error = exc_info.value
        # Verify error code is correct for YAML parse errors
        assert error.error_code == EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR

        # Verify file_path is in context
        context = error.context
        assert "file_path" in context
        assert str(bad_yaml_file) in context.get("file_path", "")

        # Verify line/column info is in context when available
        # YAML parse errors should include line_number and column_number
        assert "line_number" in context or "additional_context" in context
        if "additional_context" in context:
            additional = context["additional_context"]
            assert "line_number" in additional or "yaml_error" in additional
        else:
            # line_number should be an integer
            assert isinstance(context.get("line_number"), int)

    def test_load_empty_file(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
    ) -> None:
        """Test that empty YAML files are INTENTIONALLY rejected.

        INTENTIONAL BEHAVIOR: Empty files parse to None in YAML, which is not
        a valid dict. We explicitly reject these with VALIDATION_ERROR to
        fail-fast rather than letting None propagate to model_validate().
        """
        # Arrange
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("")

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(empty_file)

        # Empty YAML parses to None - intentionally rejected as invalid root type
        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_load_yaml_list_not_dict(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        yaml_empty_list: str,
    ) -> None:
        """Test that YAML lists at root are INTENTIONALLY rejected.

        INTENTIONAL BEHAVIOR: Contract files must have a mapping (dict) at root.
        Lists at root are semantically invalid for RuntimeHostContract which
        has named fields (event_bus, handlers, nodes). We reject with
        VALIDATION_ERROR to fail-fast with a clear message.
        """
        # Arrange
        list_yaml_file = tmp_path / "list_not_dict.yaml"
        list_yaml_file.write_text(yaml_empty_list)

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(list_yaml_file)

        # List at root - intentionally rejected as invalid root type
        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_load_yaml_scalar_not_dict(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        yaml_scalar_value: str,
    ) -> None:
        """Test that YAML scalars at root are INTENTIONALLY rejected.

        INTENTIONAL BEHAVIOR: Contract files must have a mapping (dict) at root.
        Scalars (strings, numbers, booleans) at root are semantically invalid
        for RuntimeHostContract which has named fields. We reject with
        VALIDATION_ERROR to fail-fast with a clear message.
        """
        # Arrange
        scalar_yaml_file = tmp_path / "scalar.yaml"
        scalar_yaml_file.write_text(yaml_scalar_value)

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(scalar_yaml_file)

        # Scalar at root - intentionally rejected as invalid root type
        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR


# =============================================================================
# Unknown Fields Tests
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestFileRegistryUnknownFields:
    """Test unknown fields error handling (extra="forbid")."""

    def test_load_yaml_with_unknown_fields_raises_error(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        yaml_with_unknown_fields: str,
    ) -> None:
        """Test that unknown fields in YAML raise ModelOnexError."""
        # Arrange
        unknown_fields_file = tmp_path / "unknown_fields.yaml"
        unknown_fields_file.write_text(yaml_with_unknown_fields)

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(unknown_fields_file)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR

    def test_load_yaml_with_unknown_fields_includes_file_path(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        yaml_with_unknown_fields: str,
    ) -> None:
        """Test that unknown fields error includes file path and validation_errors."""
        # Arrange
        unknown_fields_file = tmp_path / "extra_fields.yaml"
        unknown_fields_file.write_text(yaml_with_unknown_fields)

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(unknown_fields_file)

        error = exc_info.value
        # Verify error code
        assert error.error_code == EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR
        # Verify file_path is in structured context
        context = error.context
        assert "file_path" in context
        assert str(unknown_fields_file) in context.get("file_path", "")
        # Verify validation_errors is present (Pydantic validation details)
        assert "additional_context" in context
        additional = context["additional_context"]
        assert "validation_errors" in additional
        assert isinstance(additional["validation_errors"], list)

    def test_load_yaml_with_unknown_fields_includes_field_name(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        yaml_with_unknown_fields: str,
    ) -> None:
        """Test that unknown fields error includes the unknown field name."""
        # Arrange
        unknown_fields_file = tmp_path / "bad_field.yaml"
        unknown_fields_file.write_text(yaml_with_unknown_fields)

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(unknown_fields_file)

        error = exc_info.value
        error_str = str(error)
        # The error should mention one of the unknown fields
        assert "unknown_field" in error_str or "another_unknown" in error_str

    def test_load_yaml_with_nested_unknown_fields_raises_error(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        yaml_with_nested_unknown_fields: str,
    ) -> None:
        """Test that unknown fields in nested models also raise error."""
        # Arrange
        nested_unknown_file = tmp_path / "nested_unknown.yaml"
        nested_unknown_file.write_text(yaml_with_nested_unknown_fields)

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(nested_unknown_file)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR


# =============================================================================
# Unknown Handler Type Tests
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestFileRegistryUnknownHandlerType:
    """Test unknown handler type error handling."""

    def test_load_yaml_with_unknown_handler_type_raises_error(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        yaml_with_unknown_handler_type: str,
    ) -> None:
        """Test that unknown handler_type raises ModelOnexError."""
        # Arrange
        unknown_handler_file = tmp_path / "unknown_handler.yaml"
        unknown_handler_file.write_text(yaml_with_unknown_handler_type)

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(unknown_handler_file)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR

    def test_load_yaml_with_unknown_handler_type_includes_file_path(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        yaml_with_unknown_handler_type: str,
    ) -> None:
        """Test that unknown handler_type error includes file path and validation_errors."""
        # Arrange
        unknown_handler_file = tmp_path / "bad_handler.yaml"
        unknown_handler_file.write_text(yaml_with_unknown_handler_type)

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(unknown_handler_file)

        error = exc_info.value
        # Verify error code
        assert error.error_code == EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR
        # Verify file_path is in structured context
        context = error.context
        assert "file_path" in context
        assert str(unknown_handler_file) in context.get("file_path", "")
        # Verify validation_errors is present (Pydantic validation details)
        assert "additional_context" in context
        additional = context["additional_context"]
        assert "validation_errors" in additional
        assert isinstance(additional["validation_errors"], list)

    def test_load_yaml_with_unknown_handler_type_includes_invalid_type(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        yaml_with_unknown_handler_type: str,
    ) -> None:
        """Test that unknown handler_type error includes the invalid type value."""
        # Arrange
        unknown_handler_file = tmp_path / "invalid_type.yaml"
        unknown_handler_file.write_text(yaml_with_unknown_handler_type)

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(unknown_handler_file)

        error = exc_info.value
        error_str = str(error)
        # The error should mention the invalid handler type
        assert "invalid_handler_type_xyz" in error_str or "handler_type" in error_str


# =============================================================================
# Missing Required Fields Tests
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestFileRegistryMissingRequiredFields:
    """Test missing required fields error handling."""

    def test_load_yaml_missing_event_bus_raises_error(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        yaml_missing_required_fields: str,
    ) -> None:
        """Test that missing required event_bus field raises ModelOnexError."""
        # Arrange
        missing_field_file = tmp_path / "missing_event_bus.yaml"
        missing_field_file.write_text(yaml_missing_required_fields)

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(missing_field_file)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR

    def test_load_yaml_missing_event_bus_includes_file_path(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        yaml_missing_required_fields: str,
    ) -> None:
        """Test that missing field error includes file path and validation_errors."""
        # Arrange
        missing_field_file = tmp_path / "no_event_bus.yaml"
        missing_field_file.write_text(yaml_missing_required_fields)

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(missing_field_file)

        error = exc_info.value
        # Verify error code
        assert error.error_code == EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR
        # Verify file_path is in structured context
        context = error.context
        assert "file_path" in context
        assert str(missing_field_file) in context.get("file_path", "")
        # Verify validation_errors is present (Pydantic validation details)
        assert "additional_context" in context
        additional = context["additional_context"]
        assert "validation_errors" in additional
        assert isinstance(additional["validation_errors"], list)

    def test_load_yaml_missing_event_bus_includes_field_name(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        yaml_missing_required_fields: str,
    ) -> None:
        """Test that missing field error includes the field name."""
        # Arrange
        missing_field_file = tmp_path / "missing_field.yaml"
        missing_field_file.write_text(yaml_missing_required_fields)

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(missing_field_file)

        error = exc_info.value
        # Error should mention event_bus as the missing field
        assert "event_bus" in str(error)

    def test_load_yaml_missing_nested_required_field(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
    ) -> None:
        """Test that missing nested required field raises error."""
        # Arrange - event_bus present but missing required 'kind' field
        yaml_content = """
event_bus: {}
"""
        missing_nested_file = tmp_path / "missing_nested.yaml"
        missing_nested_file.write_text(yaml_content)

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(missing_nested_file)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR

    def test_load_yaml_missing_handler_type_in_handler(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
    ) -> None:
        """Test that missing handler_type in handler config raises error."""
        # Arrange
        yaml_content = """
event_bus:
  kind: kafka
handlers:
  - {}
"""
        missing_handler_type_file = tmp_path / "missing_handler_type.yaml"
        missing_handler_type_file.write_text(yaml_content)

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(missing_handler_type_file)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR


# =============================================================================
# Schema Version Mismatch Tests (Future Proofing)
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestFileRegistrySchemaVersionMismatch:
    """Test schema version validation (if implemented)."""

    def test_load_yaml_with_incompatible_schema_version(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
    ) -> None:
        """
        Test that incompatible schema version raises appropriate error.

        Note: This test assumes FileRegistry supports schema versioning.
        If not implemented yet, this test documents the expected behavior.
        """
        # Arrange - contract with a schema_version field
        yaml_content = """
schema_version: "99.0.0"
event_bus:
  kind: kafka
"""
        versioned_file = tmp_path / "versioned.yaml"
        versioned_file.write_text(yaml_content)

        # Act & Assert
        # If schema_version is not a valid field, should fail with unknown field error
        # If schema_version IS valid and checked, should fail with version mismatch
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(versioned_file)

        error = exc_info.value
        # schema_version is an unknown field (extra="forbid"), so CONTRACT_VALIDATION_ERROR
        assert error.error_code == EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR
        # File path should be in error
        assert str(versioned_file) in str(error) or "versioned.yaml" in str(error)


# =============================================================================
# Duplicate Handler Types Tests
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestFileRegistryDuplicateHandlers:
    """Test duplicate handler type validation."""

    def test_load_yaml_with_duplicate_handler_types_raises_error(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        yaml_with_duplicate_handlers: str,
    ) -> None:
        """
        Test that duplicate handler_type values raise ModelOnexError.

        Note: This validation may be handled by FileRegistry or by a separate
        validator. If not implemented yet, this test documents the requirement.
        """
        # Arrange
        duplicate_file = tmp_path / "duplicate_handlers.yaml"
        duplicate_file.write_text(yaml_with_duplicate_handlers)

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(duplicate_file)

        error = exc_info.value
        # Should be DUPLICATE_REGISTRATION for duplicate handlers
        assert error.error_code == EnumCoreErrorCode.DUPLICATE_REGISTRATION

    def test_load_yaml_with_duplicate_handler_types_includes_file_path(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        yaml_with_duplicate_handlers: str,
    ) -> None:
        """Test that duplicate handler error includes file path in structured context."""
        # Arrange
        duplicate_file = tmp_path / "dup_handlers.yaml"
        duplicate_file.write_text(yaml_with_duplicate_handlers)

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(duplicate_file)

        error = exc_info.value
        # Verify error code
        assert error.error_code == EnumCoreErrorCode.DUPLICATE_REGISTRATION
        # Verify file_path is in structured context
        context = error.context
        assert "file_path" in context
        assert str(duplicate_file) in context.get("file_path", "")
        # Verify duplicate_handler_type is in context
        assert "additional_context" in context
        additional = context["additional_context"]
        assert "duplicate_handler_type" in additional
        assert additional["duplicate_handler_type"] == "http"

    def test_load_yaml_with_duplicate_handler_types_includes_duplicate_type(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        yaml_with_duplicate_handlers: str,
    ) -> None:
        """Test that duplicate handler error includes the duplicate type."""
        # Arrange
        duplicate_file = tmp_path / "duplicate.yaml"
        duplicate_file.write_text(yaml_with_duplicate_handlers)

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(duplicate_file)

        error = exc_info.value
        error_str = str(error)
        # Error should mention http as the duplicate type
        assert "http" in error_str.lower() or "duplicate" in error_str.lower()


# =============================================================================
# Edge Cases and Error Context Tests
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestFileRegistryEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_load_handles_unicode_content(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
    ) -> None:
        """Test that unicode content in YAML is handled correctly."""
        # Arrange
        yaml_content = """
event_bus:
  kind: kafka
nodes:
  - slug: node-with-unicode-\u4e2d\u6587
"""
        unicode_file = tmp_path / "unicode.yaml"
        unicode_file.write_text(yaml_content, encoding="utf-8")

        # Act
        contract = file_registry.load(unicode_file)

        # Assert
        assert isinstance(contract, ModelRuntimeHostContract)

    def test_load_handles_multiline_strings_with_trailing_newline(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
    ) -> None:
        """Test that YAML block scalars with trailing newlines are handled.

        YAML block scalars (with |) include a trailing newline. This test
        verifies that multiline strings load successfully with the trailing
        newline preserved in the slug value.
        """
        # Arrange - YAML block scalar includes trailing newline
        yaml_content = """
event_bus:
  kind: kafka
nodes:
  - slug: |
      node-multiline-slug
"""
        multiline_file = tmp_path / "multiline.yaml"
        multiline_file.write_text(yaml_content)

        # Act - Load the file
        contract = file_registry.load(multiline_file)

        # Assert - Should load successfully with trailing newline preserved
        assert isinstance(contract, ModelRuntimeHostContract)
        assert len(contract.nodes) == 1
        # YAML block scalar (|) preserves the trailing newline
        assert contract.nodes[0].slug == "node-multiline-slug\n"

    def test_load_all_uses_fail_fast_behavior(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        valid_contract_yaml: str,
        invalid_yaml_syntax: str,
    ) -> None:
        """Test that load_all() uses fail-fast behavior and stops on first error.

        FileRegistry uses fail-fast semantics: when loading multiple files,
        it stops immediately upon encountering the first error rather than
        collecting all errors. This is the documented contract.
        """
        # Arrange - files are sorted alphabetically, so "a_valid" comes first,
        # then "b_invalid", then "c_valid". The error should be for "b_invalid".
        (tmp_path / "a_valid.yaml").write_text(valid_contract_yaml)
        (tmp_path / "b_invalid.yaml").write_text(invalid_yaml_syntax)
        (tmp_path / "c_valid.yaml").write_text(valid_contract_yaml)

        # Act & Assert - fail-fast means we stop at first error
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load_all(tmp_path)

        error = exc_info.value
        # Verify the error is for the invalid file specifically
        assert error.error_code == EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR
        context = error.context
        assert "file_path" in context
        # The error should reference b_invalid.yaml (the first error encountered)
        assert "b_invalid.yaml" in context.get("file_path", "")
        # Should NOT reference c_valid.yaml (fail-fast means we never processed it)
        assert "c_valid.yaml" not in str(error)

    def test_load_very_large_contract_with_duplicates_fails(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
    ) -> None:
        """Test that loading a contract with duplicate handlers raises DUPLICATE_REGISTRATION.

        FileRegistry enforces unique handler types per contract. This test verifies
        that duplicate handler types (http repeated 5 times) are rejected with the
        correct error code and context.
        """
        # Arrange - create a contract with duplicate handler_type entries
        handlers = "\n".join(
            ["  - handler_type: http" for _ in range(5)]
            + ["  - handler_type: database" for _ in range(5)]
        )
        nodes = "\n".join([f"  - slug: node-{i}" for i in range(100)])

        yaml_content = f"""
event_bus:
  kind: kafka
handlers:
{handlers}
nodes:
{nodes}
"""
        large_file = tmp_path / "large.yaml"
        large_file.write_text(yaml_content)

        # Act & Assert - should fail with DUPLICATE_REGISTRATION for duplicate http
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(large_file)

        error = exc_info.value
        # Verify correct error code for duplicate handlers
        assert error.error_code == EnumCoreErrorCode.DUPLICATE_REGISTRATION
        # Verify file_path is in context
        context = error.context
        assert "file_path" in context
        assert str(large_file) in context.get("file_path", "")
        # Verify the duplicate handler type is mentioned
        assert "http" in str(error).lower()

    def test_load_large_contract_with_unique_handlers_succeeds(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
    ) -> None:
        """Test that loading a large valid contract with unique handlers succeeds."""
        # Arrange - create a large but valid contract with unique handler types
        nodes = "\n".join([f"  - slug: node-{i}" for i in range(100)])

        yaml_content = f"""
event_bus:
  kind: kafka
handlers:
  - handler_type: http
  - handler_type: database
  - handler_type: kafka
nodes:
{nodes}
"""
        large_file = tmp_path / "large_valid.yaml"
        large_file.write_text(yaml_content)

        # Act
        contract = file_registry.load(large_file)

        # Assert - should load successfully
        assert isinstance(contract, ModelRuntimeHostContract)
        assert len(contract.nodes) == 100
        assert len(contract.handlers) == 3

    def test_load_file_with_only_comments(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
    ) -> None:
        """Test loading a file that only contains comments."""
        # Arrange
        yaml_content = """
# This is a comment
# Another comment
# No actual content
"""
        comment_file = tmp_path / "comments.yaml"
        comment_file.write_text(yaml_content)

        # Act & Assert
        with pytest.raises(ModelOnexError):
            file_registry.load(comment_file)

    def test_load_preserves_handler_order(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
    ) -> None:
        """Test that handler order is preserved from YAML."""
        # Arrange
        yaml_content = """
event_bus:
  kind: kafka
handlers:
  - handler_type: kafka
  - handler_type: http
  - handler_type: database
"""
        ordered_file = tmp_path / "ordered.yaml"
        ordered_file.write_text(yaml_content)

        # Act
        contract = file_registry.load(ordered_file)

        # Assert - order should be preserved
        assert len(contract.handlers) == 3
        assert contract.handlers[0].handler_type == EnumHandlerType.KAFKA
        assert contract.handlers[1].handler_type == EnumHandlerType.HTTP
        assert contract.handlers[2].handler_type == EnumHandlerType.DATABASE

    def test_load_preserves_node_order(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
    ) -> None:
        """Test that node order is preserved from YAML."""
        # Arrange
        yaml_content = """
event_bus:
  kind: kafka
nodes:
  - slug: third-node
  - slug: first-node
  - slug: second-node
"""
        ordered_file = tmp_path / "ordered_nodes.yaml"
        ordered_file.write_text(yaml_content)

        # Act
        contract = file_registry.load(ordered_file)

        # Assert - order should be preserved
        assert len(contract.nodes) == 3
        assert contract.nodes[0].slug == "third-node"
        assert contract.nodes[1].slug == "first-node"
        assert contract.nodes[2].slug == "second-node"


# =============================================================================
# Error Context Validation Tests
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestFileRegistryErrorContext:
    """Test that errors contain proper context information."""

    def test_error_context_includes_file_path_in_context_dict(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
    ) -> None:
        """Test that ModelOnexError context includes file_path."""
        # Arrange
        nonexistent = tmp_path / "context_test.yaml"

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(nonexistent)

        error = exc_info.value
        # Check if file_path is in the context
        context = error.context
        # file_path may be in context dict or in the message
        has_path = (
            "file_path" in context
            or str(nonexistent) in str(error)
            or "context_test.yaml" in str(error)
        )
        assert has_path

    def test_all_error_codes_are_onex_error_codes(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
    ) -> None:
        """Test that all raised errors use EnumCoreErrorCode."""
        # Arrange
        nonexistent = tmp_path / "code_test.yaml"

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(nonexistent)

        error = exc_info.value
        # error_code should be an EnumCoreErrorCode instance
        assert isinstance(error.error_code, EnumCoreErrorCode)

    def test_errors_are_modelonexerror_not_generic_exception(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
    ) -> None:
        """Test that errors are ModelOnexError, not generic Exception."""
        # Arrange - create file with invalid content
        invalid_file = tmp_path / "not_generic.yaml"
        invalid_file.write_text("invalid: {{{}")

        # Act & Assert - should raise ModelOnexError specifically
        try:
            file_registry.load(invalid_file)
            pytest.fail("Expected ModelOnexError to be raised")
        except ModelOnexError:
            pass  # Expected
        except Exception as e:
            pytest.fail(f"Expected ModelOnexError but got {type(e).__name__}: {e}")


# =============================================================================
# All Valid Handler Types Test
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestFileRegistryAllHandlerTypes:
    """Test that all valid EnumHandlerType values are accepted."""

    @pytest.mark.parametrize(
        "handler_type",
        [
            "http",
            "database",
            "kafka",
            "filesystem",
            "vault",
            "vector_store",
            "graph_database",
            "redis",
            "event_bus",
            "extension",
            "special",
            "named",
        ],
    )
    def test_load_accepts_all_valid_handler_types(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        handler_type: str,
    ) -> None:
        """Test that all valid handler types are accepted."""
        # Arrange
        yaml_content = f"""
event_bus:
  kind: kafka
handlers:
  - handler_type: {handler_type}
"""
        handler_file = tmp_path / f"handler_{handler_type}.yaml"
        handler_file.write_text(yaml_content)

        # Act
        contract = file_registry.load(handler_file)

        # Assert
        assert len(contract.handlers) == 1
        assert contract.handlers[0].handler_type.value == handler_type


# =============================================================================
# OSError Handling Tests (PR #173 Critical/Major Fixes)
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestFileRegistryOSErrorHandling:
    """
    Test OSError handling in FileRegistry.

    These tests verify that OSError exceptions (permission denied,
    is a directory, etc.) are properly wrapped in ModelOnexError
    instead of leaking raw OSError to callers.

    Related: PR #173 review feedback - Critical/Major issues.
    """

    def test_load_directory_path_as_file_raises_file_read_error(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
    ) -> None:
        """Test that passing a directory path to load() raises FILE_READ_ERROR."""
        # Arrange - create a directory (tmp_path is already a directory)
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(subdir)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.FILE_READ_ERROR
        assert str(subdir) in str(error) or "subdir" in str(error)

    def test_load_directory_path_includes_os_error_context(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
    ) -> None:
        """Test that loading a directory includes OS error info in context."""
        # Arrange
        subdir = tmp_path / "test_dir"
        subdir.mkdir()

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(subdir)

        error = exc_info.value
        # Context should include os_error details
        context = error.context
        has_os_error_info = (
            "os_error" in context
            or "directory" in str(error).lower()
            or "IsADirectoryError" in str(error)
        )
        assert has_os_error_info

    def test_load_does_not_leak_raw_oserror(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
    ) -> None:
        """Test that load() never leaks raw OSError."""
        # Arrange - create a directory to trigger IsADirectoryError
        subdir = tmp_path / "not_a_file"
        subdir.mkdir()

        # Act & Assert - should raise ModelOnexError, not OSError
        try:
            file_registry.load(subdir)
            pytest.fail("Expected ModelOnexError to be raised")
        except ModelOnexError:
            pass  # Expected
        except OSError as e:
            pytest.fail(f"Raw OSError leaked: {type(e).__name__}: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected exception: {type(e).__name__}: {e}")

    def test_load_all_does_not_leak_raw_oserror(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        valid_contract_yaml: str,
    ) -> None:
        """Test that load_all() never leaks raw OSError during directory scan."""
        # Arrange - create a valid directory with contracts
        (tmp_path / "contract.yaml").write_text(valid_contract_yaml)

        # Act - should not raise any OSError
        try:
            contracts = file_registry.load_all(tmp_path)
            # If it succeeds, verify the result
            assert len(contracts) == 1
        except ModelOnexError:
            pass  # Acceptable - wrapped error
        except OSError as e:
            pytest.fail(f"Raw OSError leaked: {type(e).__name__}: {e}")

    def test_load_file_path_as_not_a_directory(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        valid_contract_yaml: str,
    ) -> None:
        """Test that load_all() with file path (not dir) raises appropriate error."""
        # Arrange - create a file
        contract_file = tmp_path / "contract.yaml"
        contract_file.write_text(valid_contract_yaml)

        # Act & Assert - load_all expects directory, not file
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load_all(contract_file)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.DIRECTORY_NOT_FOUND

    def test_load_file_read_error_includes_file_path(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
    ) -> None:
        """Test that FILE_READ_ERROR includes the file path in context."""
        # Arrange
        subdir = tmp_path / "readable_dir"
        subdir.mkdir()

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(subdir)

        error = exc_info.value
        # Check file_path is in context
        assert "file_path" in error.context
        assert str(subdir) in error.context.get("file_path", "")

    def test_load_file_read_error_preserves_exception_chain(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
    ) -> None:
        """Test that FILE_READ_ERROR preserves the original exception chain."""
        # Arrange
        subdir = tmp_path / "chained_error_test"
        subdir.mkdir()

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(subdir)

        error = exc_info.value
        # The __cause__ should be the original OSError
        assert error.__cause__ is not None
        assert isinstance(error.__cause__, OSError)

    def test_from_yaml_file_deleted_after_exists_check_raises_file_not_found(
        self,
        tmp_path: Path,
        file_registry: FileRegistry,
        valid_contract_yaml: str,
    ) -> None:
        """Test TOCTOU race condition: file deleted between exists() and open().

        This tests that FileNotFoundError during the open() call (after the
        exists() check passes) is properly mapped to FILE_NOT_FOUND error code.
        This handles the race condition where a file is deleted between the
        exists check and the actual file read.

        Note: This is a documentation test - the actual TOCTOU race is hard to
        reproduce reliably. Instead, we verify that the error handling path
        exists by checking the from_yaml implementation handles FileNotFoundError
        from open() and maps it to FILE_NOT_FOUND.
        """
        # Arrange - create a file that exists initially
        contract_file = tmp_path / "toctou_test.yaml"
        contract_file.write_text(valid_contract_yaml)

        # First, verify the file loads successfully
        contract = file_registry.load(contract_file)
        assert isinstance(contract, ModelRuntimeHostContract)

        # Now delete the file to simulate TOCTOU race
        contract_file.unlink()

        # Act & Assert - loading a now-deleted file should raise FILE_NOT_FOUND
        with pytest.raises(ModelOnexError) as exc_info:
            file_registry.load(contract_file)

        error = exc_info.value
        # Verify the error code is FILE_NOT_FOUND (not FILE_READ_ERROR)
        assert error.error_code == EnumCoreErrorCode.FILE_NOT_FOUND
        # Verify file_path is in context
        context = error.context
        assert "file_path" in context
        assert str(contract_file) in context.get("file_path", "")
