# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for model_config.py module.

This module tests the basic imports and structure of the events model_config module.
"""

import pytest


@pytest.mark.unit
class TestModelConfigModule:
    """Test the model_config module structure and imports."""

    def test_module_imports(self):
        """Test that the module can be imported successfully."""
        from omnibase_core.models.events.model_event_config import BaseModel

        # Verify BaseModel is imported
        assert BaseModel is not None
        assert hasattr(BaseModel, "model_validate")
        assert hasattr(BaseModel, "model_dump")

    def test_module_structure(self):
        """Test that the module has expected structure."""
        import omnibase_core.models.events.model_event_config as module

        # Module should exist and be importable
        assert module is not None

        # Should have BaseModel available
        assert hasattr(module, "BaseModel")

        # BaseModel should be the Pydantic BaseModel
        from pydantic import BaseModel as PydanticBaseModel

        assert module.BaseModel is PydanticBaseModel

    def test_base_model_functionality(self):
        """Test that BaseModel from the module works correctly."""
        from omnibase_core.models.events.model_event_config import BaseModel

        # Create a simple model using the imported BaseModel
        class TestModel(BaseModel):
            name: str
            value: int

        # Test model creation
        model = TestModel(name="test", value=42)
        assert model.name == "test"
        assert model.value == 42

        # Test serialization
        data = model.model_dump()
        assert data == {"name": "test", "value": 42}

        # Test deserialization
        restored = TestModel.model_validate(data)
        assert restored.name == "test"
        assert restored.value == 42

    def test_module_availability(self):
        """Test that the module is available in the events package."""
        from omnibase_core.models.events import model_event_base_config as model_config

        # Module should be accessible
        assert model_config is not None

        # Should have BaseModel
        assert hasattr(model_config, "BaseModel")

    def test_import_path(self):
        """Test that the module can be imported via different paths."""
        # Direct import
        # Package import
        from omnibase_core.models.events import model_event_base_config as model_config
        from omnibase_core.models.events.model_event_base_config import (
            BaseModel as DirectBaseModel,
        )

        PackageBaseModel = model_config.BaseModel

        # Both should be the same
        assert DirectBaseModel is PackageBaseModel

    def test_base_model_validation(self):
        """Test BaseModel validation functionality."""
        from omnibase_core.models.events.model_event_base_config import BaseModel

        class ValidationModel(BaseModel):
            required_field: str
            optional_field: int | None = None

        # Valid data
        valid_data = {"required_field": "test"}
        model = ValidationModel.model_validate(valid_data)
        assert model.required_field == "test"
        assert model.optional_field is None

        # With optional field
        valid_data_with_optional = {"required_field": "test", "optional_field": 42}
        model_with_optional = ValidationModel.model_validate(valid_data_with_optional)
        assert model_with_optional.required_field == "test"
        assert model_with_optional.optional_field == 42

        # Invalid data should raise validation error
        with pytest.raises(ValueError):
            ValidationModel.model_validate(
                {"optional_field": 42}
            )  # Missing required field

    def test_base_model_serialization(self):
        """Test BaseModel serialization functionality."""
        from omnibase_core.models.events.model_event_base_config import BaseModel

        class SerializationModel(BaseModel):
            name: str
            value: int
            metadata: dict | None = None

        model = SerializationModel(name="test", value=42, metadata={"key": "value"})

        # Test model_dump
        data = model.model_dump()
        expected = {"name": "test", "value": 42, "metadata": {"key": "value"}}
        assert data == expected

        # Test model_dump_json
        json_data = model.model_dump_json()
        assert isinstance(json_data, str)
        assert '"name":"test"' in json_data  # JSON doesn't have spaces around colons
        assert '"value":42' in json_data

    def test_base_model_inheritance(self):
        """Test that BaseModel can be inherited properly."""
        from omnibase_core.models.events.model_event_base_config import BaseModel

        class ParentModel(BaseModel):
            base_field: str

        class ChildModel(ParentModel):
            child_field: int

        # Test inheritance
        child = ChildModel(base_field="parent", child_field=42)
        assert child.base_field == "parent"
        assert child.child_field == 42

        # Test serialization of inherited model
        data = child.model_dump()
        assert data == {"base_field": "parent", "child_field": 42}
