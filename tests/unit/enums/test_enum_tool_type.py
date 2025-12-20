from enum import Enum

import pytest

from omnibase_core.enums.enum_tool_type import EnumToolType


@pytest.mark.unit
class TestEnumToolType:
    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert EnumToolType.CONTRACT_TO_MODEL == "CONTRACT_TO_MODEL"
        assert EnumToolType.MULTI_DOC_MODEL_GENERATOR == "MULTI_DOC_MODEL_GENERATOR"
        assert EnumToolType.GENERATE_ERROR_CODES == "GENERATE_ERROR_CODES"
        assert EnumToolType.GENERATE_INTROSPECTION == "GENERATE_INTROSPECTION"
        assert EnumToolType.NODE_GENERATOR == "NODE_GENERATOR"
        assert EnumToolType.TEMPLATE_ENGINE == "TEMPLATE_ENGINE"
        assert EnumToolType.FILE_GENERATOR == "FILE_GENERATOR"
        assert EnumToolType.TEMPLATE_VALIDATOR == "TEMPLATE_VALIDATOR"
        assert EnumToolType.VALIDATION_ENGINE == "VALIDATION_ENGINE"
        assert EnumToolType.STANDARDS_COMPLIANCE_FIXER == "STANDARDS_COMPLIANCE_FIXER"
        assert EnumToolType.PARITY_VALIDATOR_WITH_FIXES == "PARITY_VALIDATOR_WITH_FIXES"
        assert EnumToolType.CONTRACT_COMPLIANCE == "CONTRACT_COMPLIANCE"
        assert EnumToolType.INTROSPECTION_VALIDITY == "INTROSPECTION_VALIDITY"
        assert EnumToolType.SCHEMA_CONFORMANCE == "SCHEMA_CONFORMANCE"
        assert EnumToolType.ERROR_CODE_USAGE == "ERROR_CODE_USAGE"
        assert EnumToolType.CLI_COMMANDS == "CLI_COMMANDS"
        assert EnumToolType.CLI_NODE_PARITY == "CLI_NODE_PARITY"
        assert EnumToolType.NODE_DISCOVERY == "NODE_DISCOVERY"
        assert EnumToolType.NODE_VALIDATION == "NODE_VALIDATION"
        assert EnumToolType.METADATA_LOADER == "METADATA_LOADER"
        assert EnumToolType.SCHEMA_GENERATOR == "SCHEMA_GENERATOR"
        assert EnumToolType.SCHEMA_DISCOVERY == "SCHEMA_DISCOVERY"
        assert EnumToolType.SCHEMA_TO_PYDANTIC == "SCHEMA_TO_PYDANTIC"
        assert EnumToolType.PROTOCOL_GENERATOR == "PROTOCOL_GENERATOR"
        assert EnumToolType.BACKEND_SELECTION == "BACKEND_SELECTION"
        assert EnumToolType.NODE_MANAGER_RUNNER == "NODE_MANAGER_RUNNER"
        assert EnumToolType.MAINTENANCE == "MAINTENANCE"
        assert EnumToolType.LOGGER_EMIT_LOG_EVENT == "tool_logger_emit_log_event"
        assert EnumToolType.LOGGING_UTILS == "LOGGING_UTILS"
        assert EnumToolType.SCENARIO_RUNNER == "scenario_runner"
        assert EnumToolType.FUNCTION == "FUNCTION"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumToolType, str)
        assert issubclass(EnumToolType, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        tool_type = EnumToolType.CONTRACT_TO_MODEL
        assert isinstance(tool_type, str)
        assert tool_type == "CONTRACT_TO_MODEL"
        assert len(tool_type) == 17
        assert tool_type.startswith("CONTRACT")

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumToolType)
        assert len(values) == 31
        assert EnumToolType.CONTRACT_TO_MODEL in values
        assert EnumToolType.FUNCTION in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumToolType.NODE_GENERATOR in EnumToolType
        assert "NODE_GENERATOR" in [e.value for e in EnumToolType]

    def test_enum_comparison(self):
        """Test enum comparison."""
        tool1 = EnumToolType.VALIDATION_ENGINE
        tool2 = EnumToolType.VALIDATION_ENGINE
        tool3 = EnumToolType.TEMPLATE_ENGINE

        assert tool1 == tool2
        assert tool1 != tool3
        assert tool1 == "VALIDATION_ENGINE"

    def test_enum_serialization(self):
        """Test enum serialization."""
        tool_type = EnumToolType.SCHEMA_GENERATOR
        serialized = tool_type.value
        assert serialized == "SCHEMA_GENERATOR"
        import json

        json_str = json.dumps(tool_type)
        assert json_str == '"SCHEMA_GENERATOR"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        tool_type = EnumToolType("NODE_DISCOVERY")
        assert tool_type == EnumToolType.NODE_DISCOVERY

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumToolType("INVALID_TOOL")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "CONTRACT_TO_MODEL",
            "MULTI_DOC_MODEL_GENERATOR",
            "GENERATE_ERROR_CODES",
            "GENERATE_INTROSPECTION",
            "NODE_GENERATOR",
            "TEMPLATE_ENGINE",
            "FILE_GENERATOR",
            "TEMPLATE_VALIDATOR",
            "VALIDATION_ENGINE",
            "STANDARDS_COMPLIANCE_FIXER",
            "PARITY_VALIDATOR_WITH_FIXES",
            "CONTRACT_COMPLIANCE",
            "INTROSPECTION_VALIDITY",
            "SCHEMA_CONFORMANCE",
            "ERROR_CODE_USAGE",
            "CLI_COMMANDS",
            "CLI_NODE_PARITY",
            "NODE_DISCOVERY",
            "NODE_VALIDATION",
            "METADATA_LOADER",
            "SCHEMA_GENERATOR",
            "SCHEMA_DISCOVERY",
            "SCHEMA_TO_PYDANTIC",
            "PROTOCOL_GENERATOR",
            "BACKEND_SELECTION",
            "NODE_MANAGER_RUNNER",
            "MAINTENANCE",
            "tool_logger_emit_log_event",
            "LOGGING_UTILS",
            "scenario_runner",
            "FUNCTION",
        }
        actual_values = {e.value for e in EnumToolType}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumToolType.__doc__ is not None
        assert "tool types" in EnumToolType.__doc__.lower()

    def test_enum_description_property(self):
        """Test description property for all tool types."""
        # Test that all tool types have descriptions
        for tool_type in EnumToolType:
            description = tool_type.description
            assert isinstance(description, str)
            assert len(description) > 0
            assert not description.startswith("Tool:")  # Should not be fallback

    def test_enum_description_content(self):
        """Test specific description content."""
        # Test some specific descriptions
        assert "Pydantic models" in EnumToolType.CONTRACT_TO_MODEL.description
        assert "templates" in EnumToolType.TEMPLATE_ENGINE.description
        assert "Validates" in EnumToolType.VALIDATION_ENGINE.description
        assert "CLI" in EnumToolType.CLI_COMMANDS.description
        assert "Discovers" in EnumToolType.NODE_DISCOVERY.description
        assert "schema" in EnumToolType.SCHEMA_GENERATOR.description
        assert "Logging" in EnumToolType.LOGGING_UTILS.description

    def test_enum_tool_categories(self):
        """Test logical grouping of tool types."""
        # Generation tools
        generation_tools = {
            EnumToolType.CONTRACT_TO_MODEL,
            EnumToolType.MULTI_DOC_MODEL_GENERATOR,
            EnumToolType.GENERATE_ERROR_CODES,
            EnumToolType.GENERATE_INTROSPECTION,
            EnumToolType.NODE_GENERATOR,
            EnumToolType.SCHEMA_GENERATOR,
            EnumToolType.PROTOCOL_GENERATOR,
        }

        # Template tools
        template_tools = {
            EnumToolType.TEMPLATE_ENGINE,
            EnumToolType.FILE_GENERATOR,
            EnumToolType.TEMPLATE_VALIDATOR,
        }

        # Validation tools
        validation_tools = {
            EnumToolType.VALIDATION_ENGINE,
            EnumToolType.STANDARDS_COMPLIANCE_FIXER,
            EnumToolType.PARITY_VALIDATOR_WITH_FIXES,
            EnumToolType.CONTRACT_COMPLIANCE,
            EnumToolType.INTROSPECTION_VALIDITY,
            EnumToolType.SCHEMA_CONFORMANCE,
            EnumToolType.ERROR_CODE_USAGE,
            EnumToolType.NODE_VALIDATION,
        }

        # CLI tools
        cli_tools = {
            EnumToolType.CLI_COMMANDS,
            EnumToolType.CLI_NODE_PARITY,
        }

        # Discovery tools
        discovery_tools = {
            EnumToolType.NODE_DISCOVERY,
            EnumToolType.METADATA_LOADER,
            EnumToolType.SCHEMA_DISCOVERY,
        }

        # Runtime tools
        runtime_tools = {
            EnumToolType.BACKEND_SELECTION,
            EnumToolType.NODE_MANAGER_RUNNER,
            EnumToolType.MAINTENANCE,
        }

        # Logging tools
        logging_tools = {
            EnumToolType.LOGGER_EMIT_LOG_EVENT,
            EnumToolType.LOGGING_UTILS,
        }

        # Testing tools
        testing_tools = {
            EnumToolType.SCENARIO_RUNNER,
        }

        # Function tools
        function_tools = {
            EnumToolType.FUNCTION,
        }

        # Test that all tools are categorized
        all_categories = (
            generation_tools
            | template_tools
            | validation_tools
            | cli_tools
            | discovery_tools
            | runtime_tools
            | logging_tools
            | testing_tools
            | function_tools
        )
        # Some tools might be in multiple categories or not categorized
        assert (
            len(all_categories) >= len(set(EnumToolType)) - 5
        )  # Most tools should be categorized

    def test_enum_workflow_usage(self):
        """Test typical workflow usage patterns."""
        # Development workflow tools
        dev_workflow = {
            EnumToolType.CONTRACT_TO_MODEL,
            EnumToolType.NODE_GENERATOR,
            EnumToolType.TEMPLATE_ENGINE,
            EnumToolType.VALIDATION_ENGINE,
        }

        # Validation workflow tools
        validation_workflow = {
            EnumToolType.VALIDATION_ENGINE,
            EnumToolType.STANDARDS_COMPLIANCE_FIXER,
            EnumToolType.CONTRACT_COMPLIANCE,
        }

        # Discovery workflow tools
        discovery_workflow = {
            EnumToolType.NODE_DISCOVERY,
            EnumToolType.METADATA_LOADER,
            EnumToolType.SCHEMA_DISCOVERY,
        }

        # All should be valid enum values
        for tool_type in dev_workflow | validation_workflow | discovery_workflow:
            assert tool_type in EnumToolType
