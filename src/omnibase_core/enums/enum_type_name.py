"""
Type Name Enum.

Strongly typed type name values for node types.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumTypeName(StrValueHelper, str, Enum):
    """
    Strongly typed type name values for node types.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support for node type operations.
    """

    # Generation nodes
    CONTRACT_TO_MODEL = "CONTRACT_TO_MODEL"
    MULTI_DOC_MODEL_GENERATOR = "MULTI_DOC_MODEL_GENERATOR"
    GENERATE_ERROR_CODES = "GENERATE_ERROR_CODES"
    GENERATE_INTROSPECTION = "GENERATE_INTROSPECTION"
    NODE_GENERATOR = "NODE_GENERATOR"

    # Template nodes
    TEMPLATE_ENGINE = "TEMPLATE_ENGINE"
    FILE_GENERATOR = "FILE_GENERATOR"
    TEMPLATE_VALIDATOR = "TEMPLATE_VALIDATOR"

    # Validation nodes
    VALIDATION_ENGINE = "VALIDATION_ENGINE"
    STANDARDS_COMPLIANCE_FIXER = "STANDARDS_COMPLIANCE_FIXER"
    PARITY_VALIDATOR_WITH_FIXES = "PARITY_VALIDATOR_WITH_FIXES"
    CONTRACT_COMPLIANCE = "CONTRACT_COMPLIANCE"
    INTROSPECTION_VALIDITY = "INTROSPECTION_VALIDITY"
    SCHEMA_CONFORMANCE = "SCHEMA_CONFORMANCE"
    ERROR_CODE_USAGE = "ERROR_CODE_USAGE"

    # CLI nodes
    CLI_COMMANDS = "CLI_COMMANDS"
    CLI_NODE_PARITY = "CLI_NODE_PARITY"

    # Discovery nodes
    NODE_DISCOVERY = "NODE_DISCOVERY"
    NODE_VALIDATION = "NODE_VALIDATION"
    METADATA_LOADER = "METADATA_LOADER"

    # Schema nodes
    SCHEMA_GENERATOR = "SCHEMA_GENERATOR"
    SCHEMA_DISCOVERY = "SCHEMA_DISCOVERY"
    SCHEMA_TO_PYDANTIC = "SCHEMA_TO_PYDANTIC"
    PROTOCOL_GENERATOR = "PROTOCOL_GENERATOR"

    # Runtime nodes
    BACKEND_SELECTION = "BACKEND_SELECTION"
    NODE_MANAGER_RUNNER = "NODE_MANAGER_RUNNER"
    MAINTENANCE = "MAINTENANCE"

    # Logging nodes
    NODE_LOGGER_EMIT_LOG_EVENT = "NODE_LOGGER_EMIT_LOG_EVENT"
    LOGGING_UTILS = "LOGGING_UTILS"

    # Testing nodes
    SCENARIO_RUNNER = "SCENARIO_RUNNER"

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
