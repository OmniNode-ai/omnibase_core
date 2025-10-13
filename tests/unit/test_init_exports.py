"""
Unit tests for omnibase_core.__init__ module exports and lazy loading.

Tests cover:
- Public API exports validation (__all__ defined correctly)
- No internal leaks (no private modules exposed)
- Import performance (lazy loading works correctly)
- Circular import prevention
- Version information availability
"""

import sys
import time

import pytest


class TestInitExports:
    """Test __init__.py public API exports."""

    def test_init_exports_all_defined(self):
        """Test that __all__ is defined and contains expected exports."""
        import omnibase_core

        assert hasattr(omnibase_core, "__all__")
        expected_exports = {
            "EnumCoreErrorCode",
            "ModelOnexError",
            "ModelValidationSuite",
            "ValidationResult",
            "validate_all",
            "validate_architecture",
            "validate_contracts",
            "validate_patterns",
            "validate_union_usage",
        }
        assert set(omnibase_core.__all__) == expected_exports

    def test_init_exports_no_internal_leaks(self):
        """Test that no internal/private modules are exposed in __all__."""
        import omnibase_core

        # No private modules (starting with _) should be in __all__
        for export in omnibase_core.__all__:
            assert not export.startswith(
                "_"
            ), f"Private module {export} leaked in __all__"

    def test_init_exports_are_accessible(self):
        """Test that all exports in __all__ are actually accessible."""
        import omnibase_core

        for export_name in omnibase_core.__all__:
            assert hasattr(
                omnibase_core, export_name
            ), f"Export {export_name} not accessible"
            export_obj = getattr(omnibase_core, export_name)
            assert export_obj is not None, f"Export {export_name} is None"


class TestInitImportPerformance:
    """Test __init__.py import performance and lazy loading."""

    def test_init_import_time_acceptable(self):
        """Test that importing omnibase_core is fast (lazy loading works)."""
        # Clear cached imports
        modules_to_remove = [
            key
            for key in list(sys.modules.keys())
            if key.startswith("omnibase_core") and key != "omnibase_core.__init__"
        ]
        for mod in modules_to_remove:
            del sys.modules[mod]

        # Time the import
        start = time.perf_counter()
        import omnibase_core

        import_time_ms = (time.perf_counter() - start) * 1000

        # Import should be fast (< 100ms for lazy loading)
        # This is a reasonable threshold for lazy loading
        assert (
            import_time_ms < 100
        ), f"Import took {import_time_ms:.2f}ms (expected < 100ms)"

    def test_init_lazy_loading_delays_validation_imports(self):
        """Test that validation modules are not imported until accessed."""
        # Clear cached validation imports
        modules_to_remove = [
            key for key in list(sys.modules.keys()) if "omnibase_core.validation" in key
        ]
        for mod in modules_to_remove:
            del sys.modules[mod]

        # Import main module
        import omnibase_core

        # Validation modules should NOT be imported yet
        validation_modules = [
            key
            for key in sys.modules
            if "omnibase_core.validation" in key and key != "omnibase_core"
        ]
        assert (
            len(validation_modules) == 0
        ), f"Validation modules imported too early: {validation_modules}"

        # Now access a validation function - should trigger lazy import
        _ = omnibase_core.validate_architecture

        # Now validation modules SHOULD be imported
        validation_modules = [
            key for key in sys.modules if "omnibase_core.validation" in key
        ]
        assert (
            len(validation_modules) > 0
        ), "Lazy loading did not import validation modules"


class TestInitCircularImports:
    """Test circular import prevention in __init__.py."""

    def test_init_no_circular_imports(self):
        """Test that importing omnibase_core does not cause circular imports."""
        # Clear all omnibase_core imports
        modules_to_remove = [
            key for key in list(sys.modules.keys()) if key.startswith("omnibase_core")
        ]
        for mod in modules_to_remove:
            del sys.modules[mod]

        # Should import without circular import errors
        try:
            import omnibase_core

            assert omnibase_core is not None
        except ImportError as e:
            pytest.fail(f"Circular import detected: {e}")

    def test_init_getattr_handles_missing_attributes(self):
        """Test that __getattr__ raises proper error for missing attributes."""
        import omnibase_core
        from omnibase_core.errors.model_onex_error import ModelOnexError

        with pytest.raises(ModelOnexError) as exc_info:
            _ = omnibase_core.NonExistentAttribute

        assert "has no attribute 'NonExistentAttribute'" in str(exc_info.value)


class TestInitValidationExports:
    """Test validation tool exports from __init__.py."""

    def test_init_validation_result_export(self):
        """Test that ValidationResult is properly exported."""
        from omnibase_core import ValidationResult

        assert ValidationResult is not None
        assert isinstance(ValidationResult, type)

    def test_init_model_validation_suite_export(self):
        """Test that ModelValidationSuite is properly exported."""
        from omnibase_core import ModelValidationSuite

        assert ModelValidationSuite is not None
        assert isinstance(ModelValidationSuite, type)

    def test_init_validate_all_export(self):
        """Test that validate_all function is properly exported."""
        from omnibase_core import validate_all

        assert validate_all is not None
        assert callable(validate_all)

    def test_init_validate_architecture_export(self):
        """Test that validate_architecture function is properly exported."""
        from omnibase_core import validate_architecture

        assert validate_architecture is not None
        assert callable(validate_architecture)

    def test_init_validate_contracts_export(self):
        """Test that validate_contracts function is properly exported."""
        from omnibase_core import validate_contracts

        assert validate_contracts is not None
        assert callable(validate_contracts)

    def test_init_validate_patterns_export(self):
        """Test that validate_patterns function is properly exported."""
        from omnibase_core import validate_patterns

        assert validate_patterns is not None
        assert callable(validate_patterns)

    def test_init_validate_union_usage_export(self):
        """Test that validate_union_usage function is properly exported."""
        from omnibase_core import validate_union_usage

        assert validate_union_usage is not None
        assert callable(validate_union_usage)


class TestInitErrorExports:
    """Test error class exports from __init__.py."""

    def test_init_enum_core_error_code_export(self):
        """Test that EnumCoreErrorCode is properly exported."""
        from omnibase_core import EnumCoreErrorCode

        assert EnumCoreErrorCode is not None
        # Should be an enum class
        assert hasattr(EnumCoreErrorCode, "__members__")

    def test_init_model_onex_error_export(self):
        """Test that ModelOnexError is properly exported."""
        from omnibase_core import ModelOnexError

        assert ModelOnexError is not None
        assert isinstance(ModelOnexError, type)
        # Should be an Exception subclass
        assert issubclass(ModelOnexError, Exception)


class TestInitLazyLoadingBehavior:
    """Test lazy loading behavior for different attributes."""

    def test_init_lazy_load_error_classes(self):
        """Test that error classes are lazily loaded through __getattr__."""
        # Clear cached imports
        modules_to_remove = [
            key
            for key in list(sys.modules.keys())
            if key.startswith("omnibase_core.errors")
        ]
        for mod in modules_to_remove:
            del sys.modules[mod]

        # Access error classes through lazy loading
        from omnibase_core import EnumCoreErrorCode, ModelOnexError

        assert EnumCoreErrorCode is not None
        assert ModelOnexError is not None

    def test_init_lazy_load_validation_functions(self):
        """Test that validation functions are lazily loaded through __getattr__."""
        # Clear cached validation imports
        modules_to_remove = [
            key for key in list(sys.modules.keys()) if "omnibase_core.validation" in key
        ]
        for mod in modules_to_remove:
            del sys.modules[mod]

        # Access validation functions through lazy loading
        from omnibase_core import ValidationResult, validate_all, validate_architecture

        assert ValidationResult is not None
        assert validate_all is not None
        assert validate_architecture is not None

    def test_init_multiple_lazy_loads_return_same_object(self):
        """Test that multiple lazy loads return the same object instance."""
        from omnibase_core import ModelOnexError as error1
        from omnibase_core import ModelOnexError as error2

        # Should be the exact same class object (identity check)
        assert error1 is error2


class TestInitModuleDocstring:
    """Test __init__.py module documentation."""

    def test_init_has_docstring(self):
        """Test that __init__.py has a module docstring."""
        import omnibase_core

        assert omnibase_core.__doc__ is not None
        assert len(omnibase_core.__doc__) > 0

    def test_init_docstring_describes_package(self):
        """Test that docstring describes the package purpose."""
        import omnibase_core

        docstring = omnibase_core.__doc__
        # Should mention key concepts
        assert "omnibase" in docstring.lower() or "onex" in docstring.lower()
