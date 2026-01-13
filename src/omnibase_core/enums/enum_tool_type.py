"""
Enum for all tool types used in node_manager.

This provides type safety and a single source of truth for tool names,
avoiding string-based lookups and potential typos.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumToolType(StrValueHelper, str, Enum):
    """Enumeration of all tool types available in node_manager."""

    # Core generation tools
    CONTRACT_TO_MODEL = "CONTRACT_TO_MODEL"
    MULTI_DOC_MODEL_GENERATOR = "MULTI_DOC_MODEL_GENERATOR"
    GENERATE_ERROR_CODES = "GENERATE_ERROR_CODES"
    GENERATE_INTROSPECTION = "GENERATE_INTROSPECTION"
    NODE_GENERATOR = "NODE_GENERATOR"

    # Template and file management
    TEMPLATE_ENGINE = "TEMPLATE_ENGINE"
    FILE_GENERATOR = "FILE_GENERATOR"
    TEMPLATE_VALIDATOR = "TEMPLATE_VALIDATOR"

    # Validation and compliance
    VALIDATION_ENGINE = "VALIDATION_ENGINE"
    STANDARDS_COMPLIANCE_FIXER = "STANDARDS_COMPLIANCE_FIXER"
    PARITY_VALIDATOR_WITH_FIXES = "PARITY_VALIDATOR_WITH_FIXES"
    CONTRACT_COMPLIANCE = "CONTRACT_COMPLIANCE"
    INTROSPECTION_VALIDITY = "INTROSPECTION_VALIDITY"
    SCHEMA_CONFORMANCE = "SCHEMA_CONFORMANCE"
    ERROR_CODE_USAGE = "ERROR_CODE_USAGE"

    # CLI and commands
    CLI_COMMANDS = "CLI_COMMANDS"
    CLI_NODE_PARITY = "CLI_NODE_PARITY"

    # Discovery and metadata
    NODE_DISCOVERY = "NODE_DISCOVERY"
    NODE_VALIDATION = "NODE_VALIDATION"
    METADATA_LOADER = "METADATA_LOADER"

    # Schema generation
    SCHEMA_GENERATOR = "SCHEMA_GENERATOR"
    SCHEMA_DISCOVERY = "SCHEMA_DISCOVERY"
    SCHEMA_TO_PYDANTIC = "SCHEMA_TO_PYDANTIC"

    # Protocol generation
    PROTOCOL_GENERATOR = "PROTOCOL_GENERATOR"

    # Backend and runtime
    BACKEND_SELECTION = "BACKEND_SELECTION"
    NODE_MANAGER_RUNNER = "NODE_MANAGER_RUNNER"

    # Maintenance
    MAINTENANCE = "MAINTENANCE"

    # Logging and utilities
    LOGGER_EMIT_LOG_EVENT = (
        "tool_logger_emit_log_event"  # Keep original name for current standards
    )
    LOGGING_UTILS = "LOGGING_UTILS"
    SCENARIO_RUNNER = "scenario_runner"  # Keep original name for current standards

    # Function tools
    FUNCTION = "FUNCTION"  # Language-agnostic function tool type

    @property
    def description(self) -> str:
        """Get a human-readable description of the tool type."""
        descriptions = {
            self.CONTRACT_TO_MODEL: "Generates Pydantic models from contract.yaml",
            self.MULTI_DOC_MODEL_GENERATOR: "Generates models from multiple YAML documents",
            self.GENERATE_ERROR_CODES: "Generates error code enums from contract",
            self.GENERATE_INTROSPECTION: "Generates introspection metadata",
            self.NODE_GENERATOR: "Generates complete node structure from templates",
            self.TEMPLATE_ENGINE: "Processes templates with token replacement",
            self.FILE_GENERATOR: "Generates files from templates",
            self.TEMPLATE_VALIDATOR: "Validates node templates for consistency",
            self.VALIDATION_ENGINE: "Validates node structure and contracts",
            self.STANDARDS_COMPLIANCE_FIXER: "Fixes code to comply with ONEX standards",
            self.PARITY_VALIDATOR_WITH_FIXES: "Validates and fixes parity issues",
            self.CONTRACT_COMPLIANCE: "Validates contract compliance",
            self.INTROSPECTION_VALIDITY: "Validates introspection data",
            self.SCHEMA_CONFORMANCE: "Validates schema conformance",
            self.ERROR_CODE_USAGE: "Validates error code usage",
            self.CLI_COMMANDS: "Handles CLI command generation",
            self.CLI_NODE_PARITY: "Validates CLI and node parity",
            self.NODE_DISCOVERY: "Discovers nodes in the codebase",
            self.NODE_VALIDATION: "Validates node implementation",
            self.METADATA_LOADER: "Loads node metadata",
            self.SCHEMA_GENERATOR: "Generates JSON schemas",
            self.SCHEMA_DISCOVERY: "Discovers and parses schemas",
            self.SCHEMA_TO_PYDANTIC: "Converts schemas to Pydantic models",
            self.PROTOCOL_GENERATOR: "Generates protocol interfaces",
            self.BACKEND_SELECTION: "Selects appropriate backend",
            self.NODE_MANAGER_RUNNER: "Runs node manager operations",
            self.MAINTENANCE: "Handles maintenance operations",
            self.LOGGER_EMIT_LOG_EVENT: "Emits structured log events",
            self.LOGGING_UTILS: "Logging utility functions",
            self.SCENARIO_RUNNER: "Runs test scenarios",
            self.FUNCTION: "Language-agnostic function tool",
        }
        return descriptions.get(self, f"Tool: {self.value}")
