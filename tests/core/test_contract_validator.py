"""
Tests for Enhanced Contract Validator code generation functionality.

These tests address the contract generation TODO items that were resolved
in the PR fixes.
"""

from pathlib import Path
from typing import Any

import pytest

from omnibase_core.core.contracts.enhanced_contract_validator import (
    EnhancedContractValidator,
    TypeGenerationSpec,
)


class TestEnhancedContractValidator:
    """Test cases for EnhancedContractValidator code generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = EnhancedContractValidator()

    def test_generate_pydantic_fields_basic(self):
        """Test Pydantic field generation with basic schema."""
        validator = EnhancedContractValidator()

        contract_data = {
            "schema": {
                "properties": {
                    "name": {"type": "string", "description": "User name"},
                    "age": {"type": "integer", "description": "User age"},
                }
            }
        }

        fields = validator._generate_pydantic_fields(contract_data)

        assert "name: str" in fields
        assert "age: int" in fields
        assert "User name" in fields
        assert "User age" in fields
        assert "Field(" in fields

    def test_generate_pydantic_fields_with_defaults(self):
        """Test Pydantic field generation with default values."""
        validator = EnhancedContractValidator()

        contract_data = {
            "schema": {
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Status field",
                        "default": "active",
                    },
                    "count": {
                        "type": "integer",
                        "description": "Count field",
                        "default": 0,
                    },
                }
            }
        }

        fields = validator._generate_pydantic_fields(contract_data)

        assert "status: str" in fields
        assert "count: int" in fields
        assert "default='active'" in fields
        assert "default=0" in fields

    def test_generate_pydantic_fields_empty_schema(self):
        """Test Pydantic field generation with empty schema."""
        validator = EnhancedContractValidator()

        contract_data = {"schema": {}}

        fields = validator._generate_pydantic_fields(contract_data)

        assert "data: Any" in fields
        assert "Contract data" in fields

    def test_generate_protocol_methods_basic(self):
        """Test Protocol method generation with operations."""
        validator = EnhancedContractValidator()

        contract_data = {
            "operations": [
                {
                    "name": "process_data",
                    "input_type": "str",
                    "output_type": "dict",
                    "description": "Process input data",
                },
                {
                    "name": "validate",
                    "input_type": "Any",
                    "output_type": "bool",
                    "description": "Validate input",
                },
            ]
        }

        methods = validator._generate_protocol_methods(contract_data)

        assert "async def process_data(self, input_data: str) -> dict:" in methods
        assert "async def validate(self, input_data: Any) -> bool:" in methods
        assert "Process input data" in methods
        assert "Validate input" in methods

    def test_generate_protocol_methods_empty(self):
        """Test Protocol method generation with no operations."""
        validator = EnhancedContractValidator()

        contract_data = {"operations": []}

        methods = validator._generate_protocol_methods(contract_data)

        assert "async def execute(self, input_data: Any) -> Any:" in methods
        assert "Execute the contract operation" in methods

    def test_generate_enum_values_basic(self):
        """Test enum value generation with string values."""
        validator = EnhancedContractValidator()

        contract_data = {"enum_values": ["active", "inactive", "pending"]}

        values = validator._generate_enum_values(contract_data)

        assert 'ACTIVE = "active"' in values
        assert 'INACTIVE = "inactive"' in values
        assert 'PENDING = "pending"' in values

    def test_generate_enum_values_complex(self):
        """Test enum value generation with complex specifications."""
        validator = EnhancedContractValidator()

        contract_data = {
            "enum_values": [
                {"name": "High Priority", "value": "high"},
                {"name": "Low Priority", "value": "low"},
            ]
        }

        values = validator._generate_enum_values(contract_data)

        assert 'HIGH_PRIORITY = "high"' in values
        assert 'LOW_PRIORITY = "low"' in values

    def test_generate_enum_values_empty(self):
        """Test enum value generation with no values."""
        validator = EnhancedContractValidator()

        contract_data = {"enum_values": []}

        values = validator._generate_enum_values(contract_data)

        assert 'UNKNOWN = "unknown"' in values
        assert 'DEFAULT = "default"' in values

    def test_map_json_schema_types(self):
        """Test JSON Schema type mapping to Python types."""
        validator = EnhancedContractValidator()

        # Test all supported type mappings
        assert validator._map_json_schema_type("string") == "str"
        assert validator._map_json_schema_type("integer") == "int"
        assert validator._map_json_schema_type("number") == "float"
        assert validator._map_json_schema_type("boolean") == "bool"
        assert validator._map_json_schema_type("array") == "list[Any]"
        assert validator._map_json_schema_type("object") == "dict[str, Any]"
        assert validator._map_json_schema_type("null") == "None"
        assert validator._map_json_schema_type("unknown_type") == "Any"

    def test_generate_pydantic_model_integration(self):
        """Test complete Pydantic model generation."""
        validator = EnhancedContractValidator()

        contract_data = {
            "contract_name": "test_contract",
            "node_name": "test_node",
            "description": "Test contract",
            "schema": {
                "properties": {"data": {"type": "string", "description": "Test data"}}
            },
        }

        spec = TypeGenerationSpec(
            source_path=Path("/test/contract.yaml"),
            target_path=Path("/test/output.py"),
            generation_mode="pydantic",
            naming_convention="PascalCase",
        )

        # This tests that the method calls our fixed implementation
        model_code = validator._generate_pydantic_model(contract_data, spec)

        # Verify the generated code contains expected elements
        assert "test_contract" in model_code
        assert "Test contract" in model_code
        assert (
            contract_data["description"] in model_code
            or "Generated model" in model_code
        )


if __name__ == "__main__":
    pytest.main([__file__])
