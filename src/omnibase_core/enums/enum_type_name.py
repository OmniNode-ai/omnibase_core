"""
Type Name Enum.

Strongly typed type name values for node types.
"""

from __future__ import annotations

from enum import Enum


class EnumTypeName(str, Enum):
    """
    Strongly typed type name values for node types.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support for node type operations.
    """

    # Generation nodes
    CONTRACT_TO_MODEL = "contract_to_model"
    MULTI_DOC_MODEL_GENERATOR = "multi_doc_model_generator"
    GENERATE_ERROR_CODES = "generate_error_codes"
    GENERATE_INTROSPECTION = "generate_introspection"
    NODE_GENERATOR = "node_generator"

    # Template nodes
    TEMPLATE_ENGINE = "template_engine"
    FILE_GENERATOR = "file_generator"
    TEMPLATE_VALIDATOR = "template_validator"

    # Validation nodes
    VALIDATION_ENGINE = "validation_engine"
    STANDARDS_COMPLIANCE_FIXER = "standards_compliance_fixer"
    PARITY_VALIDATOR_WITH_FIXES = "parity_validator_with_fixes"
    CONTRACT_COMPLIANCE = "contract_compliance"
    INTROSPECTION_VALIDITY = "introspection_validity"
    SCHEMA_CONFORMANCE = "schema_conformance"
    ERROR_CODE_USAGE = "error_code_usage"

    # CLI nodes
    CLI_COMMANDS = "cli_commands"
    CLI_NODE_PARITY = "cli_node_parity"

    # Discovery nodes
    NODE_DISCOVERY = "node_discovery"
    NODE_VALIDATION = "node_validation"
    METADATA_LOADER = "metadata_loader"

    # Schema nodes
    SCHEMA_GENERATOR = "schema_generator"
    SCHEMA_DISCOVERY = "schema_discovery"
    SCHEMA_TO_PYDANTIC = "schema_to_pydantic"
    PROTOCOL_GENERATOR = "protocol_generator"

    # Runtime nodes
    BACKEND_SELECTION = "backend_selection"
    NODE_MANAGER_RUNNER = "node_manager_runner"
    MAINTENANCE = "maintenance"

    # Logging nodes
    NODE_LOGGER_EMIT_LOG_EVENT = "node_logger_emit_log_event"
    LOGGING_UTILS = "logging_utils"

    # Testing nodes
    SCENARIO_RUNNER = "scenario_runner"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_generation_node(cls, type_name: EnumTypeName) -> bool:
        """Check if the type name represents a generation node."""
        return type_name in {
            cls.CONTRACT_TO_MODEL,
            cls.MULTI_DOC_MODEL_GENERATOR,
            cls.GENERATE_ERROR_CODES,
            cls.GENERATE_INTROSPECTION,
            cls.NODE_GENERATOR,
        }

    @classmethod
    def is_template_node(cls, type_name: EnumTypeName) -> bool:
        """Check if the type name represents a template node."""
        return type_name in {
            cls.TEMPLATE_ENGINE,
            cls.FILE_GENERATOR,
            cls.TEMPLATE_VALIDATOR,
        }

    @classmethod
    def is_validation_node(cls, type_name: EnumTypeName) -> bool:
        """Check if the type name represents a validation node."""
        return type_name in {
            cls.VALIDATION_ENGINE,
            cls.STANDARDS_COMPLIANCE_FIXER,
            cls.PARITY_VALIDATOR_WITH_FIXES,
            cls.CONTRACT_COMPLIANCE,
            cls.INTROSPECTION_VALIDITY,
            cls.SCHEMA_CONFORMANCE,
            cls.ERROR_CODE_USAGE,
        }

    @classmethod
    def is_cli_node(cls, type_name: EnumTypeName) -> bool:
        """Check if the type name represents a CLI node."""
        return type_name in {
            cls.CLI_COMMANDS,
            cls.CLI_NODE_PARITY,
        }

    @classmethod
    def is_discovery_node(cls, type_name: EnumTypeName) -> bool:
        """Check if the type name represents a discovery node."""
        return type_name in {
            cls.NODE_DISCOVERY,
            cls.NODE_VALIDATION,
            cls.METADATA_LOADER,
        }

    @classmethod
    def is_schema_node(cls, type_name: EnumTypeName) -> bool:
        """Check if the type name represents a schema node."""
        return type_name in {
            cls.SCHEMA_GENERATOR,
            cls.SCHEMA_DISCOVERY,
            cls.SCHEMA_TO_PYDANTIC,
            cls.PROTOCOL_GENERATOR,
        }

    @classmethod
    def is_runtime_node(cls, type_name: EnumTypeName) -> bool:
        """Check if the type name represents a runtime node."""
        return type_name in {
            cls.BACKEND_SELECTION,
            cls.NODE_MANAGER_RUNNER,
            cls.MAINTENANCE,
        }


# Export for use
__all__ = ["EnumTypeName"]
