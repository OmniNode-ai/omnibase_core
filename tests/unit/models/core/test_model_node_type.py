"""
Unit tests for ModelNodeType.

Tests all aspects of the node type model including:
- Model instantiation and validation
- Field validation and type checking
- Factory methods for all node types
- Serialization/deserialization
- Edge cases and error conditions
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_config_category import EnumConfigCategory
from omnibase_core.enums.enum_return_type import EnumReturnType
from omnibase_core.enums.enum_type_name import EnumTypeName
from omnibase_core.models.errors.model_onex_error import ModelOnexError as OnexError
from omnibase_core.models.node_metadata import ModelNodeType
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


class TestModelNodeType:
    """Test cases for ModelNodeType."""

    def test_model_instantiation_minimal_data(self):
        """Test that model can be instantiated with minimal required data."""
        node_type = ModelNodeType(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="Test node description",
            category=EnumConfigCategory.TESTING,
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
        )

        assert node_type.type_name == EnumTypeName.CONTRACT_TO_MODEL
        assert node_type.description == "Test node description"
        assert node_type.category == EnumConfigCategory.TESTING
        assert node_type.dependencies == []
        # version_compatibility is now ModelSemVer, not string
        assert node_type.version_compatibility == ModelSemVer(major=1, minor=0, patch=0)
        assert node_type.execution_priority == 50
        assert node_type.is_generator is False
        assert node_type.is_validator is False
        assert node_type.requires_contract is False
        assert node_type.output_type is None

    def test_model_instantiation_with_all_fields(self):
        """Test model instantiation with all fields provided."""
        from omnibase_core.models.primitives.model_semver import ModelSemVer

        node_type = ModelNodeType(
            type_name=EnumTypeName.VALIDATION_ENGINE,
            description="Custom node with all fields",
            category=EnumConfigCategory.VALIDATION,
            dependencies=["NODE_A", "NODE_B"],
            version_compatibility=ModelSemVer(major=2, minor=0, patch=0),
            execution_priority=75,
            is_generator=True,
            is_validator=True,
            requires_contract=True,
            output_type=EnumReturnType.TEXT,
        )

        assert node_type.type_name == EnumTypeName.VALIDATION_ENGINE
        assert node_type.description == "Custom node with all fields"
        assert node_type.category == EnumConfigCategory.VALIDATION
        assert node_type.dependencies == ["NODE_A", "NODE_B"]
        assert node_type.version_compatibility == ModelSemVer(major=2, minor=0, patch=0)
        assert node_type.execution_priority == 75
        assert node_type.is_generator is True
        assert node_type.is_validator is True
        assert node_type.requires_contract is True
        assert node_type.output_type == EnumReturnType.TEXT

    def test_required_fields_validation(self):
        """Test that required fields are properly validated."""
        # Missing type_name
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeType(
                description="Test description",
                category=EnumConfigCategory.TESTING,
                version_compatibility=DEFAULT_VERSION,
            )
        assert "type_name" in str(exc_info.value)

        # Missing description
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeType(
                type_name=EnumTypeName.CONTRACT_TO_MODEL,
                category=EnumConfigCategory.TESTING,
                version_compatibility=DEFAULT_VERSION,
            )
        assert "description" in str(exc_info.value)

        # Missing category
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeType(
                type_name=EnumTypeName.CONTRACT_TO_MODEL,
                description="Test description",
                version_compatibility=DEFAULT_VERSION,
            )
        assert "category" in str(exc_info.value)

    def test_name_pattern_validation(self):
        """Test that type_name uses valid enum values."""
        # Valid enum values
        valid_names = [
            EnumTypeName.CONTRACT_TO_MODEL,
            EnumTypeName.VALIDATION_ENGINE,
            EnumTypeName.TEMPLATE_ENGINE,
        ]

        for name in valid_names:
            node_type = ModelNodeType(
                type_name=name,
                description="Test description",
                category=EnumConfigCategory.TESTING,
                version_compatibility=DEFAULT_VERSION,
            )
            assert node_type.type_name == name

        # Invalid strings should raise Pydantic ValidationError (enum type safety)
        invalid_names = [
            "INVALID_NODE",  # Not in enum
            "lowercase",  # Invalid format
            "123NODE",  # Invalid format
            "",  # Empty string
        ]

        for name in invalid_names:
            with pytest.raises(ValidationError):
                ModelNodeType(
                    type_name=name,
                    description="Test description",
                    category=EnumConfigCategory.TESTING,
                    version_compatibility=DEFAULT_VERSION,
                )

    def test_category_pattern_validation(self):
        """Test that category uses valid enum values."""
        # Valid enum categories
        valid_categories = [
            EnumConfigCategory.GENERATION,
            EnumConfigCategory.VALIDATION,
            EnumConfigCategory.TESTING,
            EnumConfigCategory.TEMPLATE,
        ]

        for category in valid_categories:
            node_type = ModelNodeType(
                type_name=EnumTypeName.CONTRACT_TO_MODEL,
                description="Test description",
                category=category,
                version_compatibility=DEFAULT_VERSION,
            )
            assert node_type.category == category

        # Invalid strings should raise Pydantic ValidationError (enum type safety)
        invalid_categories = [
            "INVALID_CATEGORY",  # Not in enum
            "Uppercase",  # Not in enum
            "123category",  # Not in enum
            "",  # Empty string
        ]

        for category in invalid_categories:
            with pytest.raises(ValidationError):
                ModelNodeType(
                    type_name=EnumTypeName.CONTRACT_TO_MODEL,
                    description="Test description",
                    category=category,
                    version_compatibility=DEFAULT_VERSION,
                )

    def test_execution_priority_validation(self):
        """Test that execution_priority is validated within range."""
        # Valid range
        node_type = ModelNodeType(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="Test description",
            category=EnumConfigCategory.TESTING,
            version_compatibility=DEFAULT_VERSION,
            execution_priority=75,
        )
        assert node_type.execution_priority == 75

        # Minimum boundary
        node_type = ModelNodeType(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="Test description",
            category=EnumConfigCategory.TESTING,
            version_compatibility=DEFAULT_VERSION,
            execution_priority=0,
        )
        assert node_type.execution_priority == 0

        # Maximum boundary
        node_type = ModelNodeType(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="Test description",
            category=EnumConfigCategory.TESTING,
            version_compatibility=DEFAULT_VERSION,
            execution_priority=100,
        )
        assert node_type.execution_priority == 100

        # Below minimum
        with pytest.raises(ValidationError):
            ModelNodeType(
                type_name=EnumTypeName.CONTRACT_TO_MODEL,
                description="Test description",
                category=EnumConfigCategory.TESTING,
                version_compatibility=DEFAULT_VERSION,
                execution_priority=-1,
            )

        # Above maximum
        with pytest.raises(ValidationError):
            ModelNodeType(
                type_name=EnumTypeName.CONTRACT_TO_MODEL,
                description="Test description",
                category=EnumConfigCategory.TESTING,
                version_compatibility=DEFAULT_VERSION,
                execution_priority=101,
            )

    def test_field_types_validation(self):
        """Test that field types are properly validated."""
        # Test non-string type_name - Pydantic's built-in validation catches this first
        with pytest.raises(ValidationError):
            ModelNodeType(
                type_name=123,
                description="Test description",
                category=EnumConfigCategory.TESTING,
                version_compatibility=DEFAULT_VERSION,
            )

        # Test non-string description
        with pytest.raises(ValidationError):
            ModelNodeType(
                type_name=EnumTypeName.CONTRACT_TO_MODEL,
                description=123,
                category=EnumConfigCategory.TESTING,
                version_compatibility=DEFAULT_VERSION,
            )

        # Test non-string category - Pydantic's built-in validation catches this first
        with pytest.raises(ValidationError):
            ModelNodeType(
                type_name=EnumTypeName.CONTRACT_TO_MODEL,
                description="Test description",
                category=123,
                version_compatibility=DEFAULT_VERSION,
            )

        # Test non-list dependencies - Custom validator catches this
        with pytest.raises(ValidationError):
            ModelNodeType(
                type_name=EnumTypeName.CONTRACT_TO_MODEL,
                description="Test description",
                category=EnumConfigCategory.TESTING,
                version_compatibility=DEFAULT_VERSION,
                dependencies="not_a_list",
            )

        # Test non-boolean flags (Pydantic converts "true" to True)
        node_type = ModelNodeType(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="Test description",
            category=EnumConfigCategory.TESTING,
            version_compatibility=DEFAULT_VERSION,
            is_generator="true",  # Pydantic converts to True
        )
        assert node_type.is_generator is True

    def test_factory_method_contract_to_model(self):
        """Test the CONTRACT_TO_MODEL factory method."""
        node_type = ModelNodeType.CONTRACT_TO_MODEL()

        assert node_type.type_name == "CONTRACT_TO_MODEL"
        assert "contract.yaml" in node_type.description.lower()
        assert node_type.category == "generation"
        assert node_type.is_generator is True
        assert node_type.requires_contract is True
        assert node_type.output_type == EnumReturnType.MODELS
        assert node_type.is_validator is False

    def test_factory_method_multi_doc_model_generator(self):
        """Test the MULTI_DOC_MODEL_GENERATOR factory method."""
        node_type = ModelNodeType.MULTI_DOC_MODEL_GENERATOR()

        assert node_type.type_name == "MULTI_DOC_MODEL_GENERATOR"
        assert "multiple YAML" in node_type.description
        assert node_type.category == "generation"
        assert node_type.is_generator is True
        assert node_type.output_type == EnumReturnType.MODELS

    def test_factory_method_generate_error_codes(self):
        """Test the GENERATE_ERROR_CODES factory method."""
        node_type = ModelNodeType.GENERATE_ERROR_CODES()

        assert node_type.type_name == "GENERATE_ERROR_CODES"
        assert "error code" in node_type.description.lower()
        assert node_type.category == "generation"
        assert node_type.is_generator is True
        assert node_type.requires_contract is True
        assert node_type.output_type == EnumReturnType.ENUMS

    def test_factory_method_validation_engine(self):
        """Test the VALIDATION_ENGINE factory method."""
        node_type = ModelNodeType.VALIDATION_ENGINE()

        assert node_type.type_name == "VALIDATION_ENGINE"
        assert "validates" in node_type.description.lower()
        assert node_type.category == "validation"
        assert node_type.is_validator is True
        assert node_type.requires_contract is True
        assert node_type.execution_priority == 80
        assert node_type.output_type == EnumReturnType.REPORTS

    def test_factory_method_node_generator(self):
        """Test the NODE_GENERATOR factory method."""
        node_type = ModelNodeType.NODE_GENERATOR()

        assert node_type.type_name == "NODE_GENERATOR"
        assert "complete node structure" in node_type.description
        assert node_type.category == "generation"
        assert node_type.is_generator is True
        assert node_type.execution_priority == 90
        assert node_type.output_type == EnumReturnType.METADATA

    def test_factory_method_template_engine(self):
        """Test the TEMPLATE_ENGINE factory method."""
        node_type = ModelNodeType.TEMPLATE_ENGINE()

        assert node_type.type_name == "TEMPLATE_ENGINE"
        assert "template" in node_type.description.lower()
        assert node_type.category == "template"
        assert node_type.is_generator is True
        assert node_type.output_type == EnumReturnType.TEXT

    def test_factory_method_file_generator(self):
        """Test the FILE_GENERATOR factory method."""
        node_type = ModelNodeType.FILE_GENERATOR()

        assert node_type.type_name == "FILE_GENERATOR"
        assert "files from templates" in node_type.description
        assert node_type.category == "template"
        assert node_type.is_generator is True
        assert "TEMPLATE_ENGINE" in node_type.dependencies
        assert node_type.output_type == EnumReturnType.FILES

    def test_factory_method_standards_compliance_fixer(self):
        """Test the STANDARDS_COMPLIANCE_FIXER factory method."""
        node_type = ModelNodeType.STANDARDS_COMPLIANCE_FIXER()

        assert node_type.type_name == "STANDARDS_COMPLIANCE_FIXER"
        assert "ONEX standards" in node_type.description
        assert node_type.category == "maintenance"
        assert node_type.is_generator is True
        assert node_type.is_validator is True
        assert node_type.output_type == EnumReturnType.FILES

    def test_factory_method_node_discovery(self):
        """Test the NODE_DISCOVERY factory method."""
        node_type = ModelNodeType.NODE_DISCOVERY()

        assert node_type.type_name == "NODE_DISCOVERY"
        assert "discovers nodes" in node_type.description.lower()
        assert node_type.category == "discovery"
        assert node_type.execution_priority == 95
        assert node_type.output_type == EnumReturnType.METADATA

    def test_factory_method_node_manager_runner(self):
        """Test the NODE_MANAGER_RUNNER factory method."""
        node_type = ModelNodeType.NODE_MANAGER_RUNNER()

        assert node_type.type_name == "NODE_MANAGER_RUNNER"
        assert "node manager" in node_type.description.lower()
        assert node_type.category == "runtime"
        assert node_type.execution_priority == 100
        assert node_type.output_type == EnumReturnType.RESULT

    def test_factory_method_logger_emit_log_event(self):
        """Test the LOGGER_EMIT_LOG_EVENT factory method."""
        # Now uses proper enum value, should work fine
        node_type = ModelNodeType.LOGGER_EMIT_LOG_EVENT()
        assert node_type.type_name == EnumTypeName.NODE_LOGGER_EMIT_LOG_EVENT
        assert node_type.category == EnumConfigCategory.LOGGING

    def test_factory_method_scenario_runner(self):
        """Test the SCENARIO_RUNNER factory method."""
        # Now uses proper enum value, should work fine
        node_type = ModelNodeType.SCENARIO_RUNNER()
        assert node_type.type_name == EnumTypeName.SCENARIO_RUNNER
        assert node_type.category == EnumConfigCategory.TESTING

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
            assert node_type.type_name == name
            assert node_type.category == expected_category

    def test_from_string_method_unknown_type(self):
        """Test the from_string method with unknown node type raises OnexError."""
        # Unknown types not in the enum should raise OnexError to maintain type safety
        with pytest.raises(OnexError) as exc_info:
            ModelNodeType.from_string("UNKNOWN_NODE_TYPE")

        assert "Unknown node type" in str(exc_info.value)
        assert "UNKNOWN_NODE_TYPE" in str(exc_info.value)

    def test_string_representation(self):
        """Test the string representation of the model."""
        node_type = ModelNodeType.CONTRACT_TO_MODEL()
        assert str(node_type) == "CONTRACT_TO_MODEL"

        custom_node = ModelNodeType(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="Custom description",
            category=EnumConfigCategory.GENERAL,
            version_compatibility=DEFAULT_VERSION,
        )
        assert str(custom_node) == "CONTRACT_TO_MODEL"

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
        from omnibase_core.models.primitives.model_semver import ModelSemVer

        node_type = ModelNodeType(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="Test node for serialization",
            category=EnumConfigCategory.TESTING,
            dependencies=["DEP_A", "DEP_B"],
            version_compatibility=ModelSemVer(major=1, minor=5, patch=0),
            execution_priority=75,
            is_generator=True,
            is_validator=False,
            requires_contract=True,
            output_type=EnumReturnType.TEXT,
        )

        data = node_type.model_dump()

        expected_data = {
            "type_id": node_type.type_id,
            "type_name": "CONTRACT_TO_MODEL",
            "description": "Test node for serialization",
            "category": "testing",
            "dependencies": ["DEP_A", "DEP_B"],
            "version_compatibility": {"major": 1, "minor": 5, "patch": 0},
            "execution_priority": 75,
            "is_generator": True,
            "is_validator": False,
            "requires_contract": True,
            "output_type": EnumReturnType.TEXT,
        }

        assert data == expected_data

    def test_model_deserialization(self):
        """Test model deserialization from dict."""
        from omnibase_core.models.primitives.model_semver import ModelSemVer

        data = {
            "type_name": "VALIDATION_ENGINE",  # Valid EnumTypeName value
            "description": "Node created from dict",
            "category": "validation",  # Valid EnumConfigCategory value
            "dependencies": ["NODE_X", "NODE_Y"],
            "version_compatibility": {"major": 2, "minor": 0, "patch": 0},
            "execution_priority": 85,
            "is_generator": False,
            "is_validator": True,
            "requires_contract": False,
            "output_type": "REPORTS",  # EnumReturnType value as string
        }

        node_type = ModelNodeType.model_validate(data)

        # Verify deserialized values are proper enum types
        assert node_type.type_name == EnumTypeName.VALIDATION_ENGINE
        assert node_type.description == "Node created from dict"
        assert node_type.category == EnumConfigCategory.VALIDATION
        assert node_type.dependencies == ["NODE_X", "NODE_Y"]
        assert node_type.version_compatibility == ModelSemVer(major=2, minor=0, patch=0)
        assert node_type.execution_priority == 85
        assert node_type.is_generator is False
        assert node_type.is_validator is True
        assert node_type.requires_contract is False
        assert node_type.output_type == EnumReturnType.REPORTS

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

    def test_get_id_returns_type_id(self):
        """Test that get_id() returns str(type_id) for Identifiable protocol compliance."""
        # Create a node with a known type_id
        known_type_id = uuid4()
        node_type = ModelNodeType(
            type_id=known_type_id,
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="Test node for ID verification",
            category=EnumConfigCategory.TESTING,
            version_compatibility=DEFAULT_VERSION,
        )

        # Verify get_id() returns str(type_id)
        result_id = node_type.get_id()
        assert result_id == str(known_type_id)
        assert isinstance(result_id, str)

        # Verify it's a valid UUID string
        from uuid import UUID

        UUID(result_id)  # Should not raise ValueError

    def test_get_id_stable_across_calls(self):
        """Test that get_id() returns stable value across multiple calls."""
        node_type = ModelNodeType(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="Test node for ID stability",
            category=EnumConfigCategory.TESTING,
            version_compatibility=DEFAULT_VERSION,
        )

        # Call get_id() multiple times
        id1 = node_type.get_id()
        id2 = node_type.get_id()
        id3 = node_type.get_id()

        # All calls should return the same value
        assert id1 == id2 == id3
        assert id1 == str(node_type.type_id)

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
            assert node_type.type_name == name
            assert isinstance(node_type.description, str)
            assert isinstance(node_type.category, str)
            assert node_type.description != ""
            assert node_type.category != ""

        # Names that don't match the pattern and are not in factory map - should raise OnexError
        invalid_pattern_names = [
            "node_logger_emit_log_event",
            "scenario_runner",
        ]

        for name in invalid_pattern_names:
            with pytest.raises(OnexError):
                ModelNodeType.from_string(name)

        # Names not in factory map and not in EnumTypeName - should raise OnexError
        # This maintains type safety by enforcing strict enum values
        unknown_names = ["UNKNOWN_NODE_TYPE", "CUSTOM_PROCESSOR", "SPECIAL_HANDLER"]

        for name in unknown_names:
            with pytest.raises(OnexError) as exc_info:
                ModelNodeType.from_string(name)
            assert "Unknown node type" in str(exc_info.value)


class TestModelNodeTypeEdgeCases:
    """Test edge cases and error conditions for ModelNodeType."""

    def test_empty_string_fields(self):
        """Test behavior with empty string fields."""
        # Empty name should fail pattern validation
        with pytest.raises(ValidationError):
            ModelNodeType(
                type_name="",
                description="Test description",
                category=EnumConfigCategory.TESTING,
                version_compatibility=DEFAULT_VERSION,
            )

        # Empty description should be valid (no min_length constraint)
        node_type = ModelNodeType(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="",
            category=EnumConfigCategory.TESTING,
            version_compatibility=DEFAULT_VERSION,
        )
        assert node_type.description == ""

        # Empty category should fail pattern validation
        with pytest.raises(ValidationError):
            ModelNodeType(
                type_name=EnumTypeName.CONTRACT_TO_MODEL,
                description="Test description",
                category="",
                version_compatibility=DEFAULT_VERSION,
            )

    def test_whitespace_handling(self):
        """Test handling of whitespace in fields."""
        # Valid with whitespace in description
        node_type = ModelNodeType(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="  Description with spaces  ",
            category=EnumConfigCategory.TESTING,
            version_compatibility=DEFAULT_VERSION,
        )
        assert node_type.description == "  Description with spaces  "

        # Whitespace in name should fail pattern validation
        with pytest.raises(ValidationError):
            ModelNodeType(
                type_name=" TEST_NODE ",
                description="Test description",
                category=EnumConfigCategory.TESTING,
                version_compatibility=DEFAULT_VERSION,
            )

        # Whitespace in category should fail pattern validation
        with pytest.raises(ValidationError):
            ModelNodeType(
                type_name=EnumTypeName.CONTRACT_TO_MODEL,
                description="Test description",
                category=" testing ",
                version_compatibility=DEFAULT_VERSION,
            )

    def test_unicode_characters(self):
        """Test handling of unicode characters."""
        # Unicode in description should work
        node_type = ModelNodeType(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="Descripcion with n and emojis",
            category=EnumConfigCategory.TESTING,
            version_compatibility=DEFAULT_VERSION,
        )
        assert "Descripcion" in node_type.description

        # Unicode in output_type (use valid enum value)
        node_type = ModelNodeType(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="Test description",
            category=EnumConfigCategory.TESTING,
            version_compatibility=DEFAULT_VERSION,
            output_type=EnumReturnType.TEXT,
        )
        assert node_type.output_type == EnumReturnType.TEXT

    def test_very_long_strings(self):
        """Test handling of very long strings."""
        long_description = "a" * 10000

        node_type = ModelNodeType(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description=long_description,
            category=EnumConfigCategory.TESTING,
            version_compatibility=DEFAULT_VERSION,
            output_type=EnumReturnType.TEXT,
        )

        assert len(node_type.description) == 10000
        assert node_type.output_type == EnumReturnType.TEXT

    def test_none_values_for_optional_fields(self):
        """Test explicit None values for optional fields."""
        node_type = ModelNodeType(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="Test description",
            category=EnumConfigCategory.TESTING,
            version_compatibility=DEFAULT_VERSION,
            output_type=None,
        )

        assert node_type.output_type is None

    def test_large_priority_values(self):
        """Test edge cases with priority values."""
        # Test exact boundary values
        node_type = ModelNodeType(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="Test description",
            category=EnumConfigCategory.TESTING,
            version_compatibility=DEFAULT_VERSION,
            execution_priority=0,
        )
        assert node_type.execution_priority == 0

        node_type = ModelNodeType(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="Test description",
            category=EnumConfigCategory.TESTING,
            version_compatibility=DEFAULT_VERSION,
            execution_priority=100,
        )
        assert node_type.execution_priority == 100

    def test_complex_dependencies(self):
        """Test complex dependency scenarios."""
        # Large number of dependencies
        many_deps = [f"NODE_{i}" for i in range(100)]
        node_type = ModelNodeType(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="Test description",
            category=EnumConfigCategory.TESTING,
            version_compatibility=DEFAULT_VERSION,
            dependencies=many_deps,
        )
        assert len(node_type.dependencies) == 100

        # Empty dependencies list
        node_type = ModelNodeType(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="Test description",
            category=EnumConfigCategory.TESTING,
            version_compatibility=DEFAULT_VERSION,
            dependencies=[],
        )
        assert node_type.dependencies == []

        # Dependencies with special characters
        special_deps = ["NODE_WITH_123", "NODE_WITH_UNDERSCORES_LONG"]
        node_type = ModelNodeType(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="Test description",
            category=EnumConfigCategory.TESTING,
            version_compatibility=DEFAULT_VERSION,
            dependencies=special_deps,
        )
        assert node_type.dependencies == special_deps

    def test_version_compatibility_edge_cases(self):
        """Test edge cases for version compatibility."""
        from omnibase_core.models.primitives.model_semver import ModelSemVer

        # Various version scenarios
        version_scenarios = [
            ModelSemVer(major=1, minor=0, patch=0),
            ModelSemVer(major=1, minor=2, patch=3),
            ModelSemVer(major=2, minor=0, patch=0),
            ModelSemVer(major=3, minor=5, patch=7),
        ]

        for version in version_scenarios:
            node_type = ModelNodeType(
                type_name=EnumTypeName.CONTRACT_TO_MODEL,
                description="Test description",
                category=EnumConfigCategory.TESTING,
                version_compatibility=version,
            )
            assert node_type.version_compatibility == version


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
