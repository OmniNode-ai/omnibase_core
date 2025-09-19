"""
Test node models export functionality.

Validates that all exported models work correctly and that the
__all__ declarations are properly maintained.
"""

import inspect
from typing import Any, Dict, List, Type

import pytest

from omnibase_core.models.nodes import (
    ModelCliNodeExecutionInput,
    ModelMetadataNodeCollection,
    ModelNodeCapability,
    ModelNodeInformation,
    ModelNodeType,
    __all__,
)


class TestNodeExports:
    """Test exports for node domain models."""

    def test_all_declaration_completeness(self):
        """Test that __all__ includes all intended exports."""
        expected_exports = {
            'ModelCliNodeExecutionInput',
            'ModelMetadataNodeCollection',
            'ModelNodeCapability',
            'ModelNodeInformation',
            'ModelNodeType',
        }

        assert set(__all__) == expected_exports, f"__all__ mismatch: {set(__all__)} vs {expected_exports}"

    def test_all_exports_are_importable(self):
        """Test that all items in __all__ can be imported."""
        import omnibase_core.models.nodes as nodes_module

        for export_name in __all__:
            assert hasattr(nodes_module, export_name), f"Missing export: {export_name}"
            exported_item = getattr(nodes_module, export_name)
            assert exported_item is not None

    def test_all_exports_are_classes(self):
        """Test that all exports are proper class types."""
        import omnibase_core.models.nodes as nodes_module

        for export_name in __all__:
            exported_item = getattr(nodes_module, export_name)
            assert inspect.isclass(exported_item), f"{export_name} is not a class"

    def test_exported_classes_have_proper_bases(self):
        """Test that exported classes inherit from BaseModel or appropriate base."""
        import omnibase_core.models.nodes as nodes_module
        from pydantic import BaseModel, RootModel

        for export_name in __all__:
            exported_class = getattr(nodes_module, export_name)

            # Check inheritance chain
            assert (
                issubclass(exported_class, BaseModel) or
                issubclass(exported_class, RootModel)
            ), f"{export_name} doesn't inherit from BaseModel or RootModel"

    def test_exported_classes_have_docstrings(self):
        """Test that all exported classes have documentation."""
        import omnibase_core.models.nodes as nodes_module

        for export_name in __all__:
            exported_class = getattr(nodes_module, export_name)
            assert exported_class.__doc__ is not None, f"{export_name} lacks docstring"
            assert len(exported_class.__doc__.strip()) > 0, f"{export_name} has empty docstring"

    def test_no_private_exports(self):
        """Test that no private classes/functions are accidentally exported."""
        import omnibase_core.models.nodes as nodes_module

        for export_name in __all__:
            assert not export_name.startswith('_'), f"Private item {export_name} in __all__"

    def test_export_consistency_with_module_attrs(self):
        """Test that module attributes match __all__ declaration."""
        import omnibase_core.models.nodes as nodes_module

        # Get all public attributes
        public_attrs = [name for name in dir(nodes_module) if not name.startswith('_')]

        # Filter to only classes (not functions or modules)
        public_classes = [
            name for name in public_attrs
            if inspect.isclass(getattr(nodes_module, name))
        ]

        # Should match __all__ exactly
        assert set(public_classes) == set(__all__), f"Public classes {public_classes} != __all__ {__all__}"

    @pytest.mark.parametrize("export_name", __all__)
    def test_individual_export_properties(self, export_name):
        """Test properties of each exported class."""
        import omnibase_core.models.nodes as nodes_module

        exported_class = getattr(nodes_module, export_name)

        # Should be a class
        assert inspect.isclass(exported_class)

        # Should have proper naming
        assert exported_class.__name__ == export_name

        # Should have module reference
        assert exported_class.__module__.startswith('omnibase_core.models.nodes')

    def test_pydantic_model_features_exported(self):
        """Test that exported models have Pydantic features."""
        import omnibase_core.models.nodes as nodes_module

        for export_name in __all__:
            exported_class = getattr(nodes_module, export_name)

            # Should have Pydantic model features
            expected_attrs = ['model_fields', 'model_validate', 'model_dump']
            for attr in expected_attrs:
                assert hasattr(exported_class, attr), f"{export_name} missing {attr}"

    def test_model_serialization_works(self):
        """Test that exported models can be serialized/deserialized."""
        test_data = {
            'ModelCliNodeExecutionInput': {'action': 'test'},
            'ModelMetadataNodeCollection': {},
            'ModelNodeCapability': None,  # Factory method
            'ModelNodeInformation': {
                'node_id': 'test',
                'node_name': 'test',
                'node_type': 'test',
                'node_version': '1.0.0'
            },
            'ModelNodeType': None,  # Factory method
        }

        import omnibase_core.models.nodes as nodes_module

        for export_name in __all__:
            exported_class = getattr(nodes_module, export_name)

            try:
                if export_name in ['ModelNodeCapability', 'ModelNodeType']:
                    # Use factory methods
                    if export_name == 'ModelNodeCapability':
                        instance = exported_class.SUPPORTS_DRY_RUN()
                    else:
                        instance = exported_class.CONTRACT_TO_MODEL()
                else:
                    # Use direct instantiation
                    instance = exported_class(**test_data[export_name])

                # Test serialization
                serialized = instance.model_dump()
                assert isinstance(serialized, dict)

                # Test deserialization
                if export_name not in ['ModelNodeCapability', 'ModelNodeType']:
                    restored = exported_class.model_validate(serialized)
                    assert restored is not None

            except Exception as e:
                pytest.fail(f"Serialization failed for {export_name}: {e}")

    def test_factory_methods_available(self):
        """Test that factory methods are available for appropriate models."""
        factory_models = {
            'ModelNodeCapability': [
                'SUPPORTS_DRY_RUN',
                'SUPPORTS_BATCH_PROCESSING',
                'SUPPORTS_CUSTOM_HANDLERS',
                'TELEMETRY_ENABLED',
                'SUPPORTS_CORRELATION_ID',
                'SUPPORTS_EVENT_BUS',
                'SUPPORTS_SCHEMA_VALIDATION',
                'SUPPORTS_ERROR_RECOVERY',
                'SUPPORTS_EVENT_DISCOVERY',
            ],
            'ModelNodeType': [
                'CONTRACT_TO_MODEL',
                'MULTI_DOC_MODEL_GENERATOR',
                'GENERATE_ERROR_CODES',
                'GENERATE_INTROSPECTION',
                'NODE_GENERATOR',
                'TEMPLATE_ENGINE',
                'FILE_GENERATOR',
                'TEMPLATE_VALIDATOR',
                'VALIDATION_ENGINE',
            ],
        }

        import omnibase_core.models.nodes as nodes_module

        for model_name, methods in factory_models.items():
            exported_class = getattr(nodes_module, model_name)

            for method_name in methods:
                assert hasattr(exported_class, method_name), f"{model_name} missing {method_name}"
                method = getattr(exported_class, method_name)
                assert callable(method), f"{method_name} is not callable"

    def test_model_validation_works(self):
        """Test that model validation works for exported models."""
        import omnibase_core.models.nodes as nodes_module

        # Test valid data
        valid_data = {
            'ModelCliNodeExecutionInput': {'action': 'test_action'},
            'ModelMetadataNodeCollection': {},
            'ModelNodeInformation': {
                'node_id': 'test_id',
                'node_name': 'test_name',
                'node_type': 'test_type',
                'node_version': '1.0.0'
            },
        }

        for model_name, data in valid_data.items():
            exported_class = getattr(nodes_module, model_name)

            # Should not raise
            instance = exported_class.model_validate(data)
            assert instance is not None

    def test_invalid_data_validation_fails(self):
        """Test that invalid data properly fails validation."""
        import omnibase_core.models.nodes as nodes_module

        # Test invalid data
        invalid_data = {
            'ModelCliNodeExecutionInput': {},  # Missing required 'action'
            'ModelNodeInformation': {},  # Missing required fields
        }

        for model_name, data in invalid_data.items():
            exported_class = getattr(nodes_module, model_name)

            with pytest.raises(Exception):  # Should raise validation error
                exported_class.model_validate(data)

    def test_export_stability(self):
        """Test that exports remain stable across multiple imports."""
        # Import multiple times and ensure classes are the same
        import omnibase_core.models.nodes as nodes1
        import omnibase_core.models.nodes as nodes2

        for export_name in __all__:
            class1 = getattr(nodes1, export_name)
            class2 = getattr(nodes2, export_name)
            assert class1 is class2, f"{export_name} not stable across imports"

    def test_export_module_metadata(self):
        """Test that exported classes have correct module metadata."""
        import omnibase_core.models.nodes as nodes_module

        for export_name in __all__:
            exported_class = getattr(nodes_module, export_name)

            # Check module metadata
            assert hasattr(exported_class, '__module__')
            assert exported_class.__module__.startswith('omnibase_core.models.nodes')

            # Check name metadata
            assert hasattr(exported_class, '__name__')
            assert exported_class.__name__ == export_name