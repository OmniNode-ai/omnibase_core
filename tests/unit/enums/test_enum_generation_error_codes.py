"""
Tests for EnumGenerationErrorCodes enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_generation_error_codes import EnumGenerationErrorCodes


@pytest.mark.unit
class TestEnumGenerationErrorCodes:
    """Test cases for EnumGenerationErrorCodes enum."""

    def test_enum_values(self):
        """Test that all enum values are correct."""
        # File system errors
        assert EnumGenerationErrorCodes.TOOL_PATH_NOT_FOUND == "tool_path_not_found"
        assert (
            EnumGenerationErrorCodes.CONTRACT_FILE_NOT_FOUND
            == "contract_file_not_found"
        )
        assert (
            EnumGenerationErrorCodes.OUTPUT_DIRECTORY_PERMISSION_DENIED
            == "output_directory_permission_denied"
        )
        assert (
            EnumGenerationErrorCodes.FILE_WRITE_PERMISSION_DENIED
            == "file_write_permission_denied"
        )
        assert EnumGenerationErrorCodes.FILE_SYSTEM_ERROR == "file_system_error"

        # Contract validation errors
        assert (
            EnumGenerationErrorCodes.CONTRACT_EMPTY_OR_INVALID
            == "contract_empty_or_invalid"
        )
        assert EnumGenerationErrorCodes.CONTRACT_INVALID_YAML == "contract_invalid_yaml"
        assert (
            EnumGenerationErrorCodes.CONTRACT_NOT_DICTIONARY
            == "contract_not_dictionary"
        )
        assert (
            EnumGenerationErrorCodes.CONTRACT_MISSING_REQUIRED_FIELDS
            == "contract_missing_required_fields"
        )
        assert (
            EnumGenerationErrorCodes.CONTRACT_INVALID_STRUCTURE
            == "contract_invalid_structure"
        )

        # Action analysis errors
        assert (
            EnumGenerationErrorCodes.ACTION_ANALYSIS_FAILED == "action_analysis_failed"
        )
        assert EnumGenerationErrorCodes.INPUT_STATE_INVALID == "input_state_invalid"
        assert (
            EnumGenerationErrorCodes.INPUT_STATE_PROPERTIES_INVALID
            == "input_state_properties_invalid"
        )
        assert (
            EnumGenerationErrorCodes.ACTION_DEFINITION_INVALID
            == "action_definition_invalid"
        )
        assert (
            EnumGenerationErrorCodes.ACTION_REFERENCE_INVALID
            == "action_reference_invalid"
        )
        assert (
            EnumGenerationErrorCodes.ACTION_DEFINITION_NOT_FOUND
            == "action_definition_not_found"
        )
        assert EnumGenerationErrorCodes.DEFINITIONS_INVALID == "definitions_invalid"
        assert EnumGenerationErrorCodes.NO_ACTIONS_FOUND == "no_actions_found"

        # Generation errors
        assert EnumGenerationErrorCodes.GENERATION_FAILED == "generation_failed"
        assert (
            EnumGenerationErrorCodes.NODE_DELEGATION_UPDATE_FAILED
            == "node_delegation_update_failed"
        )
        assert EnumGenerationErrorCodes.VALIDATION_FAILED == "validation_failed"

        # Content generation errors
        assert (
            EnumGenerationErrorCodes.CONTENT_GENERATION_FAILED
            == "content_generation_failed"
        )
        assert (
            EnumGenerationErrorCodes.TEMPLATE_PROCESSING_FAILED
            == "template_processing_failed"
        )
        assert (
            EnumGenerationErrorCodes.MODEL_NAME_RESOLUTION_FAILED
            == "model_name_resolution_failed"
        )

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumGenerationErrorCodes, str)
        assert issubclass(EnumGenerationErrorCodes, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values (StrValueHelper returns value)."""
        assert (
            str(EnumGenerationErrorCodes.TOOL_PATH_NOT_FOUND) == "tool_path_not_found"
        )
        assert (
            str(EnumGenerationErrorCodes.CONTRACT_FILE_NOT_FOUND)
            == "contract_file_not_found"
        )
        assert str(EnumGenerationErrorCodes.GENERATION_FAILED) == "generation_failed"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values."""
        values = list(EnumGenerationErrorCodes)
        assert len(values) == 24
        assert EnumGenerationErrorCodes.TOOL_PATH_NOT_FOUND in values
        assert EnumGenerationErrorCodes.CONTRACT_FILE_NOT_FOUND in values
        assert EnumGenerationErrorCodes.GENERATION_FAILED in values
        assert EnumGenerationErrorCodes.CONTENT_GENERATION_FAILED in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert "tool_path_not_found" in EnumGenerationErrorCodes
        assert "contract_file_not_found" in EnumGenerationErrorCodes
        assert "generation_failed" in EnumGenerationErrorCodes
        assert "content_generation_failed" in EnumGenerationErrorCodes
        assert "invalid" not in EnumGenerationErrorCodes

    def test_enum_comparison(self):
        """Test enum comparison."""
        assert EnumGenerationErrorCodes.TOOL_PATH_NOT_FOUND == "tool_path_not_found"
        assert (
            EnumGenerationErrorCodes.CONTRACT_FILE_NOT_FOUND
            == "contract_file_not_found"
        )
        assert EnumGenerationErrorCodes.GENERATION_FAILED == "generation_failed"
        assert (
            EnumGenerationErrorCodes.CONTENT_GENERATION_FAILED
            == "content_generation_failed"
        )

    def test_enum_serialization(self):
        """Test enum serialization."""
        assert (
            EnumGenerationErrorCodes.TOOL_PATH_NOT_FOUND.value == "tool_path_not_found"
        )
        assert (
            EnumGenerationErrorCodes.CONTRACT_FILE_NOT_FOUND.value
            == "contract_file_not_found"
        )
        assert EnumGenerationErrorCodes.GENERATION_FAILED.value == "generation_failed"
        assert (
            EnumGenerationErrorCodes.CONTENT_GENERATION_FAILED.value
            == "content_generation_failed"
        )

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        assert (
            EnumGenerationErrorCodes("tool_path_not_found")
            == EnumGenerationErrorCodes.TOOL_PATH_NOT_FOUND
        )
        assert (
            EnumGenerationErrorCodes("contract_file_not_found")
            == EnumGenerationErrorCodes.CONTRACT_FILE_NOT_FOUND
        )
        assert (
            EnumGenerationErrorCodes("generation_failed")
            == EnumGenerationErrorCodes.GENERATION_FAILED
        )
        assert (
            EnumGenerationErrorCodes("content_generation_failed")
            == EnumGenerationErrorCodes.CONTENT_GENERATION_FAILED
        )

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumGenerationErrorCodes("invalid")

    def test_enum_all_values(self):
        """Test that all enum values are accessible."""
        all_values = [code.value for code in EnumGenerationErrorCodes]
        expected_values = [
            "tool_path_not_found",
            "contract_file_not_found",
            "output_directory_permission_denied",
            "file_write_permission_denied",
            "file_system_error",
            "contract_empty_or_invalid",
            "contract_invalid_yaml",
            "contract_not_dictionary",
            "contract_missing_required_fields",
            "contract_invalid_structure",
            "action_analysis_failed",
            "input_state_invalid",
            "input_state_properties_invalid",
            "action_definition_invalid",
            "action_reference_invalid",
            "action_definition_not_found",
            "definitions_invalid",
            "no_actions_found",
            "generation_failed",
            "node_delegation_update_failed",
            "validation_failed",
            "content_generation_failed",
            "template_processing_failed",
            "model_name_resolution_failed",
        ]
        assert set(all_values) == set(expected_values)

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert (
            "Error codes for tool generation operations"
            in EnumGenerationErrorCodes.__doc__
        )

    def test_file_system_errors(self):
        """Test file system error codes."""
        file_system_errors = [
            EnumGenerationErrorCodes.TOOL_PATH_NOT_FOUND,
            EnumGenerationErrorCodes.CONTRACT_FILE_NOT_FOUND,
            EnumGenerationErrorCodes.OUTPUT_DIRECTORY_PERMISSION_DENIED,
            EnumGenerationErrorCodes.FILE_WRITE_PERMISSION_DENIED,
            EnumGenerationErrorCodes.FILE_SYSTEM_ERROR,
        ]
        for error in file_system_errors:
            assert error in EnumGenerationErrorCodes

    def test_contract_validation_errors(self):
        """Test contract validation error codes."""
        contract_errors = [
            EnumGenerationErrorCodes.CONTRACT_EMPTY_OR_INVALID,
            EnumGenerationErrorCodes.CONTRACT_INVALID_YAML,
            EnumGenerationErrorCodes.CONTRACT_NOT_DICTIONARY,
            EnumGenerationErrorCodes.CONTRACT_MISSING_REQUIRED_FIELDS,
            EnumGenerationErrorCodes.CONTRACT_INVALID_STRUCTURE,
        ]
        for error in contract_errors:
            assert error in EnumGenerationErrorCodes

    def test_action_analysis_errors(self):
        """Test action analysis error codes."""
        action_errors = [
            EnumGenerationErrorCodes.ACTION_ANALYSIS_FAILED,
            EnumGenerationErrorCodes.INPUT_STATE_INVALID,
            EnumGenerationErrorCodes.INPUT_STATE_PROPERTIES_INVALID,
            EnumGenerationErrorCodes.ACTION_DEFINITION_INVALID,
            EnumGenerationErrorCodes.ACTION_REFERENCE_INVALID,
            EnumGenerationErrorCodes.ACTION_DEFINITION_NOT_FOUND,
            EnumGenerationErrorCodes.DEFINITIONS_INVALID,
            EnumGenerationErrorCodes.NO_ACTIONS_FOUND,
        ]
        for error in action_errors:
            assert error in EnumGenerationErrorCodes

    def test_generation_errors(self):
        """Test generation error codes."""
        generation_errors = [
            EnumGenerationErrorCodes.GENERATION_FAILED,
            EnumGenerationErrorCodes.NODE_DELEGATION_UPDATE_FAILED,
            EnumGenerationErrorCodes.VALIDATION_FAILED,
        ]
        for error in generation_errors:
            assert error in EnumGenerationErrorCodes

    def test_content_generation_errors(self):
        """Test content generation error codes."""
        content_errors = [
            EnumGenerationErrorCodes.CONTENT_GENERATION_FAILED,
            EnumGenerationErrorCodes.TEMPLATE_PROCESSING_FAILED,
            EnumGenerationErrorCodes.MODEL_NAME_RESOLUTION_FAILED,
        ]
        for error in content_errors:
            assert error in EnumGenerationErrorCodes
