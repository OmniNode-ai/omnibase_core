"""
Tests for model_schema.py module.

This module tests the schema validation models and their compatibility aliases.
"""

import pytest


class TestModelSchemaModule:
    """Test the model_schema module structure and imports."""

    def test_module_imports(self):
        """Test that all expected classes can be imported."""
        from omnibase_core.models.validation.model_schema import (
            ModelRequiredFieldsModel,
            ModelSchema,
            ModelSchemaPropertiesModel,
            RequiredFieldsModel,
            SchemaModel,
            SchemaPropertiesModel,
            SchemaPropertyModel,
        )

        # Verify all classes are imported
        assert ModelSchema is not None
        assert ModelSchemaPropertiesModel is not None
        assert ModelRequiredFieldsModel is not None
        assert SchemaPropertyModel is not None
        assert SchemaPropertiesModel is not None
        assert RequiredFieldsModel is not None
        assert SchemaModel is not None

    def test_compatibility_aliases(self):
        """Test that compatibility aliases point to correct classes."""
        from omnibase_core.models.validation.model_required_fields_model import (
            ModelRequiredFieldsModel,
        )
        from omnibase_core.models.validation.model_schema import (
            ModelRequiredFieldsModel,
            ModelSchema,
            ModelSchemaPropertiesModel,
            RequiredFieldsModel,
            SchemaModel,
            SchemaPropertiesModel,
            SchemaPropertyModel,
        )
        from omnibase_core.models.validation.model_schema_class import ModelSchema
        from omnibase_core.models.validation.model_schema_properties_model import (
            ModelSchemaPropertiesModel,
        )

        # Import the actual classes to compare
        from omnibase_core.models.validation.model_schema_property import (
            ModelSchemaProperty,
        )

        # Test that aliases point to the correct classes
        assert SchemaPropertyModel is ModelSchemaProperty
        assert SchemaPropertiesModel is ModelSchemaPropertiesModel
        assert RequiredFieldsModel is ModelRequiredFieldsModel
        assert SchemaModel is ModelSchema

    def test_module_all_exports(self):
        """Test that __all__ contains all expected exports."""
        from omnibase_core.models.validation import model_schema

        expected_exports = [
            "ModelSchema",
            "ModelSchemaPropertiesModel",
            "ModelRequiredFieldsModel",
            "SchemaPropertyModel",
            "SchemaPropertiesModel",
            "RequiredFieldsModel",
            "SchemaModel",
        ]

        # Check that all expected exports are in __all__
        assert hasattr(model_schema, "__all__")
        for export in expected_exports:
            assert export in model_schema.__all__

    def test_import_from_module(self):
        """Test importing classes from the module."""
        from omnibase_core.models.validation.model_schema import (
            ModelRequiredFieldsModel,
            ModelSchema,
            ModelSchemaPropertiesModel,
        )

        # Verify classes are accessible
        assert ModelSchema is not None
        assert ModelSchemaPropertiesModel is not None
        assert ModelRequiredFieldsModel is not None

    def test_compatibility_aliases_functionality(self):
        """Test that compatibility aliases work correctly."""
        from omnibase_core.models.validation.model_required_fields_model import (
            ModelRequiredFieldsModel,
        )
        from omnibase_core.models.validation.model_schema import (
            RequiredFieldsModel,
            SchemaModel,
            SchemaPropertiesModel,
            SchemaPropertyModel,
        )
        from omnibase_core.models.validation.model_schema_class import ModelSchema
        from omnibase_core.models.validation.model_schema_properties_model import (
            ModelSchemaPropertiesModel,
        )

        # Test that aliases are the same as their original classes
        from omnibase_core.models.validation.model_schema_property import (
            ModelSchemaProperty,
        )

        assert SchemaPropertyModel is ModelSchemaProperty
        assert SchemaPropertiesModel is ModelSchemaPropertiesModel
        assert RequiredFieldsModel is ModelRequiredFieldsModel
        assert SchemaModel is ModelSchema

    def test_module_structure(self):
        """Test that the module has expected structure."""
        import omnibase_core.models.validation.model_schema as module

        # Module should exist and be importable
        assert module is not None

        # Should have all expected attributes
        expected_attrs = [
            "ModelSchema",
            "ModelSchemaPropertiesModel",
            "ModelRequiredFieldsModel",
            "SchemaPropertyModel",
            "SchemaPropertiesModel",
            "RequiredFieldsModel",
            "SchemaModel",
        ]

        for attr in expected_attrs:
            assert hasattr(module, attr)

    def test_import_paths(self):
        """Test that classes can be imported via different paths."""
        # Direct import from module
        # Import from package
        from omnibase_core.models.validation import model_schema
        from omnibase_core.models.validation.model_schema import (
            ModelSchema as DirectModelSchema,
        )

        PackageModelSchema = model_schema.ModelSchema

        # Both should be the same
        assert DirectModelSchema is PackageModelSchema

    def test_class_availability(self):
        """Test that all classes are available and importable."""
        from omnibase_core.models.validation.model_schema import (
            ModelRequiredFieldsModel,
            ModelSchema,
            ModelSchemaPropertiesModel,
            RequiredFieldsModel,
            SchemaModel,
            SchemaPropertiesModel,
            SchemaPropertyModel,
        )

        # All classes should be available
        classes = [
            ModelSchema,
            ModelSchemaPropertiesModel,
            ModelRequiredFieldsModel,
            SchemaPropertyModel,
            SchemaPropertiesModel,
            RequiredFieldsModel,
            SchemaModel,
        ]

        for cls in classes:
            assert cls is not None
            assert hasattr(cls, "__name__")

    def test_module_docstring(self):
        """Test that the module has proper docstring."""
        import omnibase_core.models.validation.model_schema as module

        # Module should have docstring
        assert module.__doc__ is not None
        assert "Schema validation models" in module.__doc__

    def test_import_error_handling(self):
        """Test that import errors are handled properly."""
        # Test that we can import the module without errors
        try:
            from omnibase_core.models.validation.model_schema import ModelSchema

            assert ModelSchema is not None
        except ImportError as e:
            pytest.fail(f"Failed to import ModelSchema: {e}")

    def test_class_inheritance(self):
        """Test that imported classes have expected inheritance."""
        from omnibase_core.models.validation.model_schema import ModelSchema

        # ModelSchema should be a class
        assert isinstance(ModelSchema, type)

        # Should have expected methods if it's a Pydantic model
        if hasattr(ModelSchema, "model_validate"):
            assert callable(ModelSchema.model_validate)
        if hasattr(ModelSchema, "model_dump"):
            assert callable(ModelSchema.model_dump)

    def test_module_metadata(self):
        """Test that the module has expected metadata."""
        import omnibase_core.models.validation.model_schema as module

        # Module should have __file__ attribute
        assert hasattr(module, "__file__")

        # Module should have __name__ attribute
        assert hasattr(module, "__name__")
        assert module.__name__ == "omnibase_core.models.validation.model_schema"
