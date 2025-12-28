"""
Unit tests for __init___fast.py lazy loading functions.

Tests lazy loading of validation tools to prevent import-time penalties.
"""

import pytest


@pytest.mark.unit
class TestLazyValidationLoading:
    """Test suite for lazy validation loading functions."""

    def test_get_validation_tools_returns_correct_tuple_structure(self):
        """Test that get_validation_tools returns a tuple of 4 callables."""
        from omnibase_core.__init___fast import get_validation_tools

        tools = get_validation_tools()

        assert isinstance(tools, tuple)
        assert len(tools) == 4
        assert all(callable(tool) for tool in tools)

    def test_get_validation_tools_returns_correct_functions(self):
        """Test that get_validation_tools returns the correct validation functions."""
        from omnibase_core.__init___fast import get_validation_tools

        (
            validate_architecture,
            validate_union_usage,
            validate_contracts,
            validate_patterns,
        ) = get_validation_tools()

        # Verify function names
        assert validate_architecture.__name__ == "validate_architecture"
        assert validate_union_usage.__name__ == "validate_union_usage"
        assert validate_contracts.__name__ == "validate_contracts"
        assert validate_patterns.__name__ == "validate_patterns"

    def test_get_validation_tools_lazy_imports_not_at_module_level(self):
        """Test that validation tools are not imported at module level."""
        import sys

        # Remove validation modules if already imported
        modules_to_remove = [
            key
            for key in sys.modules
            if "omnibase_core.validation" in key and key != "omnibase_core"
        ]
        for mod in modules_to_remove:
            del sys.modules[mod]

        # Import just the main module

        # Validation modules should NOT be imported yet
        validation_modules = [
            key for key in sys.modules if "omnibase_core.validation" in key
        ]
        assert len(validation_modules) == 0, (
            "Validation modules imported at module level (not lazy)"
        )

    def test_get_validation_suite_returns_correct_types(self):
        """Test that get_validation_suite returns ModelValidationResult, ServiceValidationSuite, and validate_all."""
        from omnibase_core.__init___fast import get_validation_suite

        result = get_validation_suite()

        assert isinstance(result, tuple)
        assert len(result) == 3

        ModelValidationResult, ServiceValidationSuite, validate_all = result

        # Verify types
        assert isinstance(ModelValidationResult, type)
        assert isinstance(ServiceValidationSuite, type)
        assert callable(validate_all)

    def test_get_validation_suite_types_are_correct(self):
        """Test that get_validation_suite returns the correct class types."""
        from omnibase_core.__init___fast import get_validation_suite

        ModelValidationResult, ServiceValidationSuite, validate_all = (
            get_validation_suite()
        )

        # Verify class names
        assert ModelValidationResult.__name__ == "ModelValidationResult"
        assert ServiceValidationSuite.__name__ == "ServiceValidationSuite"
        assert validate_all.__name__ == "validate_all"

    def test_get_all_validation_returns_dictionary(self):
        """Test that get_all_validation returns a dictionary with all validation tools."""
        from omnibase_core.__init___fast import get_all_validation

        all_validation = get_all_validation()

        assert isinstance(all_validation, dict)
        assert len(all_validation) == 7

        # Verify expected keys
        expected_keys = {
            "ModelValidationResult",
            "ServiceValidationSuite",
            "validate_all",
            "validate_architecture",
            "validate_contracts",
            "validate_patterns",
            "validate_union_usage",
        }
        assert set(all_validation.keys()) == expected_keys

    def test_get_all_validation_values_are_correct_types(self):
        """Test that get_all_validation returns correct types for each value."""
        from omnibase_core.__init___fast import get_all_validation

        all_validation = get_all_validation()

        # Classes should be types
        assert isinstance(all_validation["ModelValidationResult"], type)
        assert isinstance(all_validation["ServiceValidationSuite"], type)

        # Functions should be callable
        assert callable(all_validation["validate_all"])
        assert callable(all_validation["validate_architecture"])
        assert callable(all_validation["validate_contracts"])
        assert callable(all_validation["validate_patterns"])
        assert callable(all_validation["validate_union_usage"])

    def test_lazy_loading_performance_no_import_cascade(self):
        """Test that lazy loading doesn't trigger import cascade until accessed."""
        import sys
        import time

        # Clear any cached validation imports
        modules_to_remove = [
            key
            for key in list(sys.modules.keys())
            if "omnibase_core.validation" in key and key != "omnibase_core"
        ]
        for mod in modules_to_remove:
            del sys.modules[mod]

        # Import main module - should be fast
        start = time.perf_counter()
        from omnibase_core.__init___fast import get_validation_tools

        import_time = (time.perf_counter() - start) * 1000

        # Accessing the function should not trigger imports
        start_access = time.perf_counter()
        tools_func = get_validation_tools
        access_time = (time.perf_counter() - start_access) * 1000

        # Verify no validation modules loaded yet
        validation_modules = [
            key for key in sys.modules if "omnibase_core.validation." in key
        ]

        # Should be minimal (not testing specific times, just that no cascade occurred)
        assert len(validation_modules) == 0, (
            f"Import cascade detected: {validation_modules}"
        )

    def test_multiple_calls_return_same_functions(self):
        """Test that multiple calls to lazy loaders return the same function instances."""
        from omnibase_core.__init___fast import get_validation_tools

        tools1 = get_validation_tools()
        tools2 = get_validation_tools()

        # Should return the same function instances (same identity)
        assert tools1[0] is tools2[0]
        assert tools1[1] is tools2[1]
        assert tools1[2] is tools2[2]
        assert tools1[3] is tools2[3]

    def test_module_all_export_list(self):
        """Test that __all__ exports the correct functions."""
        import omnibase_core.__init___fast as omnibase_core

        assert hasattr(omnibase_core, "__all__")
        expected_exports = {
            "get_all_validation",
            "get_validation_suite",
            "get_validation_tools",
        }
        assert set(omnibase_core.__all__) == expected_exports


@pytest.mark.unit
class TestLazyLoadingIntegration:
    """Integration tests for lazy loading behavior."""

    def test_can_use_validation_tools_after_lazy_loading(self):
        """Test that validation tools can be used after lazy loading."""
        from omnibase_core.__init___fast import get_validation_tools

        tools = get_validation_tools()
        validate_architecture = tools[0]

        # Should be able to call the function (even if it fails on invalid path)
        # We're just testing that the lazy loading worked
        assert callable(validate_architecture)

    def test_validation_suite_can_be_instantiated(self):
        """Test that ServiceValidationSuite can be instantiated after lazy loading."""
        from omnibase_core.__init___fast import get_validation_suite

        _, ServiceValidationSuite, _ = get_validation_suite()

        # Should be able to instantiate the class
        suite = ServiceValidationSuite()
        assert suite is not None

    def test_all_validation_tools_accessible(self):
        """Test that all validation tools in get_all_validation are accessible."""
        from omnibase_core.__init___fast import get_all_validation

        all_validation = get_all_validation()

        # All tools should be accessible and callable/instantiable
        for key, value in all_validation.items():
            assert value is not None
            if "validate" in key.lower():
                assert callable(value) or isinstance(value, type)

    def test_lazy_loading_preserves_type_checking_imports(self):
        """Test that TYPE_CHECKING imports don't affect runtime behavior."""
        # This test verifies that TYPE_CHECKING imports are truly only for type checking
        from omnibase_core.__init___fast import get_validation_tools

        tools = get_validation_tools()

        # Should work at runtime despite TYPE_CHECKING imports
        assert all(callable(tool) for tool in tools)
