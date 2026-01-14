"""
Generation error codes enum for tool generation operations.

Provides strongly-typed error codes for generation-specific error handling
with proper ONEX enum naming conventions.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumGenerationErrorCodes(StrValueHelper, str, Enum):
    """Error codes for tool generation operations."""

    # File system errors
    TOOL_PATH_NOT_FOUND = "tool_path_not_found"
    CONTRACT_FILE_NOT_FOUND = "contract_file_not_found"
    OUTPUT_DIRECTORY_PERMISSION_DENIED = "output_directory_permission_denied"
    FILE_WRITE_PERMISSION_DENIED = "file_write_permission_denied"
    FILE_SYSTEM_ERROR = "file_system_error"

    # Contract validation errors
    CONTRACT_EMPTY_OR_INVALID = "contract_empty_or_invalid"
    CONTRACT_INVALID_YAML = "contract_invalid_yaml"
    CONTRACT_NOT_DICTIONARY = "contract_not_dictionary"
    CONTRACT_MISSING_REQUIRED_FIELDS = "contract_missing_required_fields"
    CONTRACT_INVALID_STRUCTURE = "contract_invalid_structure"

    # Action analysis errors
    ACTION_ANALYSIS_FAILED = "action_analysis_failed"
    INPUT_STATE_INVALID = "input_state_invalid"
    INPUT_STATE_PROPERTIES_INVALID = "input_state_properties_invalid"
    ACTION_DEFINITION_INVALID = "action_definition_invalid"
    ACTION_REFERENCE_INVALID = "action_reference_invalid"
    ACTION_DEFINITION_NOT_FOUND = "action_definition_not_found"
    DEFINITIONS_INVALID = "definitions_invalid"
    NO_ACTIONS_FOUND = "no_actions_found"

    # Generation errors
    GENERATION_FAILED = "generation_failed"
    NODE_DELEGATION_UPDATE_FAILED = "node_delegation_update_failed"
    VALIDATION_FAILED = "validation_failed"

    # Content generation errors
    CONTENT_GENERATION_FAILED = "content_generation_failed"
    TEMPLATE_PROCESSING_FAILED = "template_processing_failed"
    MODEL_NAME_RESOLUTION_FAILED = "model_name_resolution_failed"


__all__ = ["EnumGenerationErrorCodes"]
