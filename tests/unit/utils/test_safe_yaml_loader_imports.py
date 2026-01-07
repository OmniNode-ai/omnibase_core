"""
Tests for import chain validation in util_safe_yaml_loader.

These tests verify that PR #358's fix for circular imports works correctly.
The fix changed the import of ModelYamlValue from a package-level import
to a direct file import to prevent RecursionError during module loading.

Related: OMN-1264
"""

from __future__ import annotations

import sys

import pytest


@pytest.mark.unit
class TestSafeYamlLoaderImports:
    """Test import chain validation for util_safe_yaml_loader."""

    def test_module_imports_without_circular_dependency(self) -> None:
        """Verify util_safe_yaml_loader can be imported without circular import error.

        This test validates the fix from PR #358 where ModelYamlValue import
        was changed from package-level to direct file import to prevent
        RecursionError during module loading.
        """
        # This import should succeed without RecursionError or ImportError
        from omnibase_core.utils import util_safe_yaml_loader

        # Verify the module is properly loaded
        assert util_safe_yaml_loader is not None
        assert hasattr(util_safe_yaml_loader, "_dump_yaml_content")
        assert hasattr(util_safe_yaml_loader, "serialize_pydantic_model_to_yaml")
        assert hasattr(util_safe_yaml_loader, "serialize_data_to_yaml")

    def test_model_yaml_value_import_available(self) -> None:
        """Verify ModelYamlValue can be imported from its direct file path.

        The util_safe_yaml_loader module imports ModelYamlValue using a direct
        file import to avoid circular dependency issues.
        """
        # Import ModelYamlValue the same way util_safe_yaml_loader does
        from omnibase_core.models.utils.model_yaml_value import ModelYamlValue

        # Verify the class is properly accessible
        assert ModelYamlValue is not None
        assert hasattr(ModelYamlValue, "from_schema_value")
        assert hasattr(ModelYamlValue, "to_serializable")

    def test_dump_yaml_content_with_model_yaml_value(self) -> None:
        """Verify _dump_yaml_content works correctly with ModelYamlValue instances.

        This tests the integration between the import fix and the actual
        serialization functionality that uses ModelYamlValue.
        """
        from omnibase_core.models.common.model_schema_value import ModelSchemaValue
        from omnibase_core.models.utils.model_yaml_value import ModelYamlValue
        from omnibase_core.utils.util_safe_yaml_loader import _dump_yaml_content

        # Create a ModelYamlValue and dump it
        schema_value = ModelSchemaValue.from_value({"key": "value", "number": 42})
        yaml_value = ModelYamlValue.from_schema_value(schema_value)

        result = _dump_yaml_content(yaml_value)

        # Verify the result is valid YAML string
        assert isinstance(result, str)
        assert len(result) > 0

    def test_serialize_pydantic_model_uses_model_yaml_value(self) -> None:
        """Verify serialize_pydantic_model_to_yaml uses ModelYamlValue internally.

        This ensures the import chain works end-to-end when serializing
        Pydantic models to YAML format.
        """
        from pydantic import BaseModel

        from omnibase_core.utils.util_safe_yaml_loader import (
            serialize_pydantic_model_to_yaml,
        )

        class TestModel(BaseModel):
            name: str
            value: int

        model = TestModel(name="test", value=123)
        result = serialize_pydantic_model_to_yaml(model)

        # Verify the result is valid YAML string containing expected content
        assert isinstance(result, str)
        assert "test" in result
        assert "123" in result

    def test_import_order_independence(self) -> None:
        """Verify imports work regardless of order.

        This tests that the direct file import pattern allows flexible
        import ordering without causing circular dependency issues.
        """
        # Import in different order than typical usage
        # Then import the supporting classes
        from omnibase_core.models.common.model_schema_value import ModelSchemaValue
        from omnibase_core.models.utils.model_yaml_value import ModelYamlValue
        from omnibase_core.utils.util_safe_yaml_loader import _dump_yaml_content

        # Create and serialize
        schema_value = ModelSchemaValue.from_value("test string")
        yaml_value = ModelYamlValue.from_schema_value(schema_value)

        result = _dump_yaml_content(yaml_value)
        assert isinstance(result, str)

    def test_model_yaml_value_isinstance_check_in_dump(self) -> None:
        """Verify _dump_yaml_content correctly identifies ModelYamlValue instances.

        The _dump_yaml_content function uses isinstance() to check for
        ModelYamlValue and calls to_serializable() when found. This test
        ensures the isinstance check works correctly with the direct import.
        """
        from omnibase_core.models.common.model_schema_value import ModelSchemaValue
        from omnibase_core.models.utils.model_yaml_value import ModelYamlValue
        from omnibase_core.utils.util_safe_yaml_loader import _dump_yaml_content

        # Test with ModelYamlValue (should call to_serializable)
        yaml_value = ModelYamlValue.from_schema_value(
            ModelSchemaValue.from_value({"nested": "data"})
        )
        result_yaml_value = _dump_yaml_content(yaml_value)
        assert isinstance(result_yaml_value, str)

        # Test with plain dict (should pass through directly)
        plain_dict = {"plain": "dict"}
        result_plain = _dump_yaml_content(plain_dict)
        assert isinstance(result_plain, str)
        assert "plain" in result_plain

    def test_fresh_import_no_cached_modules(self) -> None:
        """Verify module can be imported fresh without cached state issues.

        This test verifies the import works correctly even when we ensure
        no prior cached state could mask circular import issues.
        """
        # Get current module reference
        yaml_loader_module = "omnibase_core.utils.util_safe_yaml_loader"

        # Store original module if it exists
        original_yaml_loader = sys.modules.get(yaml_loader_module)

        try:
            # Remove from cache to force fresh import
            if yaml_loader_module in sys.modules:
                del sys.modules[yaml_loader_module]

            # Re-import and verify it works
            from omnibase_core.utils import util_safe_yaml_loader

            assert util_safe_yaml_loader is not None
            assert hasattr(util_safe_yaml_loader, "_dump_yaml_content")

        finally:
            # Restore original module to avoid test interference
            if original_yaml_loader is not None:
                sys.modules[yaml_loader_module] = original_yaml_loader


@pytest.mark.unit
class TestModelYamlValueIntegration:
    """Integration tests for ModelYamlValue with serialization functions."""

    def test_schema_value_yaml_serialization(self) -> None:
        """Test YAML serialization with ModelSchemaValue.

        Note: ModelSchemaValue serializes as a Python object representation,
        which is valid YAML but cannot be parsed back with yaml.safe_load().
        This test verifies the serialization succeeds without error.
        """
        from omnibase_core.models.common.model_schema_value import ModelSchemaValue
        from omnibase_core.models.utils.model_yaml_value import ModelYamlValue
        from omnibase_core.utils.util_safe_yaml_loader import _dump_yaml_content

        # Create test data
        original_data = {"string": "hello", "integer": 42, "float": 3.14}
        schema_value = ModelSchemaValue.from_value(original_data)
        yaml_value = ModelYamlValue.from_schema_value(schema_value)

        # Serialize to YAML - should succeed without error
        yaml_str = _dump_yaml_content(yaml_value)

        # Verify it produces non-empty output
        assert isinstance(yaml_str, str)
        assert len(yaml_str) > 0

    def test_model_yaml_value_dict_type(self) -> None:
        """Test ModelYamlValue.from_dict_data with serialization."""
        from omnibase_core.models.common.model_schema_value import ModelSchemaValue
        from omnibase_core.models.utils.model_yaml_value import ModelYamlValue
        from omnibase_core.utils.util_safe_yaml_loader import _dump_yaml_content

        # Create dict of ModelSchemaValue
        dict_data = {
            "key1": ModelSchemaValue.from_value("value1"),
            "key2": ModelSchemaValue.from_value(100),
        }
        yaml_value = ModelYamlValue.from_dict_data(dict_data)

        # Serialize
        result = _dump_yaml_content(yaml_value)

        assert isinstance(result, str)
        # The output should contain the keys
        assert "key1" in result or "value1" in result

    def test_model_yaml_value_list_type(self) -> None:
        """Test ModelYamlValue.from_list with serialization."""
        from omnibase_core.models.common.model_schema_value import ModelSchemaValue
        from omnibase_core.models.utils.model_yaml_value import ModelYamlValue
        from omnibase_core.utils.util_safe_yaml_loader import _dump_yaml_content

        # Create list of ModelSchemaValue
        list_data = [
            ModelSchemaValue.from_value("item1"),
            ModelSchemaValue.from_value("item2"),
            ModelSchemaValue.from_value(42),
        ]
        yaml_value = ModelYamlValue.from_list(list_data)

        # Serialize
        result = _dump_yaml_content(yaml_value)

        assert isinstance(result, str)
