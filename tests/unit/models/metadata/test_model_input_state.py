"""Test model_input_state module."""


class TestModelInputStateModule:
    """Test the model_input_state module."""

    def test_module_imports(self):
        """Test that the module imports correctly."""
        from omnibase_core.models.metadata.model_input_state import (
            ModelInputState,
            TypedDictInputStateFields,
            TypedDictInputStateSourceType,
        )

        # Test that all expected exports are available
        assert TypedDictInputStateFields is not None
        assert TypedDictInputStateSourceType is not None
        assert ModelInputState is not None

    def test_module_all_exports(self):
        """Test that __all__ contains expected exports."""
        import omnibase_core.models.metadata.model_input_state as module

        expected_exports = [
            "TypedDictInputStateFields",
            "TypedDictInputStateSourceType",
            "ModelInputState",
        ]

        assert hasattr(module, "__all__")
        assert module.__all__ == expected_exports

    def test_typed_dict_input_state_fields(self):
        """Test TypedDictInputStateFields."""
        from omnibase_core.models.metadata.model_input_state import (
            TypedDictInputStateFields,
        )

        # Test that it's a TypedDict
        assert hasattr(TypedDictInputStateFields, "__annotations__")
        assert hasattr(TypedDictInputStateFields, "__total__")

    def test_typed_dict_input_state_source_type(self):
        """Test TypedDictInputStateSourceType."""
        from omnibase_core.models.metadata.model_input_state import (
            TypedDictInputStateSourceType,
        )

        # Test that it's a TypedDict
        assert hasattr(TypedDictInputStateSourceType, "__annotations__")
        assert hasattr(TypedDictInputStateSourceType, "__total__")

    def test_model_input_state(self):
        """Test ModelInputState."""
        from omnibase_core.models.metadata.model_input_state import ModelInputState

        # Test that it's a class
        assert isinstance(ModelInputState, type)
        assert hasattr(ModelInputState, "__annotations__")

    def test_module_docstring(self):
        """Test that the module has a docstring."""
        import omnibase_core.models.metadata.model_input_state as module

        assert module.__doc__ is not None
        assert len(module.__doc__.strip()) > 0
        assert "Input State Models" in module.__doc__
        assert "re-export module" in module.__doc__.lower()
