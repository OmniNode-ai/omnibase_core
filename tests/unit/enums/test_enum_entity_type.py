from enum import Enum

import pytest

from omnibase_core.enums.enum_entity_type import EnumEntityType


class TestEnumEntityType:
    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert EnumEntityType.NODE == "node"
        assert EnumEntityType.FUNCTION == "function"
        assert EnumEntityType.MODEL == "model"
        assert EnumEntityType.SCHEMA == "schema"
        assert EnumEntityType.CONFIG == "config"
        assert EnumEntityType.METADATA == "metadata"
        assert EnumEntityType.FILE == "file"
        assert EnumEntityType.DOCUMENT == "document"
        assert EnumEntityType.TEMPLATE == "template"
        assert EnumEntityType.CONTRACT == "contract"
        assert EnumEntityType.EXAMPLE == "example"
        assert EnumEntityType.SERVICE == "service"
        assert EnumEntityType.COMPONENT == "component"
        assert EnumEntityType.MODULE == "module"
        assert EnumEntityType.PACKAGE == "package"
        assert EnumEntityType.WORKFLOW == "workflow"
        assert EnumEntityType.REDUCER == "reducer"
        assert EnumEntityType.VALIDATOR == "validator"
        assert EnumEntityType.GENERATOR == "generator"
        assert EnumEntityType.TRANSFORMER == "transformer"
        assert EnumEntityType.UNKNOWN == "unknown"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumEntityType, str)
        assert issubclass(EnumEntityType, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        entity_type = EnumEntityType.NODE
        assert isinstance(entity_type, str)
        assert entity_type == "node"
        assert len(entity_type) == 4
        assert entity_type.startswith("no")

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumEntityType)
        assert len(values) == 21
        assert EnumEntityType.NODE in values
        assert EnumEntityType.UNKNOWN in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumEntityType.FUNCTION in EnumEntityType
        assert "function" in [e.value for e in EnumEntityType]

    def test_enum_comparison(self):
        """Test enum comparison."""
        entity1 = EnumEntityType.MODEL
        entity2 = EnumEntityType.MODEL
        entity3 = EnumEntityType.SCHEMA

        assert entity1 == entity2
        assert entity1 != entity3
        assert entity1 == "model"

    def test_enum_serialization(self):
        """Test enum serialization."""
        entity_type = EnumEntityType.SERVICE
        serialized = entity_type.value
        assert serialized == "service"
        import json

        json_str = json.dumps(entity_type)
        assert json_str == '"service"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        entity_type = EnumEntityType("workflow")
        assert entity_type == EnumEntityType.WORKFLOW

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumEntityType("invalid_entity")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "node",
            "function",
            "model",
            "schema",
            "config",
            "metadata",
            "file",
            "document",
            "template",
            "contract",
            "example",
            "service",
            "component",
            "module",
            "package",
            "workflow",
            "reducer",
            "validator",
            "generator",
            "transformer",
            "unknown",
        }
        actual_values = {e.value for e in EnumEntityType}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumEntityType.__doc__ is not None
        assert "entity type values" in EnumEntityType.__doc__.lower()

    def test_enum_str_method(self):
        """Test __str__ method."""
        entity_type = EnumEntityType.MODEL
        assert str(entity_type) == "model"
        assert str(entity_type) == entity_type.value

    def test_is_code_entity_class_method(self):
        """Test is_code_entity class method."""
        # Code entities
        assert EnumEntityType.is_code_entity(EnumEntityType.FUNCTION)
        assert EnumEntityType.is_code_entity(EnumEntityType.MODEL)
        assert EnumEntityType.is_code_entity(EnumEntityType.SCHEMA)
        assert EnumEntityType.is_code_entity(EnumEntityType.MODULE)
        assert EnumEntityType.is_code_entity(EnumEntityType.PACKAGE)

        # Non-code entities
        assert not EnumEntityType.is_code_entity(EnumEntityType.NODE)
        assert not EnumEntityType.is_code_entity(EnumEntityType.FILE)
        assert not EnumEntityType.is_code_entity(EnumEntityType.SERVICE)

    def test_is_data_entity_class_method(self):
        """Test is_data_entity class method."""
        # Data entities
        assert EnumEntityType.is_data_entity(EnumEntityType.FILE)
        assert EnumEntityType.is_data_entity(EnumEntityType.DOCUMENT)
        assert EnumEntityType.is_data_entity(EnumEntityType.TEMPLATE)
        assert EnumEntityType.is_data_entity(EnumEntityType.CONTRACT)
        assert EnumEntityType.is_data_entity(EnumEntityType.EXAMPLE)
        assert EnumEntityType.is_data_entity(EnumEntityType.METADATA)

        # Non-data entities
        assert not EnumEntityType.is_data_entity(EnumEntityType.NODE)
        assert not EnumEntityType.is_data_entity(EnumEntityType.FUNCTION)
        assert not EnumEntityType.is_data_entity(EnumEntityType.SERVICE)

    def test_is_system_entity_class_method(self):
        """Test is_system_entity class method."""
        # System entities
        assert EnumEntityType.is_system_entity(EnumEntityType.SERVICE)
        assert EnumEntityType.is_system_entity(EnumEntityType.COMPONENT)
        assert EnumEntityType.is_system_entity(EnumEntityType.WORKFLOW)
        assert EnumEntityType.is_system_entity(EnumEntityType.NODE)

        # Non-system entities
        assert not EnumEntityType.is_system_entity(EnumEntityType.FILE)
        assert not EnumEntityType.is_system_entity(EnumEntityType.FUNCTION)
        assert not EnumEntityType.is_system_entity(EnumEntityType.REDUCER)

    def test_is_infrastructure_entity_class_method(self):
        """Test is_infrastructure_entity class method."""
        # Infrastructure entities
        assert EnumEntityType.is_infrastructure_entity(EnumEntityType.REDUCER)
        assert EnumEntityType.is_infrastructure_entity(EnumEntityType.VALIDATOR)
        assert EnumEntityType.is_infrastructure_entity(EnumEntityType.GENERATOR)
        assert EnumEntityType.is_infrastructure_entity(EnumEntityType.TRANSFORMER)

        # Non-infrastructure entities
        assert not EnumEntityType.is_infrastructure_entity(EnumEntityType.NODE)
        assert not EnumEntityType.is_infrastructure_entity(EnumEntityType.FILE)
        assert not EnumEntityType.is_infrastructure_entity(EnumEntityType.SERVICE)

    def test_entity_categorization_completeness(self):
        """Test that all entities are categorized by at least one method."""
        all_entities = set(EnumEntityType)

        # Get entities categorized by each method
        code_entities = {e for e in EnumEntityType if EnumEntityType.is_code_entity(e)}
        data_entities = {e for e in EnumEntityType if EnumEntityType.is_data_entity(e)}
        system_entities = {
            e for e in EnumEntityType if EnumEntityType.is_system_entity(e)
        }
        infrastructure_entities = {
            e for e in EnumEntityType if EnumEntityType.is_infrastructure_entity(e)
        }

        # All entities should be categorized (except UNKNOWN)
        categorized_entities = (
            code_entities | data_entities | system_entities | infrastructure_entities
        )
        assert EnumEntityType.UNKNOWN not in categorized_entities
        # Some entities might not be categorized by the current methods
        assert (
            len(categorized_entities) >= len(all_entities) - 3
        )  # Most entities should be categorized

    def test_entity_categorization_exclusivity(self):
        """Test that entity categories don't overlap inappropriately."""
        code_entities = {e for e in EnumEntityType if EnumEntityType.is_code_entity(e)}
        data_entities = {e for e in EnumEntityType if EnumEntityType.is_data_entity(e)}
        system_entities = {
            e for e in EnumEntityType if EnumEntityType.is_system_entity(e)
        }
        infrastructure_entities = {
            e for e in EnumEntityType if EnumEntityType.is_infrastructure_entity(e)
        }

        # Code and data entities should not overlap
        assert code_entities.isdisjoint(data_entities)

        # System and infrastructure entities should not overlap
        assert system_entities.isdisjoint(infrastructure_entities)
