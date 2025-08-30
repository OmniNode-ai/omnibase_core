"""
Test suite for UtilityTypeMapper.

Verifies type mapping functionality for ONEX contract generation.
"""

import pytest

from omnibase_core.model.core.model_schema import ModelSchema
from omnibase_core.utils.generation.utility_type_mapper import \
    UtilityTypeMapper


class TestUtilityTypeMapper:
    """Test suite for the type mapper utility."""

    def test_basic_type_mapping(self):
        """Test mapping of basic JSON schema types to Python types."""
        mapper = UtilityTypeMapper()

        # Test basic types
        assert (
            mapper.get_type_string_from_schema(ModelSchema(schema_type="string"))
            == "str"
        )
        assert (
            mapper.get_type_string_from_schema(ModelSchema(schema_type="integer"))
            == "int"
        )
        assert (
            mapper.get_type_string_from_schema(ModelSchema(schema_type="number"))
            == "float"
        )
        assert (
            mapper.get_type_string_from_schema(ModelSchema(schema_type="boolean"))
            == "bool"
        )

    def test_array_type_mapping(self):
        """Test mapping of array types."""
        mapper = UtilityTypeMapper()

        # Simple array
        schema = ModelSchema(
            schema_type="array", items=ModelSchema(schema_type="string")
        )
        assert mapper.get_type_string_from_schema(schema) == "List[str]"

        # Array with ref
        schema = ModelSchema(
            schema_type="array", items=ModelSchema(ref="#/definitions/ModelUser")
        )
        assert mapper.get_type_string_from_schema(schema) == "List[ModelUser]"

    def test_object_type_mapping(self):
        """Test mapping of object types."""
        mapper = UtilityTypeMapper()

        # Object without properties
        schema = ModelSchema(schema_type="object")
        assert mapper.get_type_string_from_schema(schema) == "Dict[str, Any]"

        # Object with properties
        schema = ModelSchema(
            schema_type="object", properties={"name": ModelSchema(schema_type="string")}
        )
        assert mapper.get_type_string_from_schema(schema) == "ModelObjectData"

    def test_enum_name_generation(self):
        """Test enum name generation from values."""
        mapper = UtilityTypeMapper()

        # Single word enum
        assert mapper.generate_enum_name_from_values(["success"]) == "EnumSuccess"

        # Snake case enum
        assert (
            mapper.generate_enum_name_from_values(["validation_error"])
            == "EnumValidationError"
        )

        # Empty enum
        assert mapper.generate_enum_name_from_values([]) == "EnumGeneric"

    def test_reference_resolution(self):
        """Test reference resolution."""
        mapper = UtilityTypeMapper()

        # Internal reference
        assert mapper.resolve_ref_name("#/definitions/User") == "ModelUser"
        assert mapper.resolve_ref_name("#/definitions/ModelUser") == "ModelUser"

        # External reference
        assert (
            mapper.resolve_ref_name("contracts/contract_models.yaml#/ProcessingConfig")
            == "ModelProcessingConfig"
        )

    def test_import_detection(self):
        """Test import statement generation."""
        mapper = UtilityTypeMapper()

        # Typing imports
        assert mapper.get_import_for_type("List[str]") == "from typing import List"
        assert mapper.get_import_for_type("Dict[str, Any]") == "from typing import Dict"
        assert mapper.get_import_for_type("Any") == "from typing import Any"

        # Model imports
        assert (
            mapper.get_import_for_type("ModelObjectData")
            == "from omnibase_core.model.core.model_object_data import ModelObjectData"
        )

        # No import needed
        assert mapper.get_import_for_type("str") is None
        assert mapper.get_import_for_type("int") is None

    def test_model_type_detection(self):
        """Test detection of model types."""
        mapper = UtilityTypeMapper()

        # Model types
        assert mapper.is_model_type("ModelUser") is True
        assert mapper.is_model_type("EnumStatus") is True

        # Model in generic
        assert mapper.is_model_type("List[ModelUser]") is True
        assert mapper.is_model_type("Dict[str, ModelConfig]") is True

        # Not model types
        assert mapper.is_model_type("str") is False
        assert mapper.is_model_type("List[int]") is False

    def test_with_reference_resolver(self):
        """Test type mapper with injected reference resolver."""

        class MockResolver:
            def _resolve_ref_name(self, ref: str) -> str:
                return "MockResolved"

        mapper = UtilityTypeMapper(reference_resolver=MockResolver())

        schema = ModelSchema(ref="#/definitions/Something")
        assert mapper.get_type_string_from_schema(schema) == "MockResolved"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
