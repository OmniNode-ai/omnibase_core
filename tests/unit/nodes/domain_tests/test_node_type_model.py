"""
Test Node Type Model functionality.

Validates that the ModelNodeType works correctly with all
its factory methods, validation, and node type enumeration.
"""

import pytest
from typing import List, Set

from omnibase_core.models.nodes import ModelNodeType


class TestNodeTypeModel:
    """Test ModelNodeType functionality."""

    def test_basic_node_type_creation(self):
        """Test basic node type creation and properties."""
        node_type = ModelNodeType(
            name="TEST_NODE",
            description="Test node for testing",
            category="testing",
        )

        assert node_type.name == "TEST_NODE"
        assert node_type.description == "Test node for testing"
        assert node_type.category == "testing"
        assert not node_type.is_generator
        assert not node_type.is_validator
        assert node_type.execution_priority == 50
        assert node_type.version_compatibility == ">=1.0.0"

    def test_contract_to_model_factory(self):
        """Test CONTRACT_TO_MODEL factory method."""
        node = ModelNodeType.CONTRACT_TO_MODEL()

        assert node.name == "CONTRACT_TO_MODEL"
        assert "Pydantic models" in node.description
        assert node.category == "generation"
        assert node.is_generator
        assert not node.is_validator
        assert node.requires_contract
        assert node.output_type == "models"

    def test_multi_doc_model_generator_factory(self):
        """Test MULTI_DOC_MODEL_GENERATOR factory method."""
        node = ModelNodeType.MULTI_DOC_MODEL_GENERATOR()

        assert node.name == "MULTI_DOC_MODEL_GENERATOR"
        assert "multiple YAML" in node.description
        assert node.category == "generation"
        assert node.is_generator
        assert node.output_type == "models"

    def test_generate_error_codes_factory(self):
        """Test GENERATE_ERROR_CODES factory method."""
        node = ModelNodeType.GENERATE_ERROR_CODES()

        assert node.name == "GENERATE_ERROR_CODES"
        assert "error code" in node.description
        assert node.category == "generation"
        assert node.is_generator
        assert node.requires_contract
        assert node.output_type == "enums"

    def test_generate_introspection_factory(self):
        """Test GENERATE_INTROSPECTION factory method."""
        node = ModelNodeType.GENERATE_INTROSPECTION()

        assert node.name == "GENERATE_INTROSPECTION"
        assert node.category == "generation"
        assert node.is_generator
        assert node.output_type == "metadata"

    def test_node_generator_factory(self):
        """Test NODE_GENERATOR factory method."""
        node = ModelNodeType.NODE_GENERATOR()

        assert node.name == "NODE_GENERATOR"
        assert node.category == "generation"
        assert node.is_generator
        assert node.execution_priority == 90
        assert node.output_type == "node"

    def test_template_engine_factory(self):
        """Test TEMPLATE_ENGINE factory method."""
        node = ModelNodeType.TEMPLATE_ENGINE()

        assert node.name == "TEMPLATE_ENGINE"
        assert node.category == "template"
        assert node.is_generator
        assert node.output_type == "text"

    def test_file_generator_factory(self):
        """Test FILE_GENERATOR factory method."""
        node = ModelNodeType.FILE_GENERATOR()

        assert node.name == "FILE_GENERATOR"
        assert node.category == "template"
        assert node.is_generator
        assert "TEMPLATE_ENGINE" in node.dependencies
        assert node.output_type == "files"

    def test_template_validator_factory(self):
        """Test TEMPLATE_VALIDATOR factory method."""
        node = ModelNodeType.TEMPLATE_VALIDATOR()

        assert node.name == "TEMPLATE_VALIDATOR"
        assert node.category == "validation"
        assert not node.is_generator
        assert node.is_validator
        assert node.output_type == "report"

    def test_validation_engine_factory(self):
        """Test VALIDATION_ENGINE factory method."""
        node = ModelNodeType.VALIDATION_ENGINE()

        assert node.name == "VALIDATION_ENGINE"
        assert node.category == "validation"
        assert not node.is_generator
        assert node.is_validator
        assert node.requires_contract
        assert node.execution_priority == 80
        assert node.output_type == "report"

    def test_standards_compliance_fixer_factory(self):
        """Test STANDARDS_COMPLIANCE_FIXER factory method."""
        node = ModelNodeType.STANDARDS_COMPLIANCE_FIXER()

        assert node.name == "STANDARDS_COMPLIANCE_FIXER"
        assert node.category == "maintenance"
        assert node.is_generator
        assert node.is_validator
        assert node.output_type == "fixes"

    def test_parity_validator_with_fixes_factory(self):
        """Test PARITY_VALIDATOR_WITH_FIXES factory method."""
        node = ModelNodeType.PARITY_VALIDATOR_WITH_FIXES()

        assert node.name == "PARITY_VALIDATOR_WITH_FIXES"
        assert node.category == "validation"
        assert node.is_validator
        assert node.is_generator
        assert node.output_type == "report_and_fixes"

    def test_contract_compliance_factory(self):
        """Test CONTRACT_COMPLIANCE factory method."""
        node = ModelNodeType.CONTRACT_COMPLIANCE()

        assert node.name == "CONTRACT_COMPLIANCE"
        assert node.category == "validation"
        assert not node.is_generator
        assert node.is_validator
        assert node.requires_contract
        assert node.output_type == "report"

    def test_introspection_validity_factory(self):
        """Test INTROSPECTION_VALIDITY factory method."""
        node = ModelNodeType.INTROSPECTION_VALIDITY()

        assert node.name == "INTROSPECTION_VALIDITY"
        assert node.category == "validation"
        assert node.is_validator
        assert node.output_type == "report"

    def test_schema_conformance_factory(self):
        """Test SCHEMA_CONFORMANCE factory method."""
        node = ModelNodeType.SCHEMA_CONFORMANCE()

        assert node.name == "SCHEMA_CONFORMANCE"
        assert node.category == "validation"
        assert node.is_validator
        assert node.output_type == "report"

    def test_error_code_usage_factory(self):
        """Test ERROR_CODE_USAGE factory method."""
        node = ModelNodeType.ERROR_CODE_USAGE()

        assert node.name == "ERROR_CODE_USAGE"
        assert node.category == "validation"
        assert node.is_validator
        assert node.output_type == "report"

    def test_cli_commands_factory(self):
        """Test CLI_COMMANDS factory method."""
        node = ModelNodeType.CLI_COMMANDS()

        assert node.name == "CLI_COMMANDS"
        assert node.category == "cli"
        assert node.is_generator
        assert node.output_type == "commands"

    def test_cli_node_parity_factory(self):
        """Test CLI_NODE_PARITY factory method."""
        node = ModelNodeType.CLI_NODE_PARITY()

        assert node.name == "CLI_NODE_PARITY"
        assert node.category == "cli"
        assert node.is_validator
        assert node.output_type == "report"

    def test_node_discovery_factory(self):
        """Test NODE_DISCOVERY factory method."""
        node = ModelNodeType.NODE_DISCOVERY()

        assert node.name == "NODE_DISCOVERY"
        assert node.category == "discovery"
        assert node.execution_priority == 95
        assert node.output_type == "nodes"

    def test_node_validation_factory(self):
        """Test NODE_VALIDATION factory method."""
        node = ModelNodeType.NODE_VALIDATION()

        assert node.name == "NODE_VALIDATION"
        assert node.category == "validation"
        assert node.is_validator
        assert node.requires_contract
        assert node.output_type == "report"

    def test_metadata_loader_factory(self):
        """Test METADATA_LOADER factory method."""
        node = ModelNodeType.METADATA_LOADER()

        assert node.name == "METADATA_LOADER"
        assert node.category == "discovery"
        assert node.output_type == "metadata"

    def test_schema_generator_factory(self):
        """Test SCHEMA_GENERATOR factory method."""
        node = ModelNodeType.SCHEMA_GENERATOR()

        assert node.name == "SCHEMA_GENERATOR"
        assert node.category == "schema"
        assert node.is_generator
        assert node.output_type == "schemas"

    def test_schema_discovery_factory(self):
        """Test SCHEMA_DISCOVERY factory method."""
        node = ModelNodeType.SCHEMA_DISCOVERY()

        assert node.name == "SCHEMA_DISCOVERY"
        assert node.category == "schema"
        assert node.output_type == "schemas"

    def test_schema_to_pydantic_factory(self):
        """Test SCHEMA_TO_PYDANTIC factory method."""
        node = ModelNodeType.SCHEMA_TO_PYDANTIC()

        assert node.name == "SCHEMA_TO_PYDANTIC"
        assert node.category == "schema"
        assert node.is_generator
        assert "SCHEMA_DISCOVERY" in node.dependencies
        assert node.output_type == "models"

    def test_protocol_generator_factory(self):
        """Test PROTOCOL_GENERATOR factory method."""
        node = ModelNodeType.PROTOCOL_GENERATOR()

        assert node.name == "PROTOCOL_GENERATOR"
        assert node.category == "generation"
        assert node.is_generator
        assert node.output_type == "protocols"

    def test_backend_selection_factory(self):
        """Test BACKEND_SELECTION factory method."""
        node = ModelNodeType.BACKEND_SELECTION()

        assert node.name == "BACKEND_SELECTION"
        assert node.category == "runtime"
        assert node.output_type == "backend"

    def test_node_manager_runner_factory(self):
        """Test NODE_MANAGER_RUNNER factory method."""
        node = ModelNodeType.NODE_MANAGER_RUNNER()

        assert node.name == "NODE_MANAGER_RUNNER"
        assert node.category == "runtime"
        assert node.execution_priority == 100
        assert node.output_type == "result"

    def test_maintenance_factory(self):
        """Test MAINTENANCE factory method."""
        node = ModelNodeType.MAINTENANCE()

        assert node.name == "MAINTENANCE"
        assert node.category == "maintenance"
        assert node.output_type == "status"

    def test_logger_emit_log_event_factory(self):
        """Test LOGGER_EMIT_LOG_EVENT factory method."""
        node = ModelNodeType.LOGGER_EMIT_LOG_EVENT()

        assert node.name == "node_logger_emit_log_event"
        assert node.category == "logging"
        assert node.output_type == "logs"

    def test_logging_utils_factory(self):
        """Test LOGGING_UTILS factory method."""
        node = ModelNodeType.LOGGING_UTILS()

        assert node.name == "LOGGING_UTILS"
        assert node.category == "logging"
        assert node.output_type == "logs"

    def test_scenario_runner_factory(self):
        """Test SCENARIO_RUNNER factory method."""
        node = ModelNodeType.SCENARIO_RUNNER()

        assert node.name == "scenario_runner"
        assert node.category == "testing"
        assert node.output_type == "results"

    def test_from_string_known_types(self):
        """Test from_string with known node types."""
        test_cases = [
            "CONTRACT_TO_MODEL",
            "VALIDATION_ENGINE",
            "NODE_GENERATOR",
            "TEMPLATE_ENGINE",
            "FILE_GENERATOR",
            "node_logger_emit_log_event",
            "scenario_runner",
        ]

        for node_name in test_cases:
            node = ModelNodeType.from_string(node_name)
            assert node.name == node_name

    def test_from_string_unknown_type(self):
        """Test from_string with unknown node type."""
        node = ModelNodeType.from_string("UNKNOWN_NODE_TYPE")

        assert node.name == "UNKNOWN_NODE_TYPE"
        assert node.description == "Node: UNKNOWN_NODE_TYPE"
        assert node.category == "unknown"

    def test_string_representation(self):
        """Test string representation."""
        node = ModelNodeType.CONTRACT_TO_MODEL()
        assert str(node) == "CONTRACT_TO_MODEL"

    def test_equality_comparison(self):
        """Test equality comparison."""
        node = ModelNodeType.CONTRACT_TO_MODEL()

        # Test equality with string
        assert node == "CONTRACT_TO_MODEL"

        # Test equality with another node type
        other_node = ModelNodeType.CONTRACT_TO_MODEL()
        assert node == other_node

        # Test inequality
        different_node = ModelNodeType.VALIDATION_ENGINE()
        assert node != different_node
        assert node != "VALIDATION_ENGINE"

    def test_name_pattern_validation(self):
        """Test name pattern validation."""
        # Valid names
        valid_names = [
            "CONTRACT_TO_MODEL",
            "A_VALID_NAME",
            "X123_TEST",
        ]

        for name in valid_names:
            node = ModelNodeType(
                name=name,
                description="Test",
                category="test",
            )
            assert node.name == name

        # Invalid names should fail validation
        invalid_names = [
            "invalid_name",  # lowercase
            "123_INVALID",   # starts with number
            "INVALID-NAME",  # contains hyphen
            "",              # empty
        ]

        for name in invalid_names:
            with pytest.raises(Exception):
                ModelNodeType(
                    name=name,
                    description="Test",
                    category="test",
                )

    def test_category_pattern_validation(self):
        """Test category pattern validation."""
        # Valid categories
        valid_categories = [
            "generation",
            "validation",
            "template",
            "runtime",
            "discovery",
            "test_category",
        ]

        for category in valid_categories:
            node = ModelNodeType(
                name="TEST_NODE",
                description="Test",
                category=category,
            )
            assert node.category == category

        # Invalid categories should fail validation
        invalid_categories = [
            "INVALID_CATEGORY",  # uppercase
            "invalid-category",  # contains hyphen
            "",                  # empty
            "123invalid",        # starts with number
        ]

        for category in invalid_categories:
            with pytest.raises(Exception):
                ModelNodeType(
                    name="TEST_NODE",
                    description="Test",
                    category=category,
                )

    def test_execution_priority_validation(self):
        """Test execution priority validation."""
        # Valid priorities
        for priority in [0, 25, 50, 75, 100]:
            node = ModelNodeType(
                name="TEST_NODE",
                description="Test",
                category="test",
                execution_priority=priority,
            )
            assert node.execution_priority == priority

        # Invalid priorities should fail validation
        invalid_priorities = [-1, 101, 150]

        for priority in invalid_priorities:
            with pytest.raises(Exception):
                ModelNodeType(
                    name="TEST_NODE",
                    description="Test",
                    category="test",
                    execution_priority=priority,
                )

    def test_dependencies_management(self):
        """Test dependency management."""
        node = ModelNodeType(
            name="TEST_NODE",
            description="Test node with dependencies",
            category="test",
            dependencies=["DEP1", "DEP2"],
        )

        assert len(node.dependencies) == 2
        assert "DEP1" in node.dependencies
        assert "DEP2" in node.dependencies

        # Test empty dependencies
        simple_node = ModelNodeType(
            name="SIMPLE_NODE",
            description="Simple node",
            category="test",
        )
        assert len(simple_node.dependencies) == 0

    def test_model_serialization(self):
        """Test model serialization and deserialization."""
        original = ModelNodeType.CONTRACT_TO_MODEL()

        # Serialize
        serialized = original.model_dump()
        assert isinstance(serialized, dict)
        assert serialized["name"] == "CONTRACT_TO_MODEL"

        # Deserialize
        restored = ModelNodeType.model_validate(serialized)
        assert restored.name == original.name
        assert restored.description == original.description
        assert restored.category == original.category

    def test_all_factory_methods_comprehensive(self):
        """Test all factory methods comprehensively."""
        factory_methods = [
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
            "LOGGER_EMIT_LOG_EVENT",
            "LOGGING_UTILS",
            "SCENARIO_RUNNER",
        ]

        for method_name in factory_methods:
            node = getattr(ModelNodeType, method_name)()

            # Basic validation
            assert node.name is not None
            assert node.description is not None
            assert node.category is not None

            # Execution priority should be valid
            assert 0 <= node.execution_priority <= 100

            # Dependencies should be a list
            assert isinstance(node.dependencies, list)

    def test_node_type_categories(self):
        """Test node type categories are consistent."""
        category_examples = {
            "generation": ["CONTRACT_TO_MODEL", "NODE_GENERATOR"],
            "validation": ["VALIDATION_ENGINE", "CONTRACT_COMPLIANCE"],
            "template": ["TEMPLATE_ENGINE", "FILE_GENERATOR"],
            "runtime": ["BACKEND_SELECTION", "NODE_MANAGER_RUNNER"],
            "discovery": ["NODE_DISCOVERY", "METADATA_LOADER"],
            "schema": ["SCHEMA_GENERATOR", "SCHEMA_DISCOVERY"],
            "cli": ["CLI_COMMANDS", "CLI_NODE_PARITY"],
            "maintenance": ["MAINTENANCE", "STANDARDS_COMPLIANCE_FIXER"],
            "logging": ["LOGGER_EMIT_LOG_EVENT", "LOGGING_UTILS"],
            "testing": ["SCENARIO_RUNNER"],
        }

        for category, examples in category_examples.items():
            for example in examples:
                node = ModelNodeType.from_string(example)
                assert node.category == category, f"{example} should be in {category} category"

    def test_generator_and_validator_patterns(self):
        """Test generator and validator patterns."""
        # Generators should have output
        generators = [
            ModelNodeType.CONTRACT_TO_MODEL(),
            ModelNodeType.NODE_GENERATOR(),
            ModelNodeType.FILE_GENERATOR(),
        ]

        for generator in generators:
            assert generator.is_generator
            assert generator.output_type is not None

        # Validators should produce reports
        validators = [
            ModelNodeType.VALIDATION_ENGINE(),
            ModelNodeType.CONTRACT_COMPLIANCE(),
            ModelNodeType.TEMPLATE_VALIDATOR(),
        ]

        for validator in validators:
            assert validator.is_validator
            assert "report" in validator.output_type

    def test_execution_priority_patterns(self):
        """Test execution priority patterns."""
        # High priority nodes (orchestrators)
        high_priority = [
            ModelNodeType.NODE_MANAGER_RUNNER(),
            ModelNodeType.NODE_DISCOVERY(),
        ]

        for node in high_priority:
            assert node.execution_priority >= 90

        # Medium priority nodes (validators)
        medium_priority = [
            ModelNodeType.VALIDATION_ENGINE(),
        ]

        for node in medium_priority:
            assert node.execution_priority >= 75

        # Default priority nodes
        default_priority = [
            ModelNodeType.CONTRACT_TO_MODEL(),
        ]

        for node in default_priority:
            assert node.execution_priority == 50

    @pytest.mark.parametrize("factory_method", [
        "CONTRACT_TO_MODEL",
        "VALIDATION_ENGINE",
        "NODE_GENERATOR",
        "TEMPLATE_ENGINE",
        "FILE_GENERATOR",
        "NODE_MANAGER_RUNNER",
        "SCHEMA_GENERATOR",
        "CLI_COMMANDS",
        "NODE_DISCOVERY",
        "MAINTENANCE",
    ])
    def test_individual_factory_methods(self, factory_method):
        """Test individual factory methods work correctly."""
        node = getattr(ModelNodeType, factory_method)()

        # Basic validation
        assert node.name == factory_method or node.name in ["node_logger_emit_log_event", "scenario_runner"]
        assert node.description is not None
        assert node.category is not None

        # Test string representation
        assert str(node) == node.name

        # Test equality
        same_node = getattr(ModelNodeType, factory_method)()
        assert node == same_node
        assert node == node.name

        # Test model validation
        node_dict = node.model_dump()
        restored_node = ModelNodeType.model_validate(node_dict)
        assert restored_node.name == node.name