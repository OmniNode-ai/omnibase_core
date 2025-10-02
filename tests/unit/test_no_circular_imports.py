"""
Test to verify no circular import dependencies.

This test ensures that the core types and models can be imported
without circular dependency issues.
"""

import sys
from importlib import import_module


def test_import_core_types():
    """Test that core types can be imported without issues."""
    # Should import cleanly
    from omnibase_core.types.core_types import (
        BasicErrorContext,
        ProtocolErrorContext,
        ProtocolSchemaValue,
    )

    # Verify types are available
    assert BasicErrorContext is not None
    assert ProtocolErrorContext is not None
    assert ProtocolSchemaValue is not None


def test_import_error_codes():
    """Test that error_codes module can be imported."""
    from omnibase_core.errors.error_codes import (
        CoreErrorCode,
        OnexError,
    )

    assert CoreErrorCode is not None
    assert OnexError is not None


def test_import_model_error_context():
    """Test that ModelErrorContext can be imported."""
    from omnibase_core.models.common.model_error_context import ModelErrorContext

    assert ModelErrorContext is not None


def test_import_model_schema_value():
    """Test that ModelSchemaValue can be imported."""
    from omnibase_core.models.common.model_schema_value import ModelSchemaValue

    assert ModelSchemaValue is not None


def test_import_model_numeric_value():
    """Test that ModelNumericValue can be imported."""
    from omnibase_core.models.common.model_numeric_value import ModelNumericValue

    assert ModelNumericValue is not None


def test_no_circular_dependency_chain():
    """
    Test the full import chain that previously had circular dependencies.

    The old circular dependency chain was:
    1. error_codes → ModelSchemaValue
    2. ModelSchemaValue → OnexError
    3. OnexError → ModelErrorContext
    4. ModelErrorContext → OnexError + ModelSchemaValue

    This test verifies the chain can now be imported in any order.
    """
    # Clear any previously imported modules to test fresh imports
    modules_to_test = [
        "omnibase_core.errors.error_codes",
        "omnibase_core.models.common.model_schema_value",
        "omnibase_core.models.common.model_error_context",
        "omnibase_core.models.common.model_numeric_value",
        "omnibase_core.types.core_types",
    ]

    # Remove from sys.modules if present (for clean test)
    for mod_name in modules_to_test:
        if mod_name in sys.modules:
            del sys.modules[mod_name]

    # Now try to import in the order that would trigger circular dependency
    try:
        # Step 1: Import error_codes (would try to import ModelSchemaValue)
        error_codes_mod = import_module("omnibase_core.errors.error_codes")
        assert error_codes_mod is not None

        # Step 2: Import ModelSchemaValue (would try to import OnexError)
        schema_value_mod = import_module(
            "omnibase_core.models.common.model_schema_value"
        )
        assert schema_value_mod is not None

        # Step 3: Import ModelErrorContext (would try to import OnexError)
        error_context_mod = import_module(
            "omnibase_core.models.common.model_error_context"
        )
        assert error_context_mod is not None

        # Step 4: Import ModelNumericValue (would try to import OnexError)
        numeric_value_mod = import_module(
            "omnibase_core.models.common.model_numeric_value"
        )
        assert numeric_value_mod is not None

        # If we got here, no circular imports!
        print("✓ No circular dependencies detected")

    except ImportError as e:
        # Circular import would raise ImportError
        raise AssertionError(f"Circular import detected: {e}") from e


def test_simple_error_context_functionality():
    """Test that BasicErrorContext works as expected."""
    from omnibase_core.types.core_types import BasicErrorContext

    # Create a simple context
    context = BasicErrorContext(
        file_path="/test/file.py",
        line_number=42,
        function_name="test_function",
        additional_context={"key": "value"},
    )

    # Test to_dict
    context_dict = context.to_dict()
    assert context_dict["file_path"] == "/test/file.py"
    assert context_dict["line_number"] == 42
    assert context_dict["function_name"] == "test_function"
    assert context_dict["key"] == "value"

    # Test from_dict
    restored = BasicErrorContext.from_dict(context_dict)
    assert restored.file_path == context.file_path
    assert restored.line_number == context.line_number
    assert restored.function_name == context.function_name
    assert restored.additional_context == context.additional_context


def test_model_error_context_conversion():
    """Test conversion between ModelErrorContext and BasicErrorContext."""
    from omnibase_core.models.common.model_error_context import ModelErrorContext
    from omnibase_core.models.common.model_schema_value import ModelSchemaValue
    from omnibase_core.types.core_types import BasicErrorContext

    # Create a ModelErrorContext
    model_context = ModelErrorContext(
        file_path="/test/file.py",
        line_number=42,
        additional_context={
            "key": ModelSchemaValue.from_value("value"),
        },
    )

    # Convert to BasicErrorContext
    simple_context = model_context.to_simple_context()
    assert isinstance(simple_context, BasicErrorContext)
    assert simple_context.file_path == "/test/file.py"
    assert simple_context.line_number == 42
    assert simple_context.additional_context["key"] == "value"

    # Convert back to ModelErrorContext
    restored_model = ModelErrorContext.from_simple_context(simple_context)
    assert restored_model.file_path == model_context.file_path
    assert restored_model.line_number == model_context.line_number
    assert restored_model.additional_context["key"].to_value() == "value"


def test_onex_error_no_circular_dependency():
    """Test that OnexError can be created without triggering circular imports."""
    from omnibase_core.errors.error_codes import CoreErrorCode, OnexError

    # Create an OnexError
    error = OnexError(
        message="Test error",
        error_code=CoreErrorCode.VALIDATION_ERROR,
        file_path="/test/file.py",
        line_number=42,
    )

    # Verify error was created
    assert error.message == "Test error"
    assert error.error_code == CoreErrorCode.VALIDATION_ERROR
    assert error.context.get("file_path") == "/test/file.py"
    assert error.context.get("line_number") == 42
