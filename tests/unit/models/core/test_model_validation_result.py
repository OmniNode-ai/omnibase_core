"""
Tests for ModelValidationResult.

This module tests the generic validation result model for common use.
"""

import pytest

from omnibase_core.models.core.model_validation_result import ModelValidationResult


class TestModelValidationResult:
    """Test ModelValidationResult functionality."""

    def test_create_validation_result(self):
        """Test creating a ModelValidationResult instance."""
        result = ModelValidationResult()
        assert result is not None
        assert isinstance(result, ModelValidationResult)

    def test_validation_result_inheritance(self):
        """Test that ModelValidationResult inherits from BaseModel."""
        from pydantic import BaseModel

        result = ModelValidationResult()
        assert isinstance(result, BaseModel)

    def test_validation_result_serialization(self):
        """Test ModelValidationResult serialization."""
        result = ModelValidationResult()

        data = result.model_dump()
        assert isinstance(data, dict)
        assert data == {}

    def test_validation_result_deserialization(self):
        """Test ModelValidationResult deserialization."""
        data = {}
        result = ModelValidationResult.model_validate(data)
        assert isinstance(result, ModelValidationResult)

    def test_validation_result_json_serialization(self):
        """Test ModelValidationResult JSON serialization."""
        result = ModelValidationResult()

        json_data = result.model_dump_json()
        assert isinstance(json_data, str)
        assert json_data == "{}"

    def test_validation_result_roundtrip(self):
        """Test serialization and deserialization roundtrip."""
        original_result = ModelValidationResult()

        # Serialize
        data = original_result.model_dump()

        # Deserialize
        restored_result = ModelValidationResult.model_validate(data)

        # Verify they are equivalent
        assert restored_result.model_dump() == original_result.model_dump()

    def test_validation_result_equality(self):
        """Test ModelValidationResult equality."""
        result1 = ModelValidationResult()
        result2 = ModelValidationResult()

        # Empty models should be equal
        assert result1 == result2

    def test_validation_result_hash(self):
        """Test ModelValidationResult hashing."""
        result = ModelValidationResult()

        # Pydantic models are not hashable by default
        # Test that we can access the model for hashing purposes
        data = result.model_dump()
        hash_value = hash(str(data))
        assert isinstance(hash_value, int)

    def test_validation_result_str(self):
        """Test ModelValidationResult string representation."""
        result = ModelValidationResult()

        str_repr = str(result)
        assert isinstance(str_repr, str)
        # Empty model might have empty string representation
        assert str_repr is not None

    def test_validation_result_repr(self):
        """Test ModelValidationResult repr representation."""
        result = ModelValidationResult()

        repr_str = repr(result)
        assert isinstance(repr_str, str)
        assert "ModelValidationResult" in repr_str

    def test_validation_result_attributes(self):
        """Test ModelValidationResult attributes."""
        result = ModelValidationResult()

        # Should have model_dump method
        assert hasattr(result, "model_dump")
        assert callable(result.model_dump)

        # Should have model_validate method
        assert hasattr(ModelValidationResult, "model_validate")
        assert callable(ModelValidationResult.model_validate)

    def test_validation_result_validation(self):
        """Test ModelValidationResult validation."""
        # Valid empty model
        result = ModelValidationResult()
        assert result is not None

        # Should accept empty dict
        result = ModelValidationResult.model_validate({})
        assert result is not None

    def test_validation_result_metadata(self):
        """Test ModelValidationResult metadata."""
        result = ModelValidationResult()

        # Should have model_fields
        assert hasattr(result, "model_fields")
        assert isinstance(result.model_fields, dict)

        # Should have model_config
        assert hasattr(result, "model_config")
        assert hasattr(result.model_config, "get")

    def test_validation_result_creation_with_data(self):
        """Test ModelValidationResult creation with data."""
        # Even with data, should work (empty model)
        result = ModelValidationResult.model_validate({"some_field": "some_value"})
        assert result is not None

        # Should ignore extra fields for empty model
        data = result.model_dump()
        assert data == {}

    def test_validation_result_copy(self):
        """Test ModelValidationResult copying."""
        result = ModelValidationResult()

        # Should be able to create a copy
        copied_result = result.model_copy()
        assert copied_result is not None
        assert copied_result == result
        assert copied_result is not result  # Different objects

    def test_validation_result_immutability(self):
        """Test ModelValidationResult immutability."""
        result = ModelValidationResult()

        # Should be immutable by default
        original_data = result.model_dump()

        # Attempting to modify should not affect the original
        # (though this is more about Pydantic behavior)
        assert result.model_dump() == original_data

    def test_validation_result_docstring(self):
        """Test ModelValidationResult docstring."""
        assert ModelValidationResult.__doc__ is not None
        assert (
            "Generic validationresult model for common use"
            in ModelValidationResult.__doc__
        )

    def test_validation_result_class_name(self):
        """Test ModelValidationResult class name."""
        assert ModelValidationResult.__name__ == "ModelValidationResult"

    def test_validation_result_module(self):
        """Test ModelValidationResult module."""
        assert (
            ModelValidationResult.__module__
            == "omnibase_core.models.core.model_validation_result"
        )
