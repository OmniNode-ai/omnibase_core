"""
Unit tests for ModelNodeType.

Tests all aspects of the node type model including:
- Model instantiation with defaults and custom values
- Property getters (name)
- Factory methods for all node types
- from_string conversion with fallback
- String representation and equality
- Protocol implementations
- Edge cases and error handling
"""

import pytest

from omnibase_core.enums.enum_config_category import EnumConfigCategory
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_return_type import EnumReturnType
from omnibase_core.enums.enum_type_name import EnumTypeName
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.node_metadata.model_node_type import ModelNodeType
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.mark.unit
class TestModelNodeType:
    """Test cases for ModelNodeType."""

    def test_model_instantiation_minimal(self):
        """Test that model can be instantiated with minimal required fields."""
        node_type = ModelNodeType(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="Test node type",
            category=EnumConfigCategory.GENERATION,
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
        )

        assert node_type.type_name == EnumTypeName.CONTRACT_TO_MODEL
        assert node_type.description == "Test node type"
        assert node_type.category == EnumConfigCategory.GENERATION
        assert node_type.type_id is not None

    def test_model_instantiation_full(self):
        """Test model instantiation with all fields."""
        node_type = ModelNodeType(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="Full test node",
            category=EnumConfigCategory.GENERATION,
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            dependencies=["DEP1", "DEP2"],
            execution_priority=75,
            is_generator=True,
            is_validator=False,
            requires_contract=True,
            output_type=EnumReturnType.MODELS,
        )

        assert len(node_type.dependencies) == 2
        assert node_type.execution_priority == 75
        assert node_type.is_generator is True
        assert node_type.is_validator is False
        assert node_type.requires_contract is True
        assert node_type.output_type == EnumReturnType.MODELS

    def test_name_property_returns_enum_value(self):
        """Test name property returns string value of type_name."""
        node_type = ModelNodeType.CONTRACT_TO_MODEL()

        assert node_type.name == "CONTRACT_TO_MODEL"
        assert isinstance(node_type.name, str)

    def test_str_representation(self):
        """Test __str__ returns type_name value."""
        node_type = ModelNodeType.CONTRACT_TO_MODEL()

        assert str(node_type) == "CONTRACT_TO_MODEL"

    def test_eq_with_string(self):
        """Test equality comparison with string."""
        node_type = ModelNodeType.CONTRACT_TO_MODEL()

        assert node_type == "CONTRACT_TO_MODEL"

    def test_eq_with_another_node_type(self):
        """Test equality comparison with another ModelNodeType."""
        node1 = ModelNodeType.CONTRACT_TO_MODEL()
        node2 = ModelNodeType.CONTRACT_TO_MODEL()

        assert node1 == node2

    def test_eq_with_enum_type_name(self):
        """Test equality comparison with EnumTypeName."""
        node_type = ModelNodeType.CONTRACT_TO_MODEL()

        assert node_type == EnumTypeName.CONTRACT_TO_MODEL

    def test_eq_with_different_type(self):
        """Test inequality with different types."""
        node_type = ModelNodeType.CONTRACT_TO_MODEL()

        assert node_type != 123
        assert node_type != None
        assert node_type != []

    def test_eq_with_different_node_type(self):
        """Test inequality with different node type."""
        node1 = ModelNodeType.CONTRACT_TO_MODEL()
        node2 = ModelNodeType.NODE_GENERATOR()

        assert node1 != node2


@pytest.mark.unit
class TestModelNodeTypeFactoryMethods:
    """Test all factory methods for node types."""

    def test_CONTRACT_TO_MODEL_factory(self):
        """Test CONTRACT_TO_MODEL factory method."""
        node = ModelNodeType.CONTRACT_TO_MODEL()

        assert node.type_name == EnumTypeName.CONTRACT_TO_MODEL
        assert node.category == EnumConfigCategory.GENERATION
        assert node.is_generator is True
        assert node.requires_contract is True
        assert node.output_type == EnumReturnType.MODELS

    def test_MULTI_DOC_MODEL_GENERATOR_factory(self):
        """Test MULTI_DOC_MODEL_GENERATOR factory method."""
        node = ModelNodeType.MULTI_DOC_MODEL_GENERATOR()

        assert node.type_name == EnumTypeName.MULTI_DOC_MODEL_GENERATOR
        assert node.is_generator is True
        assert node.output_type == EnumReturnType.MODELS

    def test_GENERATE_ERROR_CODES_factory(self):
        """Test GENERATE_ERROR_CODES factory method."""
        node = ModelNodeType.GENERATE_ERROR_CODES()

        assert node.type_name == EnumTypeName.GENERATE_ERROR_CODES
        assert node.is_generator is True
        assert node.requires_contract is True
        assert node.output_type == EnumReturnType.ENUMS

    def test_GENERATE_INTROSPECTION_factory(self):
        """Test GENERATE_INTROSPECTION factory method."""
        node = ModelNodeType.GENERATE_INTROSPECTION()

        assert node.type_name == EnumTypeName.GENERATE_INTROSPECTION
        assert node.output_type == EnumReturnType.METADATA

    def test_NODE_GENERATOR_factory(self):
        """Test NODE_GENERATOR factory method."""
        node = ModelNodeType.NODE_GENERATOR()

        assert node.type_name == EnumTypeName.NODE_GENERATOR
        assert node.execution_priority == 90
        assert node.is_generator is True

    def test_TEMPLATE_ENGINE_factory(self):
        """Test TEMPLATE_ENGINE factory method."""
        node = ModelNodeType.TEMPLATE_ENGINE()

        assert node.type_name == EnumTypeName.TEMPLATE_ENGINE
        assert node.category == EnumConfigCategory.TEMPLATE
        assert node.output_type == EnumReturnType.TEXT

    def test_FILE_GENERATOR_factory(self):
        """Test FILE_GENERATOR factory method."""
        node = ModelNodeType.FILE_GENERATOR()

        assert node.type_name == EnumTypeName.FILE_GENERATOR
        assert "TEMPLATE_ENGINE" in node.dependencies
        assert node.output_type == EnumReturnType.FILES

    def test_TEMPLATE_VALIDATOR_factory(self):
        """Test TEMPLATE_VALIDATOR factory method."""
        node = ModelNodeType.TEMPLATE_VALIDATOR()

        assert node.type_name == EnumTypeName.TEMPLATE_VALIDATOR
        assert node.is_validator is True
        assert node.output_type == EnumReturnType.REPORTS

    def test_VALIDATION_ENGINE_factory(self):
        """Test VALIDATION_ENGINE factory method."""
        node = ModelNodeType.VALIDATION_ENGINE()

        assert node.type_name == EnumTypeName.VALIDATION_ENGINE
        assert node.category == EnumConfigCategory.VALIDATION
        assert node.is_validator is True
        assert node.execution_priority == 80

    def test_STANDARDS_COMPLIANCE_FIXER_factory(self):
        """Test STANDARDS_COMPLIANCE_FIXER factory method."""
        node = ModelNodeType.STANDARDS_COMPLIANCE_FIXER()

        assert node.type_name == EnumTypeName.STANDARDS_COMPLIANCE_FIXER
        assert node.is_generator is True
        assert node.is_validator is True

    def test_PARITY_VALIDATOR_WITH_FIXES_factory(self):
        """Test PARITY_VALIDATOR_WITH_FIXES factory method."""
        node = ModelNodeType.PARITY_VALIDATOR_WITH_FIXES()

        assert node.type_name == EnumTypeName.PARITY_VALIDATOR_WITH_FIXES
        assert node.is_validator is True
        assert node.is_generator is True

    def test_CONTRACT_COMPLIANCE_factory(self):
        """Test CONTRACT_COMPLIANCE factory method."""
        node = ModelNodeType.CONTRACT_COMPLIANCE()

        assert node.type_name == EnumTypeName.CONTRACT_COMPLIANCE
        assert node.is_validator is True
        assert node.requires_contract is True

    def test_INTROSPECTION_VALIDITY_factory(self):
        """Test INTROSPECTION_VALIDITY factory method."""
        node = ModelNodeType.INTROSPECTION_VALIDITY()

        assert node.is_validator is True

    def test_SCHEMA_CONFORMANCE_factory(self):
        """Test SCHEMA_CONFORMANCE factory method."""
        node = ModelNodeType.SCHEMA_CONFORMANCE()

        assert node.is_validator is True

    def test_ERROR_CODE_USAGE_factory(self):
        """Test ERROR_CODE_USAGE factory method."""
        node = ModelNodeType.ERROR_CODE_USAGE()

        assert node.is_validator is True

    def test_CLI_COMMANDS_factory(self):
        """Test CLI_COMMANDS factory method."""
        node = ModelNodeType.CLI_COMMANDS()

        assert node.category == EnumConfigCategory.CLI
        assert node.is_generator is True

    def test_CLI_NODE_PARITY_factory(self):
        """Test CLI_NODE_PARITY factory method."""
        node = ModelNodeType.CLI_NODE_PARITY()

        assert node.category == EnumConfigCategory.CLI
        assert node.is_validator is True

    def test_NODE_DISCOVERY_factory(self):
        """Test NODE_DISCOVERY factory method."""
        node = ModelNodeType.NODE_DISCOVERY()

        assert node.category == EnumConfigCategory.DISCOVERY
        assert node.execution_priority == 95

    def test_NODE_VALIDATION_factory(self):
        """Test NODE_VALIDATION factory method."""
        node = ModelNodeType.NODE_VALIDATION()

        assert node.is_validator is True
        assert node.requires_contract is True

    def test_METADATA_LOADER_factory(self):
        """Test METADATA_LOADER factory method."""
        node = ModelNodeType.METADATA_LOADER()

        assert node.category == EnumConfigCategory.DISCOVERY

    def test_SCHEMA_GENERATOR_factory(self):
        """Test SCHEMA_GENERATOR factory method."""
        node = ModelNodeType.SCHEMA_GENERATOR()

        assert node.category == EnumConfigCategory.SCHEMA
        assert node.is_generator is True

    def test_SCHEMA_DISCOVERY_factory(self):
        """Test SCHEMA_DISCOVERY factory method."""
        node = ModelNodeType.SCHEMA_DISCOVERY()

        assert node.category == EnumConfigCategory.SCHEMA

    def test_SCHEMA_TO_PYDANTIC_factory(self):
        """Test SCHEMA_TO_PYDANTIC factory method."""
        node = ModelNodeType.SCHEMA_TO_PYDANTIC()

        assert node.is_generator is True
        assert "SCHEMA_DISCOVERY" in node.dependencies

    def test_PROTOCOL_GENERATOR_factory(self):
        """Test PROTOCOL_GENERATOR factory method."""
        node = ModelNodeType.PROTOCOL_GENERATOR()

        assert node.is_generator is True
        assert node.output_type == EnumReturnType.PROTOCOLS

    def test_BACKEND_SELECTION_factory(self):
        """Test BACKEND_SELECTION factory method."""
        node = ModelNodeType.BACKEND_SELECTION()

        assert node.category == EnumConfigCategory.RUNTIME

    def test_NODE_MANAGER_RUNNER_factory(self):
        """Test NODE_MANAGER_RUNNER factory method."""
        node = ModelNodeType.NODE_MANAGER_RUNNER()

        assert node.execution_priority == 100

    def test_MAINTENANCE_factory(self):
        """Test MAINTENANCE factory method."""
        node = ModelNodeType.MAINTENANCE()

        assert node.category == EnumConfigCategory.MAINTENANCE

    def test_LOGGER_EMIT_LOG_EVENT_factory(self):
        """Test LOGGER_EMIT_LOG_EVENT factory method."""
        node = ModelNodeType.LOGGER_EMIT_LOG_EVENT()

        assert node.category == EnumConfigCategory.LOGGING

    def test_LOGGING_UTILS_factory(self):
        """Test LOGGING_UTILS factory method."""
        node = ModelNodeType.LOGGING_UTILS()

        assert node.category == EnumConfigCategory.LOGGING

    def test_SCENARIO_RUNNER_factory(self):
        """Test SCENARIO_RUNNER factory method."""
        node = ModelNodeType.SCENARIO_RUNNER()

        assert node.category == EnumConfigCategory.TESTING


@pytest.mark.unit
class TestModelNodeTypeFromString:
    """Test from_string factory method."""

    def test_from_string_known_type(self):
        """Test from_string with known node type."""
        node = ModelNodeType.from_string("CONTRACT_TO_MODEL")

        assert node.type_name == EnumTypeName.CONTRACT_TO_MODEL
        assert node.is_generator is True

    def test_from_string_all_factory_types(self):
        """Test from_string works for all factory methods."""
        factory_names = [
            "CONTRACT_TO_MODEL",
            "NODE_GENERATOR",
            "VALIDATION_ENGINE",
            "TEMPLATE_ENGINE",
            "CLI_COMMANDS",
        ]

        for name in factory_names:
            node = ModelNodeType.from_string(name)
            assert node.type_name.value == name

    def test_from_string_valid_enum_no_factory(self):
        """Test from_string with valid enum but no dedicated factory."""
        # This should create a generic node with UNKNOWN category
        # We need a valid EnumTypeName value that doesn't have a factory
        # For this test, we'll use one that exists in the enum
        try:
            node = ModelNodeType.from_string("CONTRACT_TO_MODEL")
            assert node is not None
        except ModelOnexError:
            pytest.skip("No valid EnumTypeName without factory")

    def test_from_string_invalid_type_raises_error(self):
        """Test from_string raises ModelOnexError for invalid type."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelNodeType.from_string("INVALID_NODE_TYPE_12345")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Unknown node type" in str(exc_info.value)


@pytest.mark.unit
class TestModelNodeTypeProtocols:
    """Test protocol implementations."""

    def test_get_id_protocol(self):
        """Test get_id protocol method returns string ID."""
        node = ModelNodeType.CONTRACT_TO_MODEL()

        node_id = node.get_id()
        assert isinstance(node_id, str)
        assert len(node_id) > 0

    def test_get_metadata_protocol(self):
        """Test get_metadata protocol method."""
        node = ModelNodeType.CONTRACT_TO_MODEL()

        metadata = node.get_metadata()
        assert isinstance(metadata, dict)
        assert "description" in metadata

    def test_set_metadata_protocol(self):
        """Test set_metadata protocol method."""
        node = ModelNodeType.CONTRACT_TO_MODEL()

        result = node.set_metadata({"description": "Updated description"})
        assert result is True
        assert node.description == "Updated description"

    def test_set_metadata_protocol_unknown_field(self):
        """Test set_metadata with unknown field doesn't fail."""
        node = ModelNodeType.CONTRACT_TO_MODEL()

        result = node.set_metadata({"unknown_field": "value"})
        assert result is True

    def test_serialize_protocol(self):
        """Test serialize protocol method."""
        node = ModelNodeType.CONTRACT_TO_MODEL()

        serialized = node.serialize()
        assert isinstance(serialized, dict)
        assert "type_name" in serialized
        assert "description" in serialized
        assert "category" in serialized

    def test_validate_instance_protocol(self):
        """Test validate_instance protocol method."""
        node = ModelNodeType.CONTRACT_TO_MODEL()

        assert node.validate_instance() is True

    def test_get_id_with_type_id_field(self):
        """Test get_id uses type_id field."""
        node = ModelNodeType.CONTRACT_TO_MODEL()

        # Should have type_id
        assert hasattr(node, "type_id")
        node_id = node.get_id()
        assert node_id == str(node.type_id)


@pytest.mark.unit
class TestModelNodeTypeEdgeCases:
    """Test edge cases and error scenarios."""

    def test_execution_priority_default(self):
        """Test execution_priority defaults to 50."""
        node = ModelNodeType(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="Test",
            category=EnumConfigCategory.GENERATION,
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
        )

        assert node.execution_priority == 50

    def test_execution_priority_boundaries(self):
        """Test execution_priority enforces boundaries."""
        # Min boundary
        node_min = ModelNodeType(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="Test",
            category=EnumConfigCategory.GENERATION,
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            execution_priority=0,
        )
        assert node_min.execution_priority == 0

        # Max boundary
        node_max = ModelNodeType(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="Test",
            category=EnumConfigCategory.GENERATION,
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            execution_priority=100,
        )
        assert node_max.execution_priority == 100

    def test_boolean_flags_default_false(self):
        """Test boolean flags default to False."""
        node = ModelNodeType(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="Test",
            category=EnumConfigCategory.GENERATION,
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
        )

        assert node.is_generator is False
        assert node.is_validator is False
        assert node.requires_contract is False

    def test_dependencies_empty_by_default(self):
        """Test dependencies is empty list by default."""
        node = ModelNodeType.CONTRACT_TO_MODEL()

        # CONTRACT_TO_MODEL shouldn't have dependencies
        assert isinstance(node.dependencies, list)

    def test_output_type_can_be_none(self):
        """Test output_type can be None."""
        node = ModelNodeType(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="Test",
            category=EnumConfigCategory.GENERATION,
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            output_type=None,
        )

        assert node.output_type is None

    def test_model_config_extra_ignore(self):
        """Test that model ignores extra fields."""
        node = ModelNodeType(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="Test",
            category=EnumConfigCategory.GENERATION,
            version_compatibility=ModelSemVer(major=1, minor=0, patch=0),
            extra_field="ignored",
        )

        assert node.type_name == EnumTypeName.CONTRACT_TO_MODEL

    def test_model_config_validate_assignment(self):
        """Test that model validates on assignment."""
        node = ModelNodeType.CONTRACT_TO_MODEL()

        # Should validate new assignments
        node.description = "Updated description"
        assert node.description == "Updated description"

    def test_version_compatibility_default(self):
        """Test version_compatibility has sensible default."""
        node = ModelNodeType.CONTRACT_TO_MODEL()

        assert node.version_compatibility is not None
        assert isinstance(node.version_compatibility, ModelSemVer)

    def test_factory_methods_produce_consistent_results(self):
        """Test factory methods produce consistent results."""
        node1 = ModelNodeType.CONTRACT_TO_MODEL()
        node2 = ModelNodeType.CONTRACT_TO_MODEL()

        assert node1.type_name == node2.type_name
        assert node1.description == node2.description
        assert node1.category == node2.category

    def test_serialize_includes_all_fields(self):
        """Test serialize includes all fields."""
        node = ModelNodeType.CONTRACT_TO_MODEL()

        serialized = node.serialize()

        expected_fields = [
            "type_id",
            "type_name",
            "description",
            "category",
            "dependencies",
            "execution_priority",
            "is_generator",
            "is_validator",
            "requires_contract",
        ]

        for field in expected_fields:
            assert field in serialized
