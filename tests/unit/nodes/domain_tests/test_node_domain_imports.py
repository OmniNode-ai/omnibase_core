"""
Test node domain import validation.

Validates that all node models can be imported correctly from their
reorganized locations and that exports work as expected.
"""

import importlib
import sys
from typing import Type, Union
from unittest.mock import patch

import pytest

from omnibase_core.models.nodes import (
    ModelCliNodeExecutionInput,
    ModelMetadataNodeCollection,
    ModelNodeCapability,
    ModelNodeInformation,
    ModelNodeType,
)


class TestNodeDomainImports:
    """Test imports for node domain reorganization."""

    def test_direct_imports_available(self):
        """Test that all node models can be imported directly."""
        # Test that the models are imported correctly
        assert ModelCliNodeExecutionInput is not None
        assert ModelMetadataNodeCollection is not None
        assert ModelNodeCapability is not None
        assert ModelNodeInformation is not None
        assert ModelNodeType is not None

    def test_module_level_imports(self):
        """Test that models can be imported at module level."""
        from omnibase_core.models import nodes

        assert hasattr(nodes, 'ModelCliNodeExecutionInput')
        assert hasattr(nodes, 'ModelMetadataNodeCollection')
        assert hasattr(nodes, 'ModelNodeCapability')
        assert hasattr(nodes, 'ModelNodeInformation')
        assert hasattr(nodes, 'ModelNodeType')

    def test_nodes_module_structure(self):
        """Test the nodes module structure is correct."""
        import omnibase_core.models.nodes as nodes_module

        # Check __all__ exists and contains expected exports
        assert hasattr(nodes_module, '__all__')
        expected_exports = {
            'ModelCliNodeExecutionInput',
            'ModelMetadataNodeCollection',
            'ModelNodeCapability',
            'ModelNodeInformation',
            'ModelNodeType',
        }
        assert set(nodes_module.__all__) == expected_exports

    def test_backwards_compatibility_imports(self):
        """Test that imports still work with full paths."""
        # Test full import paths work
        from omnibase_core.models.nodes.model_cli_node_execution_input import ModelCliNodeExecutionInput as CLI
        from omnibase_core.models.nodes.model_metadata_node_collection import ModelMetadataNodeCollection as Collection
        from omnibase_core.models.nodes.model_node_capability import ModelNodeCapability as Capability
        from omnibase_core.models.nodes.model_node_information import ModelNodeInformation as Information
        from omnibase_core.models.nodes.model_node_type import ModelNodeType as NodeType

        # Verify they're the same classes
        assert CLI is ModelCliNodeExecutionInput
        assert Collection is ModelMetadataNodeCollection
        assert Capability is ModelNodeCapability
        assert Information is ModelNodeInformation
        assert NodeType is ModelNodeType

    def test_dynamic_import_functionality(self):
        """Test dynamic imports work correctly."""
        # Test dynamic import of the nodes module
        nodes_module = importlib.import_module('omnibase_core.models.nodes')

        # Test each model can be accessed dynamically
        models = [
            'ModelCliNodeExecutionInput',
            'ModelMetadataNodeCollection',
            'ModelNodeCapability',
            'ModelNodeInformation',
            'ModelNodeType',
        ]

        for model_name in models:
            assert hasattr(nodes_module, model_name)
            model_class = getattr(nodes_module, model_name)
            assert isinstance(model_class, type)

    def test_import_performance(self):
        """Test that imports are performant and don't cause circular imports."""
        import time

        start_time = time.time()

        # Import the module fresh
        if 'omnibase_core.models.nodes' in sys.modules:
            del sys.modules['omnibase_core.models.nodes']

        import omnibase_core.models.nodes

        import_time = time.time() - start_time

        # Import should be fast (less than 100ms)
        assert import_time < 0.1, f"Import took {import_time:.3f}s, too slow"

    def test_no_circular_imports(self):
        """Test that there are no circular import issues."""
        # This test will fail if there are circular imports
        import importlib

        # Force reimport to detect circular imports
        modules_to_test = [
            'omnibase_core.models.nodes.model_cli_node_execution_input',
            'omnibase_core.models.nodes.model_metadata_node_collection',
            'omnibase_core.models.nodes.model_node_capability',
            'omnibase_core.models.nodes.model_node_information',
            'omnibase_core.models.nodes.model_node_type',
        ]

        for module_name in modules_to_test:
            if module_name in sys.modules:
                del sys.modules[module_name]

            # This should not raise ImportError due to circular imports
            module = importlib.import_module(module_name)
            assert module is not None

    def test_import_error_handling(self):
        """Test proper error handling for missing imports."""
        with pytest.raises(ImportError):
            from omnibase_core.models.nodes import NonExistentModel

    def test_pydantic_model_registration(self):
        """Test that all models are properly registered as Pydantic models."""
        models = [
            ModelCliNodeExecutionInput,
            ModelMetadataNodeCollection,
            ModelNodeCapability,
            ModelNodeInformation,
            ModelNodeType,
        ]

        for model in models:
            # Test Pydantic features work
            assert hasattr(model, 'model_fields')
            assert hasattr(model, 'model_validate')
            assert hasattr(model, 'model_dump')

    def test_star_import_functionality(self):
        """Test that star imports work correctly."""
        # This should import all models
        exec("from omnibase_core.models.nodes import *")

        # Check that models are available in local scope
        local_vars = locals()
        expected_models = [
            'ModelCliNodeExecutionInput',
            'ModelMetadataNodeCollection',
            'ModelNodeCapability',
            'ModelNodeInformation',
            'ModelNodeType',
        ]

        for model_name in expected_models:
            assert model_name in local_vars

    @pytest.mark.parametrize("model_class", [
        ModelCliNodeExecutionInput,
        ModelMetadataNodeCollection,
        ModelNodeCapability,
        ModelNodeInformation,
        ModelNodeType,
    ])
    def test_model_instantiation_after_import(self, model_class):
        """Test that models can be instantiated after import."""
        # Test basic instantiation doesn't fail
        try:
            if model_class == ModelCliNodeExecutionInput:
                instance = model_class(action="test")
            elif model_class == ModelMetadataNodeCollection:
                instance = model_class({})
            elif model_class == ModelNodeCapability:
                instance = model_class.SUPPORTS_DRY_RUN()
            elif model_class == ModelNodeInformation:
                instance = model_class(
                    node_id="test",
                    node_name="test",
                    node_type="test",
                    node_version="1.0.0"
                )
            elif model_class == ModelNodeType:
                instance = model_class.CONTRACT_TO_MODEL()

            assert instance is not None
        except Exception as e:
            pytest.fail(f"Failed to instantiate {model_class.__name__}: {e}")

    def test_module_docstring_and_metadata(self):
        """Test that module has proper documentation."""
        import omnibase_core.models.nodes as nodes_module

        # Check module docstring exists
        assert nodes_module.__doc__ is not None
        assert "ONEX Nodes Domain Models" in nodes_module.__doc__

    def test_import_isolation(self):
        """Test that imports don't pollute global namespace."""
        import omnibase_core.models.nodes

        # Check that internal implementation details aren't exported
        internal_modules = [
            'pydantic',
            'datetime',
            'typing',
            'hashlib',
        ]

        for internal in internal_modules:
            assert not hasattr(omnibase_core.models.nodes, internal)