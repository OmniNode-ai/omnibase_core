"""
Unit tests for ModelNodeType.

Tests all aspects of the node type model including:
- Model instantiation and validation
- Field validation and type checking
- Factory methods for all node types
- Serialization/deserialization
- Edge cases and error conditions
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.nodes.model_node_type import ModelNodeType


class TestModelNodeType:
    """Test cases for ModelNodeType."""

    def test_model_instantiation_minimal_data(self):
        """Test that model can be instantiated with minimal required data."""
        node_type = ModelNodeType(
            name="TEST_NODE", description="Test node description", category="testing"
        )

        assert node_type.name == "TEST_NODE"
        assert node_type.description == "Test node description"
        assert node_type.category == "testing"
        assert node_type.dependencies == []
        assert node_type.version_compatibility == ">=1.0.0"
        assert node_type.execution_priority == 50
        assert node_type.is_generator is False
        assert node_type.is_validator is False
        assert node_type.requires_contract is False
        assert node_type.output_type is None

    def test_model_instantiation_with_all_fields(self):
        """Test model instantiation with all fields provided."""
        node_type = ModelNodeType(
            name="CUSTOM_NODE",
            description="Custom node with all fields",
            category="custom_category",
            dependencies=["NODE_A", "NODE_B"],
            version_compatibility=">=2.0.0",
            execution_priority=75,
            is_generator=True,
            is_validator=True,
            requires_contract=True,
            output_type="custom_output",
        )

        assert node_type.name == "CUSTOM_NODE"
        assert node_type.description == "Custom node with all fields"
        assert node_type.category == "custom_category"
        assert node_type.dependencies == ["NODE_A", "NODE_B"]
        assert node_type.version_compatibility == ">=2.0.0"
        assert node_type.execution_priority == 75
        assert node_type.is_generator is True
        assert node_type.is_validator is True
        assert node_type.requires_contract is True
        assert node_type.output_type == "custom_output"

    def test_required_fields_validation(self):
        """Test that required fields are properly validated."""
        # Missing name
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeType(description="Test description", category="testing")
        assert "name" in str(exc_info.value)

        # Missing description
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeType(name="TEST_NODE", category="testing")
        assert "description" in str(exc_info.value)

        # Missing category
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeType(name="TEST_NODE", description="Test description")
        assert "category" in str(exc_info.value)

    def test_name_pattern_validation(self):
        """Test that name follows the required pattern."""
        # Valid patterns
        valid_names = ["A", "TEST_NODE", "CONTRACT_TO_MODEL", "NODE123", "A_B_C_123"]

        for name in valid_names:
            node_type = ModelNodeType(
                name=name, description="Test description", category="testing"
            )
            assert node_type.name == name

        # Invalid patterns
        invalid_names = [
            "lowercase",  # Starts with lowercase
            "123NODE",  # Starts with number
            "_UNDERSCORE",  # Starts with underscore
            "node-name",  # Contains hyphen
            "node.name",  # Contains dot
            "node name",  # Contains space
            "",  # Empty string
            "a",  # Lowercase letter
        ]

        for name in invalid_names:
            with pytest.raises(ValidationError) as exc_info:
                ModelNodeType(
                    name=name, description="Test description", category="testing"
                )
            assert "pattern" in str(
                exc_info.value
            ).lower() or "string_pattern_mismatch" in str(exc_info.value)

    def test_category_pattern_validation(self):
        """Test that category follows the required pattern."""
        # Valid patterns
        valid_categories = [
            "a",
            "test",
            "generation",
            "test_category",
            "category123",
            "a_b_c_123",
        ]

        for category in valid_categories:
            node_type = ModelNodeType(
                name="TEST_NODE", description="Test description", category=category
            )
            assert node_type.category == category

        # Invalid patterns
        invalid_categories = [
            "Uppercase",  # Starts with uppercase
            "123category",  # Starts with number
            "_underscore",  # Starts with underscore
            "cat-egory",  # Contains hyphen
            "cat.egory",  # Contains dot
            "cat egory",  # Contains space
            "",  # Empty string
        ]

        for category in invalid_categories:
            with pytest.raises(ValidationError) as exc_info:
                ModelNodeType(
                    name="TEST_NODE", description="Test description", category=category
                )
            assert "pattern" in str(
                exc_info.value
            ).lower() or "string_pattern_mismatch" in str(exc_info.value)

    def test_execution_priority_validation(self):
        """Test that execution_priority is validated within range."""
        # Valid range
        node_type = ModelNodeType(
            name="TEST_NODE",
            description="Test description",
            category="testing",
            execution_priority=75,
        )
        assert node_type.execution_priority == 75

        # Minimum boundary
        node_type = ModelNodeType(
            name="TEST_NODE",
            description="Test description",
            category="testing",
            execution_priority=0,
        )
        assert node_type.execution_priority == 0

        # Maximum boundary
        node_type = ModelNodeType(
            name="TEST_NODE",
            description="Test description",
            category="testing",
            execution_priority=100,
        )
        assert node_type.execution_priority == 100

        # Below minimum
        with pytest.raises(ValidationError):
            ModelNodeType(
                name="TEST_NODE",
                description="Test description",
                category="testing",
                execution_priority=-1,
            )

        # Above maximum
        with pytest.raises(ValidationError):
            ModelNodeType(
                name="TEST_NODE",
                description="Test description",
                category="testing",
                execution_priority=101,
            )

    def test_field_types_validation(self):
        """Test that field types are properly validated."""
        # Test non-string name
        with pytest.raises(ValidationError):
            ModelNodeType(name=123, description="Test description", category="testing")

        # Test non-string description
        with pytest.raises(ValidationError):
            ModelNodeType(name="TEST_NODE", description=123, category="testing")

        # Test non-string category
        with pytest.raises(ValidationError):
            ModelNodeType(
                name="TEST_NODE", description="Test description", category=123
            )

        # Test non-list dependencies
        with pytest.raises(ValidationError):
            ModelNodeType(
                name="TEST_NODE",
                description="Test description",
                category="testing",
                dependencies="not_a_list",
            )

        # Test non-boolean flags (Pydantic converts "true" to True)
        node_type = ModelNodeType(
            name="TEST_NODE",
            description="Test description",
            category="testing",
            is_generator="true",  # Pydantic converts to True
        )
        assert node_type.is_generator is True

    def test_factory_method_contract_to_model(self):
        """Test the CONTRACT_TO_MODEL factory method."""
        node_type = ModelNodeType.CONTRACT_TO_MODEL()

        assert node_type.name == "CONTRACT_TO_MODEL"
        assert "contract.yaml" in node_type.description.lower()
        assert node_type.category == "generation"
        assert node_type.is_generator is True
        assert node_type.requires_contract is True
        assert node_type.output_type == "models"
        assert node_type.is_validator is False

    def test_factory_method_multi_doc_model_generator(self):
        """Test the MULTI_DOC_MODEL_GENERATOR factory method."""
        node_type = ModelNodeType.MULTI_DOC_MODEL_GENERATOR()

        assert node_type.name == "MULTI_DOC_MODEL_GENERATOR"
        assert "multiple YAML" in node_type.description
        assert node_type.category == "generation"
        assert node_type.is_generator is True
        assert node_type.output_type == "models"

    def test_factory_method_generate_error_codes(self):
        """Test the GENERATE_ERROR_CODES factory method."""
        node_type = ModelNodeType.GENERATE_ERROR_CODES()

        assert node_type.name == "GENERATE_ERROR_CODES"
        assert "error code" in node_type.description.lower()
        assert node_type.category == "generation"
        assert node_type.is_generator is True
        assert node_type.requires_contract is True
        assert node_type.output_type == "enums"

    def test_factory_method_validation_engine(self):
        """Test the VALIDATION_ENGINE factory method."""
        node_type = ModelNodeType.VALIDATION_ENGINE()

        assert node_type.name == "VALIDATION_ENGINE"
        assert "validates" in node_type.description.lower()
        assert node_type.category == "validation"
        assert node_type.is_validator is True
        assert node_type.requires_contract is True
        assert node_type.execution_priority == 80
        assert node_type.output_type == "report"

    def test_factory_method_node_generator(self):
        """Test the NODE_GENERATOR factory method."""
        node_type = ModelNodeType.NODE_GENERATOR()

        assert node_type.name == "NODE_GENERATOR"
        assert "complete node structure" in node_type.description
        assert node_type.category == "generation"
        assert node_type.is_generator is True
        assert node_type.execution_priority == 90
        assert node_type.output_type == "node"

    def test_factory_method_template_engine(self):
        """Test the TEMPLATE_ENGINE factory method."""
        node_type = ModelNodeType.TEMPLATE_ENGINE()

        assert node_type.name == "TEMPLATE_ENGINE"
        assert "template" in node_type.description.lower()
        assert node_type.category == "template"
        assert node_type.is_generator is True
        assert node_type.output_type == "text"

    def test_factory_method_file_generator(self):
        """Test the FILE_GENERATOR factory method."""
        node_type = ModelNodeType.FILE_GENERATOR()

        assert node_type.name == "FILE_GENERATOR"
        assert "files from templates" in node_type.description
        assert node_type.category == "template"
        assert node_type.is_generator is True
        assert "TEMPLATE_ENGINE" in node_type.dependencies
        assert node_type.output_type == "files"

    def test_factory_method_standards_compliance_fixer(self):
        """Test the STANDARDS_COMPLIANCE_FIXER factory method."""
        node_type = ModelNodeType.STANDARDS_COMPLIANCE_FIXER()

        assert node_type.name == "STANDARDS_COMPLIANCE_FIXER"
        assert "ONEX standards" in node_type.description
        assert node_type.category == "maintenance"
        assert node_type.is_generator is True
        assert node_type.is_validator is True
        assert node_type.output_type == "fixes"

    def test_factory_method_node_discovery(self):
        """Test the NODE_DISCOVERY factory method."""
        node_type = ModelNodeType.NODE_DISCOVERY()

        assert node_type.name == "NODE_DISCOVERY"
        assert "discovers nodes" in node_type.description.lower()
        assert node_type.category == "discovery"
        assert node_type.execution_priority == 95
        assert node_type.output_type == "nodes"

    def test_factory_method_node_manager_runner(self):
        """Test the NODE_MANAGER_RUNNER factory method."""
        node_type = ModelNodeType.NODE_MANAGER_RUNNER()

        assert node_type.name == "NODE_MANAGER_RUNNER"
        assert "node manager" in node_type.description.lower()
        assert node_type.category == "runtime"
        assert node_type.execution_priority == 100
        assert node_type.output_type == "result"

    def test_factory_method_logger_emit_log_event(self):
        """Test the LOGGER_EMIT_LOG_EVENT factory method."""
        # This factory method uses a name that doesn't match the pattern
        # So it should raise ValidationError
        with pytest.raises(ValidationError):
            ModelNodeType.LOGGER_EMIT_LOG_EVENT()

    def test_factory_method_scenario_runner(self):
        """Test the SCENARIO_RUNNER factory method."""
        # This factory method uses a name that doesn't match the pattern
        # So it should raise ValidationError
        with pytest.raises(ValidationError):
            ModelNodeType.SCENARIO_RUNNER()

    def test_from_string_method_known_types(self):
        """Test the from_string method with known node types."""
        # Test a few key node types
        test_cases = [
            ("CONTRACT_TO_MODEL", "generation"),
            ("VALIDATION_ENGINE", "validation"),
            ("NODE_DISCOVERY", "discovery"),
            ("TEMPLATE_ENGINE", "template"),
            ("CLI_COMMANDS", "cli"),
        ]

        for name, expected_category in test_cases:
            node_type = ModelNodeType.from_string(name)
            assert node_type.name == name
            assert node_type.category == expected_category

    def test_from_string_method_unknown_type(self):
        """Test the from_string method with unknown node type."""
        node_type = ModelNodeType.from_string("UNKNOWN_NODE_TYPE")

        assert node_type.name == "UNKNOWN_NODE_TYPE"
        assert node_type.description == "Node: UNKNOWN_NODE_TYPE"
        assert node_type.category == "unknown"

    def test_string_representation(self):
        """Test the string representation of the model."""
        node_type = ModelNodeType.CONTRACT_TO_MODEL()
        assert str(node_type) == "CONTRACT_TO_MODEL"

        custom_node = ModelNodeType(
            name="CUSTOM_NODE", description="Custom description", category="custom"
        )
        assert str(custom_node) == "CUSTOM_NODE"

    def test_equality_comparison(self):
        """Test equality comparison methods."""
        node_type1 = ModelNodeType.CONTRACT_TO_MODEL()
        node_type2 = ModelNodeType.CONTRACT_TO_MODEL()
        node_type3 = ModelNodeType.VALIDATION_ENGINE()

        # Same type instances should be equal
        assert node_type1 == node_type2

        # Different types should not be equal
        assert node_type1 != node_type3

        # String comparison should work
        assert node_type1 == "CONTRACT_TO_MODEL"
        assert node_type1 != "VALIDATION_ENGINE"

        # Comparison with other types should return False
        assert node_type1 != 123
        assert node_type1 != None
        assert node_type1 != ["CONTRACT_TO_MODEL"]

    def test_model_serialization(self):
        """Test model serialization to dict."""
        node_type = ModelNodeType(
            name="TEST_NODE",
            description="Test node for serialization",
            category="testing",
            dependencies=["DEP_A", "DEP_B"],
            version_compatibility=">=1.5.0",
            execution_priority=75,
            is_generator=True,
            is_validator=False,
            requires_contract=True,
            output_type="test_output",
        )

        data = node_type.model_dump()

        expected_data = {
            "name": "TEST_NODE",
            "description": "Test node for serialization",
            "category": "testing",
            "dependencies": ["DEP_A", "DEP_B"],
            "version_compatibility": ">=1.5.0",
            "execution_priority": 75,
            "is_generator": True,
            "is_validator": False,
            "requires_contract": True,
            "output_type": "test_output",
        }

        assert data == expected_data

    def test_model_deserialization(self):
        """Test model deserialization from dict."""
        data = {
            "name": "DESERIALIZED_NODE",
            "description": "Node created from dict",
            "category": "deserialization",
            "dependencies": ["NODE_X", "NODE_Y"],
            "version_compatibility": ">=2.0.0",
            "execution_priority": 85,
            "is_generator": False,
            "is_validator": True,
            "requires_contract": False,
            "output_type": "analysis",
        }

        node_type = ModelNodeType.model_validate(data)

        assert node_type.name == "DESERIALIZED_NODE"
        assert node_type.description == "Node created from dict"
        assert node_type.category == "deserialization"
        assert node_type.dependencies == ["NODE_X", "NODE_Y"]
        assert node_type.version_compatibility == ">=2.0.0"
        assert node_type.execution_priority == 85
        assert node_type.is_generator is False
        assert node_type.is_validator is True
        assert node_type.requires_contract is False
        assert node_type.output_type == "analysis"

    def test_model_json_serialization(self):
        """Test JSON serialization and deserialization."""
        node_type = ModelNodeType.VALIDATION_ENGINE()

        # Serialize to JSON
        json_str = node_type.model_dump_json()
        assert isinstance(json_str, str)

        # Deserialize from JSON
        node_type_from_json = ModelNodeType.model_validate_json(json_str)

        assert node_type_from_json.name == node_type.name
        assert node_type_from_json.description == node_type.description
        assert node_type_from_json.category == node_type.category
        assert node_type_from_json.is_validator == node_type.is_validator
        assert node_type_from_json.requires_contract == node_type.requires_contract

    def test_all_factory_methods_coverage(self):
        """Test that all factory methods defined in from_string are callable."""
        # Valid factory method names that should work
        valid_factory_names = [
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
            "LOGGING_UTILS",
        ]

        # Test that each valid factory method works
        for name in valid_factory_names:
            node_type = ModelNodeType.from_string(name)
            assert node_type.name == name
            assert isinstance(node_type.description, str)
            assert isinstance(node_type.category, str)
            assert node_type.description != ""
            assert node_type.category != ""

        # Names that don't match the pattern but are in factory map - should raise ValidationError
        invalid_pattern_names = [
            "node_logger_emit_log_event",
            "scenario_runner",
        ]

        for name in invalid_pattern_names:
            with pytest.raises(ValidationError):
                ModelNodeType.from_string(name)

        # Names not in factory map should create generic nodes (but must follow name pattern)
        unknown_names = ["UNKNOWN_NODE_TYPE", "CUSTOM_PROCESSOR", "SPECIAL_HANDLER"]

        for name in unknown_names:
            node_type = ModelNodeType.from_string(name)
            assert node_type.name == name
            assert node_type.description == f"Node: {name}"
            assert node_type.category == "unknown"


class TestModelNodeTypeEdgeCases:
    """Test edge cases and error conditions for ModelNodeType."""

    def test_empty_string_fields(self):
        """Test behavior with empty string fields."""
        # Empty name should fail pattern validation
        with pytest.raises(ValidationError):
            ModelNodeType(name="", description="Test description", category="testing")

        # Empty description should be valid (no min_length constraint)
        node_type = ModelNodeType(name="TEST_NODE", description="", category="testing")
        assert node_type.description == ""

        # Empty category should fail pattern validation
        with pytest.raises(ValidationError):
            ModelNodeType(name="TEST_NODE", description="Test description", category="")

    def test_whitespace_handling(self):
        """Test handling of whitespace in fields."""
        # Valid with whitespace in description
        node_type = ModelNodeType(
            name="TEST_NODE",
            description="  Description with spaces  ",
            category="testing",
        )
        assert node_type.description == "  Description with spaces  "

        # Whitespace in name should fail pattern validation
        with pytest.raises(ValidationError):
            ModelNodeType(
                name=" TEST_NODE ", description="Test description", category="testing"
            )

        # Whitespace in category should fail pattern validation
        with pytest.raises(ValidationError):
            ModelNodeType(
                name="TEST_NODE", description="Test description", category=" testing "
            )

    def test_unicode_characters(self):
        """Test handling of unicode characters."""
        # Unicode in description should work
        node_type = ModelNodeType(
            name="TEST_NODE",
            description="Descripción with ñ and émojis 🚀",
            category="testing",
        )
        assert "ñ" in node_type.description
        assert "🚀" in node_type.description

        # Unicode in output_type should work
        node_type = ModelNodeType(
            name="TEST_NODE",
            description="Test description",
            category="testing",
            output_type="ütput_type_ñ",
        )
        assert node_type.output_type == "ütput_type_ñ"

    def test_very_long_strings(self):
        """Test handling of very long strings."""
        long_description = "a" * 10000
        long_output_type = "b" * 1000

        node_type = ModelNodeType(
            name="TEST_NODE",
            description=long_description,
            category="testing",
            output_type=long_output_type,
        )

        assert len(node_type.description) == 10000
        assert len(node_type.output_type) == 1000

    def test_none_values_for_optional_fields(self):
        """Test explicit None values for optional fields."""
        node_type = ModelNodeType(
            name="TEST_NODE",
            description="Test description",
            category="testing",
            output_type=None,
        )

        assert node_type.output_type is None

    def test_large_priority_values(self):
        """Test edge cases with priority values."""
        # Test exact boundary values
        node_type = ModelNodeType(
            name="TEST_NODE",
            description="Test description",
            category="testing",
            execution_priority=0,
        )
        assert node_type.execution_priority == 0

        node_type = ModelNodeType(
            name="TEST_NODE",
            description="Test description",
            category="testing",
            execution_priority=100,
        )
        assert node_type.execution_priority == 100

    def test_complex_dependencies(self):
        """Test complex dependency scenarios."""
        # Large number of dependencies
        many_deps = [f"NODE_{i}" for i in range(100)]
        node_type = ModelNodeType(
            name="TEST_NODE",
            description="Test description",
            category="testing",
            dependencies=many_deps,
        )
        assert len(node_type.dependencies) == 100

        # Empty dependencies list
        node_type = ModelNodeType(
            name="TEST_NODE",
            description="Test description",
            category="testing",
            dependencies=[],
        )
        assert node_type.dependencies == []

        # Dependencies with special characters
        special_deps = ["NODE_WITH_123", "NODE_WITH_UNDERSCORES_LONG"]
        node_type = ModelNodeType(
            name="TEST_NODE",
            description="Test description",
            category="testing",
            dependencies=special_deps,
        )
        assert node_type.dependencies == special_deps

    def test_version_compatibility_edge_cases(self):
        """Test edge cases for version compatibility."""
        # Complex version constraints
        version_constraints = [">=1.0.0", "~1.2.3", "^2.0.0", "1.0.0 - 2.0.0", "*"]

        for constraint in version_constraints:
            node_type = ModelNodeType(
                name="TEST_NODE",
                description="Test description",
                category="testing",
                version_compatibility=constraint,
            )
            assert node_type.version_compatibility == constraint


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
