"""
Unit tests for EnumEntityType.

Tests all aspects of the entity type enum including:
- Enum value validation
- Category classification methods (is_code_entity, is_data_entity, etc.)
- String representation
- JSON serialization compatibility
- Pydantic integration
- All helper methods
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_entity_type import EnumEntityType


class TestEnumEntityTypeBasics:
    """Test basic enum functionality."""

    def test_enum_values_core(self):
        """Test that all core entity type enum values are present."""
        core_entities = {
            "NODE": "node",
            "FUNCTION": "function",
            "MODEL": "model",
            "SCHEMA": "schema",
            "CONFIG": "config",
            "METADATA": "metadata",
        }

        for name, value in core_entities.items():
            entity_type = getattr(EnumEntityType, name)
            assert entity_type.value == value
            assert str(entity_type) == value

    def test_enum_values_data(self):
        """Test that all data entity type enum values are present."""
        data_entities = {
            "FILE": "file",
            "DOCUMENT": "document",
            "TEMPLATE": "template",
            "CONTRACT": "contract",
            "EXAMPLE": "example",
        }

        for name, value in data_entities.items():
            entity_type = getattr(EnumEntityType, name)
            assert entity_type.value == value
            assert str(entity_type) == value

    def test_enum_values_system(self):
        """Test that all system entity type enum values are present."""
        system_entities = {
            "SERVICE": "service",
            "COMPONENT": "component",
            "MODULE": "module",
            "PACKAGE": "package",
            "WORKFLOW": "workflow",
        }

        for name, value in system_entities.items():
            entity_type = getattr(EnumEntityType, name)
            assert entity_type.value == value
            assert str(entity_type) == value

    def test_enum_values_infrastructure(self):
        """Test that all infrastructure entity type enum values are present."""
        infra_entities = {
            "REDUCER": "reducer",
            "VALIDATOR": "validator",
            "GENERATOR": "generator",
            "TRANSFORMER": "transformer",
        }

        for name, value in infra_entities.items():
            entity_type = getattr(EnumEntityType, name)
            assert entity_type.value == value
            assert str(entity_type) == value

    def test_enum_values_unknown(self):
        """Test that UNKNOWN entity type is present."""
        assert EnumEntityType.UNKNOWN.value == "unknown"
        assert str(EnumEntityType.UNKNOWN) == "unknown"

    def test_string_representation(self):
        """Test __str__ method returns correct string values."""
        assert str(EnumEntityType.NODE) == "node"
        assert str(EnumEntityType.FUNCTION) == "function"
        assert str(EnumEntityType.FILE) == "file"
        assert str(EnumEntityType.SERVICE) == "service"
        assert str(EnumEntityType.REDUCER) == "reducer"


class TestEnumEntityTypeCategoryMethods:
    """Test category classification methods."""

    def test_is_code_entity(self):
        """Test is_code_entity class method."""
        # Code entities should return True
        assert EnumEntityType.is_code_entity(EnumEntityType.FUNCTION) is True
        assert EnumEntityType.is_code_entity(EnumEntityType.MODEL) is True
        assert EnumEntityType.is_code_entity(EnumEntityType.SCHEMA) is True
        assert EnumEntityType.is_code_entity(EnumEntityType.MODULE) is True
        assert EnumEntityType.is_code_entity(EnumEntityType.PACKAGE) is True

        # Non-code entities should return False
        assert EnumEntityType.is_code_entity(EnumEntityType.FILE) is False
        assert EnumEntityType.is_code_entity(EnumEntityType.SERVICE) is False
        assert EnumEntityType.is_code_entity(EnumEntityType.REDUCER) is False
        assert EnumEntityType.is_code_entity(EnumEntityType.UNKNOWN) is False

    def test_is_data_entity(self):
        """Test is_data_entity class method."""
        # Data entities should return True
        assert EnumEntityType.is_data_entity(EnumEntityType.FILE) is True
        assert EnumEntityType.is_data_entity(EnumEntityType.DOCUMENT) is True
        assert EnumEntityType.is_data_entity(EnumEntityType.TEMPLATE) is True
        assert EnumEntityType.is_data_entity(EnumEntityType.CONTRACT) is True
        assert EnumEntityType.is_data_entity(EnumEntityType.EXAMPLE) is True
        assert EnumEntityType.is_data_entity(EnumEntityType.METADATA) is True

        # Non-data entities should return False
        assert EnumEntityType.is_data_entity(EnumEntityType.FUNCTION) is False
        assert EnumEntityType.is_data_entity(EnumEntityType.SERVICE) is False
        assert EnumEntityType.is_data_entity(EnumEntityType.REDUCER) is False

    def test_is_system_entity(self):
        """Test is_system_entity class method."""
        # System entities should return True
        assert EnumEntityType.is_system_entity(EnumEntityType.SERVICE) is True
        assert EnumEntityType.is_system_entity(EnumEntityType.COMPONENT) is True
        assert EnumEntityType.is_system_entity(EnumEntityType.WORKFLOW) is True
        assert EnumEntityType.is_system_entity(EnumEntityType.NODE) is True

        # Non-system entities should return False
        assert EnumEntityType.is_system_entity(EnumEntityType.FUNCTION) is False
        assert EnumEntityType.is_system_entity(EnumEntityType.FILE) is False
        assert EnumEntityType.is_system_entity(EnumEntityType.REDUCER) is False

    def test_is_infrastructure_entity(self):
        """Test is_infrastructure_entity class method."""
        # Infrastructure entities should return True
        assert EnumEntityType.is_infrastructure_entity(EnumEntityType.REDUCER) is True
        assert EnumEntityType.is_infrastructure_entity(EnumEntityType.VALIDATOR) is True
        assert EnumEntityType.is_infrastructure_entity(EnumEntityType.GENERATOR) is True
        assert (
            EnumEntityType.is_infrastructure_entity(EnumEntityType.TRANSFORMER) is True
        )

        # Non-infrastructure entities should return False
        assert EnumEntityType.is_infrastructure_entity(EnumEntityType.FUNCTION) is False
        assert EnumEntityType.is_infrastructure_entity(EnumEntityType.FILE) is False
        assert EnumEntityType.is_infrastructure_entity(EnumEntityType.SERVICE) is False

    def test_category_mutual_exclusivity(self):
        """Test that entity types belong to only one category (or none)."""
        all_entities = list(EnumEntityType)

        for entity in all_entities:
            categories = [
                EnumEntityType.is_code_entity(entity),
                EnumEntityType.is_data_entity(entity),
                EnumEntityType.is_system_entity(entity),
                EnumEntityType.is_infrastructure_entity(entity),
            ]

            # UNKNOWN should not belong to any category
            if entity == EnumEntityType.UNKNOWN:
                assert (
                    sum(categories) == 0
                ), f"{entity} should not belong to any category"
            # CONFIG should not belong to any category (it's core but not classified)
            elif entity == EnumEntityType.CONFIG:
                assert (
                    sum(categories) == 0
                ), f"{entity} should not belong to any category"
            else:
                # All other entities should belong to exactly one category
                assert (
                    sum(categories) == 1
                ), f"{entity} should belong to exactly one category, found {sum(categories)}"


class TestEnumEntityTypeIntegration:
    """Test integration with other systems."""

    def test_enum_equality(self):
        """Test enum equality comparison."""
        assert EnumEntityType.NODE == EnumEntityType.NODE
        assert EnumEntityType.FUNCTION != EnumEntityType.MODEL
        assert EnumEntityType.SERVICE == EnumEntityType.SERVICE

    def test_enum_membership(self):
        """Test enum membership checking."""
        assert EnumEntityType.NODE in EnumEntityType
        assert EnumEntityType.FILE in EnumEntityType
        assert EnumEntityType.REDUCER in EnumEntityType

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        entity_types = list(EnumEntityType)
        # Should have all 21 entity types
        assert len(entity_types) == 21

        # Verify key entities are present
        entity_values = [et.value for et in entity_types]
        assert "node" in entity_values
        assert "function" in entity_values
        assert "file" in entity_values

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        # Test direct serialization
        entity = EnumEntityType.FUNCTION
        json_str = json.dumps(entity, default=str)
        assert json_str == '"function"'

        # Test in dictionary
        data = {"entity_type": EnumEntityType.SERVICE}
        json_str = json.dumps(data, default=str)
        assert '"entity_type": "service"' in json_str

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class EntityModel(BaseModel):
            entity_type: EnumEntityType

        # Test valid enum assignment
        entity = EntityModel(entity_type=EnumEntityType.FUNCTION)
        assert entity.entity_type == EnumEntityType.FUNCTION

        # Test string assignment (should work due to str inheritance)
        entity = EntityModel(entity_type="reducer")
        assert entity.entity_type == EnumEntityType.REDUCER

        # Test invalid value should raise ValidationError
        with pytest.raises(ValidationError):
            EntityModel(entity_type="invalid_entity_type")

    def test_pydantic_serialization(self):
        """Test Pydantic model serialization."""

        class EntityModel(BaseModel):
            entity_type: EnumEntityType

        entity = EntityModel(entity_type=EnumEntityType.VALIDATOR)

        # Test dict serialization
        entity_dict = entity.model_dump()
        assert entity_dict == {"entity_type": "validator"}

        # Test JSON serialization
        json_str = entity.model_dump_json()
        assert json_str == '{"entity_type":"validator"}'


class TestEnumEntityTypeEdgeCases:
    """Test edge cases and error conditions."""

    def test_case_sensitivity(self):
        """Test that enum values are case-sensitive."""
        assert EnumEntityType.NODE.value == "node"
        assert EnumEntityType.NODE.value != "NODE"
        assert EnumEntityType.NODE.value != "Node"

    def test_invalid_enum_creation(self):
        """Test that invalid enum values cannot be created."""
        with pytest.raises((ValueError, AttributeError)):
            _ = EnumEntityType("invalid_entity")

    def test_unique_decorator_enforcement(self):
        """Test that @unique decorator prevents duplicate values."""
        # Get all enum values
        values = [et.value for et in EnumEntityType]

        # All values should be unique (no duplicates)
        assert len(values) == len(set(values))

    def test_yaml_serialization_compatibility(self):
        """Test YAML serialization compatibility."""
        import yaml

        # Test that enum values are YAML serializable
        data = {"entity_type": EnumEntityType.WORKFLOW.value}
        yaml_str = yaml.dump(data, default_flow_style=False)
        assert "entity_type: workflow" in yaml_str

        # Test that we can load it back
        loaded_data = yaml.safe_load(yaml_str)
        assert loaded_data["entity_type"] == "workflow"

        # Test that the enum value equals the string
        assert EnumEntityType.WORKFLOW == "workflow"


class TestEnumEntityTypeComprehensiveScenarios:
    """Test comprehensive real-world scenarios."""

    def test_entity_routing_by_category(self):
        """Test routing entities based on their category."""
        # Simulate routing different entity types
        code_entities = [
            et for et in EnumEntityType if EnumEntityType.is_code_entity(et)
        ]
        assert len(code_entities) == 5
        assert EnumEntityType.FUNCTION in code_entities
        assert EnumEntityType.MODULE in code_entities

        data_entities = [
            et for et in EnumEntityType if EnumEntityType.is_data_entity(et)
        ]
        assert len(data_entities) == 6
        assert EnumEntityType.FILE in data_entities
        assert EnumEntityType.CONTRACT in data_entities

    def test_onex_node_classification(self):
        """Test ONEX node-related entity classification."""
        # NODE is a system entity
        assert EnumEntityType.is_system_entity(EnumEntityType.NODE) is True

        # REDUCER is an infrastructure entity
        assert EnumEntityType.is_infrastructure_entity(EnumEntityType.REDUCER) is True

        # FUNCTION and MODEL are code entities
        assert EnumEntityType.is_code_entity(EnumEntityType.FUNCTION) is True
        assert EnumEntityType.is_code_entity(EnumEntityType.MODEL) is True

    def test_entity_type_classification_coverage(self):
        """Test that all non-generic entities are classified."""
        all_entities = list(EnumEntityType)
        unclassified_entities = [EnumEntityType.UNKNOWN, EnumEntityType.CONFIG]

        classified_entities = [
            et
            for et in all_entities
            if (
                EnumEntityType.is_code_entity(et)
                or EnumEntityType.is_data_entity(et)
                or EnumEntityType.is_system_entity(et)
                or EnumEntityType.is_infrastructure_entity(et)
            )
        ]

        # All entities except unclassified ones should be classified
        expected_classified = len(all_entities) - len(unclassified_entities)
        assert len(classified_entities) == expected_classified

    def test_data_pipeline_entity_types(self):
        """Test entity types relevant to data pipelines."""
        # TRANSFORMER is infrastructure
        assert (
            EnumEntityType.is_infrastructure_entity(EnumEntityType.TRANSFORMER) is True
        )

        # VALIDATOR is infrastructure
        assert EnumEntityType.is_infrastructure_entity(EnumEntityType.VALIDATOR) is True

        # FILE and DOCUMENT are data entities
        assert EnumEntityType.is_data_entity(EnumEntityType.FILE) is True
        assert EnumEntityType.is_data_entity(EnumEntityType.DOCUMENT) is True

    def test_comprehensive_entity_model(self):
        """Test a comprehensive model using entity type with metadata."""

        class EntityDescriptor(BaseModel):
            entity_type: EnumEntityType
            name: str
            is_code: bool
            is_data: bool
            is_system: bool
            is_infrastructure: bool

        def create_descriptor(
            entity_type: EnumEntityType, name: str
        ) -> EntityDescriptor:
            return EntityDescriptor(
                entity_type=entity_type,
                name=name,
                is_code=EnumEntityType.is_code_entity(entity_type),
                is_data=EnumEntityType.is_data_entity(entity_type),
                is_system=EnumEntityType.is_system_entity(entity_type),
                is_infrastructure=EnumEntityType.is_infrastructure_entity(entity_type),
            )

        # Test function entity
        func_descriptor = create_descriptor(EnumEntityType.FUNCTION, "my_function")
        assert func_descriptor.entity_type == EnumEntityType.FUNCTION
        assert func_descriptor.is_code is True
        assert func_descriptor.is_data is False
        assert func_descriptor.is_system is False
        assert func_descriptor.is_infrastructure is False

        # Test file entity
        file_descriptor = create_descriptor(EnumEntityType.FILE, "data.json")
        assert file_descriptor.entity_type == EnumEntityType.FILE
        assert file_descriptor.is_code is False
        assert file_descriptor.is_data is True
        assert file_descriptor.is_system is False
        assert file_descriptor.is_infrastructure is False

        # Test service entity
        service_descriptor = create_descriptor(EnumEntityType.SERVICE, "api_service")
        assert service_descriptor.entity_type == EnumEntityType.SERVICE
        assert service_descriptor.is_code is False
        assert service_descriptor.is_data is False
        assert service_descriptor.is_system is True
        assert service_descriptor.is_infrastructure is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
