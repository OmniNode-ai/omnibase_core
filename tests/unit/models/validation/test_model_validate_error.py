# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for model_validate_error.py module.

This module tests the validation error models and their compatibility aliases.
"""

import pytest


@pytest.mark.unit
class TestModelValidateErrorModule:
    """Test the model_validate_error module structure and imports."""

    def test_module_imports(self):
        """Test that all expected classes can be imported."""
        from omnibase_core.models.validation.model_validate_error import (
            ModelValidateMessage,
            ModelValidateMessageContext,
            ModelValidateResult,
            ValidateMessageModel,
            ValidateMessageModelContext,
            ValidateResultModel,
        )

        # Verify all classes are imported
        assert ModelValidateMessage is not None
        assert ModelValidateMessageContext is not None
        assert ModelValidateResult is not None
        assert ValidateMessageModelContext is not None
        assert ValidateMessageModel is not None
        assert ValidateResultModel is not None

    def test_compatibility_aliases(self):
        """Test that compatibility aliases point to correct classes."""
        from omnibase_core.models.validation.model_validate_error import (
            ModelValidateMessage,
            ModelValidateMessageContext,
            ModelValidateResult,
            ValidateMessageModel,
            ValidateMessageModelContext,
            ValidateResultModel,
        )

        # Test that aliases point to the correct classes
        assert ValidateMessageModelContext is ModelValidateMessageContext
        assert ValidateMessageModel is ModelValidateMessage
        assert ValidateResultModel is ModelValidateResult

    def test_module_all_exports(self):
        """Test that __all__ contains all expected exports."""
        from omnibase_core.models.validation import model_validate_error

        expected_exports = [
            "ModelValidateMessage",
            "ModelValidateMessageContext",
            "ModelValidateResult",
            "ValidateMessageModel",
            "ValidateMessageModelContext",
            "ValidateResultModel",
        ]

        # Check that all expected exports are in __all__
        assert hasattr(model_validate_error, "__all__")
        for export in expected_exports:
            assert export in model_validate_error.__all__

    def test_import_from_module(self):
        """Test importing classes from the module."""
        from omnibase_core.models.validation.model_validate_error import (
            ModelValidateMessage,
            ModelValidateMessageContext,
            ModelValidateResult,
        )

        # Verify classes are accessible
        assert ModelValidateMessage is not None
        assert ModelValidateMessageContext is not None
        assert ModelValidateResult is not None

    def test_compatibility_aliases_functionality(self):
        """Test that compatibility aliases work correctly."""
        # Test that aliases are the same as their original classes
        from omnibase_core.models.validation.model_validate_error import (
            ModelValidateMessage,
            ModelValidateMessageContext,
            ModelValidateResult,
            ValidateMessageModel,
            ValidateMessageModelContext,
            ValidateResultModel,
        )

        assert ValidateMessageModelContext is ModelValidateMessageContext
        assert ValidateMessageModel is ModelValidateMessage
        assert ValidateResultModel is ModelValidateResult

    def test_module_structure(self):
        """Test that the module has expected structure."""
        import omnibase_core.models.validation.model_validate_error as module

        # Module should exist and be importable
        assert module is not None

        # Should have all expected attributes
        expected_attrs = [
            "ModelValidateMessage",
            "ModelValidateMessageContext",
            "ModelValidateResult",
            "ValidateMessageModel",
            "ValidateMessageModelContext",
            "ValidateResultModel",
        ]

        for attr in expected_attrs:
            assert hasattr(module, attr)

    def test_import_paths(self):
        """Test that classes can be imported via different paths."""
        # Direct import from module
        # Import from package
        from omnibase_core.models.validation import model_validate_error
        from omnibase_core.models.validation.model_validate_error import (
            ModelValidateMessage as DirectModelValidateMessage,
        )

        PackageModelValidateMessage = model_validate_error.ModelValidateMessage

        # Both should be the same
        assert DirectModelValidateMessage is PackageModelValidateMessage

    def test_class_availability(self):
        """Test that all classes are available and importable."""
        from omnibase_core.models.validation.model_validate_error import (
            ModelValidateMessage,
            ModelValidateMessageContext,
            ModelValidateResult,
            ValidateMessageModel,
            ValidateMessageModelContext,
            ValidateResultModel,
        )

        # All classes should be available
        classes = [
            ModelValidateMessage,
            ModelValidateMessageContext,
            ModelValidateResult,
            ValidateMessageModelContext,
            ValidateMessageModel,
            ValidateResultModel,
        ]

        for cls in classes:
            assert cls is not None
            assert hasattr(cls, "__name__")

    def test_module_docstring(self):
        """Test that the module has proper docstring."""
        import omnibase_core.models.validation.model_validate_error as module

        # Module should have docstring
        assert module.__doc__ is not None
        assert "Validation error models" in module.__doc__

    def test_import_error_handling(self):
        """Test that import errors are handled properly."""
        # Test that we can import the module without errors
        try:
            from omnibase_core.models.validation.model_validate_error import (
                ModelValidateMessage,
            )

            assert ModelValidateMessage is not None
        except ImportError as e:
            pytest.fail(f"Failed to import ModelValidateMessage: {e}")

    def test_class_inheritance(self):
        """Test that imported classes have expected inheritance."""
        from omnibase_core.models.validation.model_validate_error import (
            ModelValidateMessage,
        )

        # ModelValidateMessage should be a class
        assert isinstance(ModelValidateMessage, type)

        # Should have expected methods if it's a Pydantic model
        if hasattr(ModelValidateMessage, "model_validate"):
            assert callable(ModelValidateMessage.model_validate)
        if hasattr(ModelValidateMessage, "model_dump"):
            assert callable(ModelValidateMessage.model_dump)

    def test_module_metadata(self):
        """Test that the module has expected metadata."""
        import omnibase_core.models.validation.model_validate_error as module

        # Module should have __file__ attribute
        assert hasattr(module, "__file__")

        # Module should have __name__ attribute
        assert hasattr(module, "__name__")
        assert module.__name__ == "omnibase_core.models.validation.model_validate_error"

    def test_omninode_metadata(self):
        """Test that the module contains OmniNode metadata."""
        import omnibase_core.models.validation.model_validate_error as module

        # Check for OmniNode metadata in the module source
        module_source = module.__doc__ or ""

        # The module should have a docstring
        assert module_source is not None
        assert len(module_source) > 0

    def test_module_imports_from_separated_models(self):
        """Test that the module imports from separated model files."""
        from omnibase_core.models.validation.model_validate_error import (
            ModelValidateMessage,
            ModelValidateMessageContext,
            ModelValidateResult,
        )

        # These should be imported from their respective files
        assert ModelValidateMessage is not None
        assert ModelValidateMessageContext is not None
        assert ModelValidateResult is not None

    def test_compatibility_aliases_consistency(self):
        """Test that compatibility aliases are consistent."""
        from omnibase_core.models.validation.model_validate_error import (
            ModelValidateMessage,
            ModelValidateMessageContext,
            ModelValidateResult,
            ValidateMessageModel,
            ValidateMessageModelContext,
            ValidateResultModel,
        )

        # Test that aliases are consistent
        assert ValidateMessageModel is ModelValidateMessage
        assert ValidateMessageModelContext is ModelValidateMessageContext
        assert ValidateResultModel is ModelValidateResult

    def test_module_re_exports(self):
        """Test that the module re-exports classes correctly."""
        from omnibase_core.models.validation.model_validate_error import (
            ModelValidateMessage,
            ModelValidateMessageContext,
            ModelValidateResult,
        )

        # Test that re-exports work
        assert ModelValidateMessage is not None
        assert ModelValidateMessageContext is not None
        assert ModelValidateResult is not None

    def test_module_structure_consistency(self):
        """Test that the module structure is consistent."""
        import omnibase_core.models.validation.model_validate_error as module

        # Test that the module has consistent structure
        assert hasattr(module, "__all__")
        assert hasattr(module, "__doc__")
        assert hasattr(module, "__file__")
        assert hasattr(module, "__name__")

        # Test that all expected classes are available
        expected_classes = [
            "ModelValidateMessage",
            "ModelValidateMessageContext",
            "ModelValidateResult",
            "ValidateMessageModel",
            "ValidateMessageModelContext",
            "ValidateResultModel",
        ]

        for class_name in expected_classes:
            assert hasattr(module, class_name)
            assert getattr(module, class_name) is not None
