# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for EnumTypeName.

Tests all aspects of the type name enum including:
- Enum value validation
- Helper methods and class methods
- String representation
- JSON serialization compatibility
- Pydantic integration
- Node type categorization logic
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_type_name import EnumTypeName


@pytest.mark.unit
class TestEnumTypeName:
    """Test cases for EnumTypeName."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        # Generation nodes
        assert EnumTypeName.CONTRACT_TO_MODEL.value == "CONTRACT_TO_MODEL"
        assert (
            EnumTypeName.MULTI_DOC_MODEL_GENERATOR.value == "MULTI_DOC_MODEL_GENERATOR"
        )
        assert EnumTypeName.GENERATE_ERROR_CODES.value == "GENERATE_ERROR_CODES"
        assert EnumTypeName.GENERATE_INTROSPECTION.value == "GENERATE_INTROSPECTION"
        assert EnumTypeName.NODE_GENERATOR.value == "NODE_GENERATOR"

        # Template nodes
        assert EnumTypeName.TEMPLATE_ENGINE.value == "TEMPLATE_ENGINE"
        assert EnumTypeName.FILE_GENERATOR.value == "FILE_GENERATOR"
        assert EnumTypeName.TEMPLATE_VALIDATOR.value == "TEMPLATE_VALIDATOR"

        # Validation nodes
        assert EnumTypeName.VALIDATION_ENGINE.value == "VALIDATION_ENGINE"
        assert (
            EnumTypeName.STANDARDS_COMPLIANCE_FIXER.value
            == "STANDARDS_COMPLIANCE_FIXER"
        )
        assert (
            EnumTypeName.PARITY_VALIDATOR_WITH_FIXES.value
            == "PARITY_VALIDATOR_WITH_FIXES"
        )

    def test_string_representation(self):
        """Test string representation of enum values."""
        assert str(EnumTypeName.CONTRACT_TO_MODEL) == "CONTRACT_TO_MODEL"
        assert str(EnumTypeName.TEMPLATE_ENGINE) == "TEMPLATE_ENGINE"
        assert str(EnumTypeName.VALIDATION_ENGINE) == "VALIDATION_ENGINE"
        assert str(EnumTypeName.CLI_COMMANDS) == "CLI_COMMANDS"

    def test_is_generation_node(self):
        """Test is_generation_node classification method."""
        # Should be generation nodes
        assert EnumTypeName.is_generation_node(EnumTypeName.CONTRACT_TO_MODEL) is True
        assert (
            EnumTypeName.is_generation_node(EnumTypeName.MULTI_DOC_MODEL_GENERATOR)
            is True
        )
        assert (
            EnumTypeName.is_generation_node(EnumTypeName.GENERATE_ERROR_CODES) is True
        )
        assert (
            EnumTypeName.is_generation_node(EnumTypeName.GENERATE_INTROSPECTION) is True
        )
        assert EnumTypeName.is_generation_node(EnumTypeName.NODE_GENERATOR) is True

        # Should not be generation nodes
        assert EnumTypeName.is_generation_node(EnumTypeName.TEMPLATE_ENGINE) is False
        assert EnumTypeName.is_generation_node(EnumTypeName.VALIDATION_ENGINE) is False
        assert EnumTypeName.is_generation_node(EnumTypeName.CLI_COMMANDS) is False

    def test_is_template_node(self):
        """Test is_template_node classification method."""
        # Should be template nodes
        assert EnumTypeName.is_template_node(EnumTypeName.TEMPLATE_ENGINE) is True
        assert EnumTypeName.is_template_node(EnumTypeName.FILE_GENERATOR) is True
        assert EnumTypeName.is_template_node(EnumTypeName.TEMPLATE_VALIDATOR) is True

        # Should not be template nodes
        assert EnumTypeName.is_template_node(EnumTypeName.CONTRACT_TO_MODEL) is False
        assert EnumTypeName.is_template_node(EnumTypeName.VALIDATION_ENGINE) is False
        assert EnumTypeName.is_template_node(EnumTypeName.CLI_COMMANDS) is False

    def test_is_validation_node(self):
        """Test is_validation_node classification method."""
        # Should be validation nodes
        assert EnumTypeName.is_validation_node(EnumTypeName.VALIDATION_ENGINE) is True
        assert (
            EnumTypeName.is_validation_node(EnumTypeName.STANDARDS_COMPLIANCE_FIXER)
            is True
        )
        assert (
            EnumTypeName.is_validation_node(EnumTypeName.PARITY_VALIDATOR_WITH_FIXES)
            is True
        )
        assert EnumTypeName.is_validation_node(EnumTypeName.CONTRACT_COMPLIANCE) is True
        assert (
            EnumTypeName.is_validation_node(EnumTypeName.INTROSPECTION_VALIDITY) is True
        )
        assert EnumTypeName.is_validation_node(EnumTypeName.SCHEMA_CONFORMANCE) is True
        assert EnumTypeName.is_validation_node(EnumTypeName.ERROR_CODE_USAGE) is True

        # Should not be validation nodes
        assert EnumTypeName.is_validation_node(EnumTypeName.CONTRACT_TO_MODEL) is False
        assert EnumTypeName.is_validation_node(EnumTypeName.TEMPLATE_ENGINE) is False
        assert EnumTypeName.is_validation_node(EnumTypeName.CLI_COMMANDS) is False

    def test_is_cli_node(self):
        """Test is_cli_node classification method."""
        # Should be CLI nodes
        assert EnumTypeName.is_cli_node(EnumTypeName.CLI_COMMANDS) is True
        assert EnumTypeName.is_cli_node(EnumTypeName.CLI_NODE_PARITY) is True

        # Should not be CLI nodes
        assert EnumTypeName.is_cli_node(EnumTypeName.CONTRACT_TO_MODEL) is False
        assert EnumTypeName.is_cli_node(EnumTypeName.TEMPLATE_ENGINE) is False
        assert EnumTypeName.is_cli_node(EnumTypeName.VALIDATION_ENGINE) is False

    def test_is_discovery_node(self):
        """Test is_discovery_node classification method."""
        # Should be discovery nodes
        assert EnumTypeName.is_discovery_node(EnumTypeName.NODE_DISCOVERY) is True
        assert EnumTypeName.is_discovery_node(EnumTypeName.NODE_VALIDATION) is True
        assert EnumTypeName.is_discovery_node(EnumTypeName.METADATA_LOADER) is True

        # Should not be discovery nodes
        assert EnumTypeName.is_discovery_node(EnumTypeName.CONTRACT_TO_MODEL) is False
        assert EnumTypeName.is_discovery_node(EnumTypeName.TEMPLATE_ENGINE) is False
        assert EnumTypeName.is_discovery_node(EnumTypeName.CLI_COMMANDS) is False

    def test_is_schema_node(self):
        """Test is_schema_node classification method."""
        # Should be schema nodes
        assert EnumTypeName.is_schema_node(EnumTypeName.SCHEMA_GENERATOR) is True
        assert EnumTypeName.is_schema_node(EnumTypeName.SCHEMA_DISCOVERY) is True
        assert EnumTypeName.is_schema_node(EnumTypeName.SCHEMA_TO_PYDANTIC) is True
        assert EnumTypeName.is_schema_node(EnumTypeName.PROTOCOL_GENERATOR) is True

        # Should not be schema nodes
        assert EnumTypeName.is_schema_node(EnumTypeName.CONTRACT_TO_MODEL) is False
        assert EnumTypeName.is_schema_node(EnumTypeName.TEMPLATE_ENGINE) is False
        assert EnumTypeName.is_schema_node(EnumTypeName.CLI_COMMANDS) is False

    def test_is_runtime_node(self):
        """Test is_runtime_node classification method."""
        # Should be runtime nodes
        assert EnumTypeName.is_runtime_node(EnumTypeName.BACKEND_SELECTION) is True
        assert EnumTypeName.is_runtime_node(EnumTypeName.NODE_MANAGER_RUNNER) is True
        assert EnumTypeName.is_runtime_node(EnumTypeName.MAINTENANCE) is True

        # Should not be runtime nodes
        assert EnumTypeName.is_runtime_node(EnumTypeName.CONTRACT_TO_MODEL) is False
        assert EnumTypeName.is_runtime_node(EnumTypeName.TEMPLATE_ENGINE) is False
        assert EnumTypeName.is_runtime_node(EnumTypeName.CLI_COMMANDS) is False

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        assert EnumTypeName.CONTRACT_TO_MODEL == EnumTypeName.CONTRACT_TO_MODEL
        assert EnumTypeName.CONTRACT_TO_MODEL != EnumTypeName.TEMPLATE_ENGINE
        assert EnumTypeName.CONTRACT_TO_MODEL == "CONTRACT_TO_MODEL"
        assert EnumTypeName.TEMPLATE_ENGINE != "CONTRACT_TO_MODEL"

    def test_enum_membership(self):
        """Test enum membership checks."""
        assert EnumTypeName.CONTRACT_TO_MODEL in EnumTypeName
        assert EnumTypeName.TEMPLATE_ENGINE in EnumTypeName
        assert EnumTypeName.VALIDATION_ENGINE in EnumTypeName

    def test_enum_iteration(self):
        """Test iteration over enum values."""
        type_names = list(EnumTypeName)
        # Should have all defined type names
        assert len(type_names) > 0
        assert EnumTypeName.CONTRACT_TO_MODEL in type_names
        assert EnumTypeName.TEMPLATE_ENGINE in type_names
        assert EnumTypeName.VALIDATION_ENGINE in type_names

    def test_json_serialization(self):
        """Test JSON serialization of enum values."""
        assert json.dumps(EnumTypeName.CONTRACT_TO_MODEL) == '"CONTRACT_TO_MODEL"'
        assert json.dumps(EnumTypeName.TEMPLATE_ENGINE) == '"TEMPLATE_ENGINE"'

    def test_pydantic_model_integration(self):
        """Test Pydantic model integration with enum."""

        class NodeConfig(BaseModel):
            type_name: EnumTypeName

        # Test valid enum value
        config = NodeConfig(type_name=EnumTypeName.CONTRACT_TO_MODEL)
        assert config.type_name == EnumTypeName.CONTRACT_TO_MODEL

        # Test valid string value
        config = NodeConfig(type_name="TEMPLATE_ENGINE")
        assert config.type_name == EnumTypeName.TEMPLATE_ENGINE

        # Test invalid value
        with pytest.raises(ValidationError):
            NodeConfig(type_name="INVALID_TYPE")

    def test_enum_uniqueness(self):
        """Test that all enum values are unique."""
        values = [type_name.value for type_name in EnumTypeName]
        assert len(values) == len(set(values))

    def test_node_categorization_mutually_exclusive(self):
        """Test that node categorization methods are mutually exclusive."""
        for type_name in EnumTypeName:
            categories = [
                EnumTypeName.is_generation_node(type_name),
                EnumTypeName.is_template_node(type_name),
                EnumTypeName.is_validation_node(type_name),
                EnumTypeName.is_cli_node(type_name),
                EnumTypeName.is_discovery_node(type_name),
                EnumTypeName.is_schema_node(type_name),
                EnumTypeName.is_runtime_node(type_name),
            ]
            # Each type should belong to at most one category
            assert sum(categories) <= 1, f"{type_name} belongs to multiple categories"


@pytest.mark.unit
class TestEnumTypeNameEdgeCases:
    """Test edge cases for EnumTypeName."""

    def test_case_sensitivity(self):
        """Test that enum values are case-sensitive."""

        class NodeConfig(BaseModel):
            type_name: EnumTypeName

        # Exact case should work
        config = NodeConfig(type_name="CONTRACT_TO_MODEL")
        assert config.type_name == EnumTypeName.CONTRACT_TO_MODEL

        # Different case should fail
        with pytest.raises(ValidationError):
            NodeConfig(type_name="contract_to_model")

        with pytest.raises(ValidationError):
            NodeConfig(type_name="Contract_To_Model")

    def test_whitespace_handling(self):
        """Test that whitespace in values is rejected."""

        class NodeConfig(BaseModel):
            type_name: EnumTypeName

        with pytest.raises(ValidationError):
            NodeConfig(type_name=" CONTRACT_TO_MODEL")

        with pytest.raises(ValidationError):
            NodeConfig(type_name="CONTRACT_TO_MODEL ")

    def test_all_nodes_have_category(self):
        """Test that all nodes can be classified into at least one category."""
        uncategorized = []
        for type_name in EnumTypeName:
            is_categorized = (
                EnumTypeName.is_generation_node(type_name)
                or EnumTypeName.is_template_node(type_name)
                or EnumTypeName.is_validation_node(type_name)
                or EnumTypeName.is_cli_node(type_name)
                or EnumTypeName.is_discovery_node(type_name)
                or EnumTypeName.is_schema_node(type_name)
                or EnumTypeName.is_runtime_node(type_name)
            )
            if not is_categorized:
                uncategorized.append(type_name)

        # Some nodes may be uncategorized (e.g., logging, testing)
        # This test documents which ones are uncategorized
        expected_uncategorized = {
            EnumTypeName.NODE_LOGGER_EMIT_LOG_EVENT,
            EnumTypeName.LOGGING_UTILS,
            EnumTypeName.SCENARIO_RUNNER,
        }
        assert set(uncategorized) == expected_uncategorized
