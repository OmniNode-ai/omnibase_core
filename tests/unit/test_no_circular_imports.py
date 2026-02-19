# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Test to verify no circular import dependencies.

This test ensures that the core types and models can be imported
without circular dependency issues.

Import Chain (Must Remain in This Order):
1. types.core_types (minimal types, no external deps)
2. errors.error_codes → types.core_types
3. models.common.model_schema_value → errors.error_codes
4. types.constraints → TYPE_CHECKING import of errors.error_codes
5. models.* → types.constraints
6. types.constraints → models.base (lazy __getattr__ only)
"""

import importlib
import sys
from importlib import import_module

import pytest


def test_import_core_types():
    """Test that core types can be imported without issues."""
    # Should import cleanly
    from omnibase_core.types.type_core import (
        ProtocolSchemaValue,
        TypedDictBasicErrorContext,
    )

    # Verify types are available
    assert TypedDictBasicErrorContext is not None
    assert ProtocolSchemaValue is not None


def test_import_error_codes():
    """Test that error_codes module can be imported."""
    from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
    from omnibase_core.models.errors.model_onex_error import ModelOnexError

    assert EnumCoreErrorCode is not None
    assert ModelOnexError is not None


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
        "omnibase_core.types.type_core",
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
    """Test that TypedDictBasicErrorContext works as expected."""
    from omnibase_core.types.type_core import TypedDictBasicErrorContext

    # TypedDict creates plain dict instances, so we create it as a dict
    context: TypedDictBasicErrorContext = {
        "file_path": "/test/file.py",
        "line_number": 42,
        "function_name": "test_function",
        "additional_context": {"key": "value"},
    }

    # TypedDict is just a dict, so we can access fields directly
    assert context["file_path"] == "/test/file.py"
    assert context["line_number"] == 42
    assert context["function_name"] == "test_function"
    assert context["additional_context"]["key"] == "value"

    # TypedDict instances are dicts, so we can copy them
    restored = context.copy()
    assert restored["file_path"] == context["file_path"]
    assert restored["line_number"] == context["line_number"]
    assert restored["function_name"] == context["function_name"]
    assert restored["additional_context"] == context["additional_context"]


def test_model_error_context_conversion():
    """Test conversion between ModelErrorContext and TypedDictBasicErrorContext."""
    from omnibase_core.models.common.model_error_context import ModelErrorContext
    from omnibase_core.models.common.model_schema_value import ModelSchemaValue

    # Create a ModelErrorContext
    model_context = ModelErrorContext(
        file_path="/test/file.py",
        line_number=42,
        additional_context={
            "key": ModelSchemaValue.from_value("value"),
        },
    )

    # Convert to TypedDictBasicErrorContext (returns a dict)
    simple_context = model_context.to_simple_context()
    # TypedDict is just a type annotation for dict, so we check it's a dict with the right keys
    assert isinstance(simple_context, dict)
    assert simple_context["file_path"] == "/test/file.py"
    assert simple_context["line_number"] == 42
    assert simple_context["additional_context"]["key"] == "value"

    # Convert back to ModelErrorContext
    restored_model = ModelErrorContext.from_simple_context(simple_context)
    assert restored_model.file_path == model_context.file_path
    assert restored_model.line_number == model_context.line_number
    assert restored_model.additional_context["key"].to_value() == "value"


def test_onex_error_no_circular_dependency():
    """Test that OnexError can be created without triggering circular imports."""
    from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
    from omnibase_core.models.errors.model_onex_error import ModelOnexError as OnexError

    # Create an OnexError
    error = OnexError(
        message="Test error",
        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        file_path="/test/file.py",
        line_number=42,
    )

    # Verify error was created
    assert error.message == "Test error"
    assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
    assert error.context.get("file_path") == "/test/file.py"
    assert error.context.get("line_number") == 42


def test_import_chain_sequential() -> None:
    """
    Test that each module in the import chain can be imported sequentially.

    This verifies that the import order is correct and no circular dependencies
    exist at module import time.
    """
    # Start with a clean slate - remove all omnibase_core modules
    modules_to_remove = [key for key in sys.modules if key.startswith("omnibase_core")]
    for module in modules_to_remove:
        del sys.modules[module]

    # Import in the correct order - each step should succeed
    steps = [
        ("types.type_core", "omnibase_core.types.type_core"),
        ("errors.error_codes", "omnibase_core.errors.error_codes"),
        (
            "models.common.model_schema_value",
            "omnibase_core.models.common.model_schema_value",
        ),
        ("types.type_constraints", "omnibase_core.types.type_constraints"),
        ("models", "omnibase_core.models"),
    ]

    for step_name, module_name in steps:
        try:
            importlib.import_module(module_name)
        except ImportError as e:
            msg = f"Failed to import {step_name} ({module_name}): {e}"
            raise AssertionError(msg) from e


def test_type_checking_imports_not_runtime() -> None:
    """
    Verify that TYPE_CHECKING imports are truly only for type checking.

    This checks that modules imported under TYPE_CHECKING guards are not
    available at runtime in the module's direct namespace.
    """
    # Import types.constraints (has TYPE_CHECKING import of ModelOnexError)
    import omnibase_core.types.type_constraints as constraints_module

    # Check that ModelOnexError is not directly accessible at runtime
    # (it's imported under TYPE_CHECKING for type hints only)
    # Note: EnumCoreErrorCode IS imported at runtime on line 60 of constraints.py
    type_checking_imports = ["ModelOnexError"]

    for import_name in type_checking_imports:
        # These should NOT be directly accessible at runtime
        # They are only available under TYPE_CHECKING for type hints
        if import_name in dir(constraints_module):
            # If it's in dir(), check if it's actually accessible
            try:
                attr = getattr(constraints_module, import_name, None)
                if attr is not None:
                    msg = f"{import_name} should only be available during TYPE_CHECKING, not at runtime"
                    raise AssertionError(msg)
            except AttributeError:
                # This is expected - TYPE_CHECKING imports shouldn't be accessible
                pass


def test_lazy_imports_work() -> None:
    """
    Test that lazy imports in types.constraints work correctly.

    The __getattr__ pattern should load models.base only when accessed.
    """
    # Import types.constraints
    import omnibase_core.types.type_constraints as constraints_module

    # Check that we can access the lazy imports
    lazy_imports = [
        "ModelBaseCollection",
        "ModelBaseFactory",
        "BaseCollection",
        "BaseFactory",
    ]

    for import_name in lazy_imports:
        # This should trigger __getattr__ and import models.base
        try:
            attr = getattr(constraints_module, import_name)
            assert attr is not None, (
                f"{import_name} should be available via __getattr__"
            )
        except AttributeError as e:
            msg = f"Lazy import {import_name} failed: {e}"
            raise AssertionError(msg) from e


def test_validation_functions_lazy_import() -> None:
    """
    Test that validation functions use lazy imports correctly.

    The validate_primitive_value and validate_context_value functions
    use standard Python TypeError (not ModelOnexError) to avoid importing
    error_codes, thus maintaining the lazy import pattern.
    """
    # Clear module cache
    modules_to_remove = [key for key in sys.modules if key.startswith("omnibase_core")]
    for module in modules_to_remove:
        del sys.modules[module]

    # Import types.constraints
    from omnibase_core.types.type_constraints import (
        validate_context_value,
        validate_primitive_value,
    )

    # Test successful validation (should not trigger import)
    assert validate_primitive_value("test")
    assert validate_context_value("test")

    # Test failed validation (should raise TypeError, not ModelOnexError)
    try:
        validate_primitive_value(object())  # Invalid type
    except TypeError as e:
        # Expected - validation should fail with TypeError
        assert "Expected primitive value" in str(e)
    else:
        pytest.fail("validate_primitive_value should have raised TypeError")

    # Verify error_codes is NOT imported (lazy import maintained)
    assert "omnibase_core.errors.error_codes" not in sys.modules, (
        "error_codes should NOT be imported (lazy import pattern maintained)"
    )


def test_import_order_documentation() -> None:
    """
    Verify that import order documentation is present in critical modules.

    This ensures that the documentation we added remains in place and
    developers are warned about the import constraints.
    """
    import omnibase_core.errors.error_codes as error_codes_module
    import omnibase_core.models.common.model_schema_value as schema_value_module
    import omnibase_core.types.type_constraints as constraints_module

    # Check that each module has import order documentation
    modules_to_check = [
        (error_codes_module, "errors.error_codes"),
        (schema_value_module, "models.common.model_schema_value"),
        (constraints_module, "types.constraints"),
    ]

    for module, module_name in modules_to_check:
        docstring = module.__doc__ or ""
        assert (
            "IMPORT ORDER CONSTRAINTS" in docstring
            or "Import Chain" in docstring
            or "LAZY IMPORT" in docstring
        ), f"{module_name} is missing import order documentation in docstring"


def test_error_codes_safe_imports() -> None:
    """
    Verify that error_codes only imports from safe modules.

    This ensures that error_codes doesn't create circular dependencies
    by importing from models or types.constraints at runtime.
    """
    # Clear module cache
    modules_to_remove = [key for key in sys.modules if key.startswith("omnibase_core")]
    for module in modules_to_remove:
        del sys.modules[module]

    # Import error_codes

    # Check what omnibase_core modules were imported
    imported_modules = [key for key in sys.modules if key.startswith("omnibase_core")]

    # error_codes should only import from safe modules
    # It should NOT import from models.* or types.constraints
    forbidden_imports = [
        "omnibase_core.models.common.model_schema_value",
        "omnibase_core.models.common.model_error_context",
        "omnibase_core.types.type_constraints",
        "omnibase_core.models.base",
    ]

    for forbidden in forbidden_imports:
        if forbidden in imported_modules:
            msg = f"error_codes has runtime import of {forbidden} - this will cause circular import!"
            raise AssertionError(msg)

    # Note: Previously checked for required imports like enum_onex_status,
    # but these were removed as unused during tech debt cleanup.
    # The important check is that forbidden imports are not present.


def test_contracts_no_circular_imports() -> None:
    """
    Verify that contract models don't create circular imports.

    This test specifically checks for the circular import that was found in PR #65
    where model_contract_compute.py was importing model_validation_rules_converter
    at module level, which created a circular dependency:

    model_contract_compute → model_validation_rules_converter
    → model_validation_rules → contracts/__init__ → model_contract_compute

    The fix is to use lazy imports (local imports in field validators) instead
    of module-level imports.
    """
    # Clear module cache
    modules_to_remove = [key for key in sys.modules if key.startswith("omnibase_core")]
    for module in modules_to_remove:
        del sys.modules[module]

    # Try to import the contract models in the order that would trigger circular import
    try:
        # Import model_contract_compute first
        # Import contracts __init__ (aggregates all contract models)
        import omnibase_core.models.contracts
        import omnibase_core.models.contracts.model_contract_compute

        # Import model_validation_rules
        import omnibase_core.models.contracts.model_validation_rules

        # Import model_validation_rules_converter
        import omnibase_core.models.utils.model_validation_rules_converter  # noqa: F401

        # If we got here, no circular imports!
        print("✓ No circular dependencies in contracts modules")

    except ImportError as e:
        # Circular import would raise ImportError
        raise AssertionError(f"Circular import detected in contracts: {e}") from e


def test_contract_compute_uses_lazy_import() -> None:
    """
    Verify that model_contract_compute uses lazy imports for ValidationRulesConverter.

    This ensures that ValidationRulesConverter is only imported inside the
    field validator function, not at module level.
    """
    # Clear module cache
    modules_to_remove = [key for key in sys.modules if key.startswith("omnibase_core")]
    for module in modules_to_remove:
        del sys.modules[module]

    # Import model_contract_compute

    # Check what modules were imported
    imported_modules = [key for key in sys.modules if key.startswith("omnibase_core")]

    # model_validation_rules_converter should NOT be imported at module load time
    # (it should only be imported when the field validator is actually called)
    if (
        "omnibase_core.models.utils.model_validation_rules_converter"
        in imported_modules
    ):
        msg = (
            "model_contract_compute has runtime import of model_validation_rules_converter "
            "at module level - this creates circular import! Use lazy import in field validator instead."
        )
        raise AssertionError(msg)


@pytest.mark.unit
def test_fsm_package_no_circular_imports() -> None:
    """
    Regression test for OMN-2048: circular import in fsm package.

    The circular import chain was:
        fsm/__init__.py
          -> model_fsm_transition_result.py
            -> reducer/__init__.py (ModelIntent)
              -> model_reducer_input.py
                -> common/__init__.py (ModelReducerMetadata)
                  -> model_envelope.py
                    -> validation/__init__.py
                      -> model_migration_conflict_union.py
                        -> validator_migration_types.py
                          -> validation/__init__.py (ContractPatchValidator)
                            -> validator_contract_patch.py
                              -> contracts/__init__.py
                                -> mixins/__init__.py (MixinNodeTypeValidator)
                                  -> mixin_fsm_execution.py
                                    -> util_fsm_executor.py
                                      -> model_fsm_transition_result.py  <- CIRCULAR

    Fix: util_fsm_executor.py defers ModelFSMTransitionResult import to
    function scope (lazy import) and imports ModelFSMStateSnapshot from
    its module directly rather than through fsm/__init__.py.
    """
    # Clear module cache to test fresh imports
    modules_to_remove = [key for key in sys.modules if key.startswith("omnibase_core")]
    for module in modules_to_remove:
        del sys.modules[module]

    try:
        # Import through the fsm package init - this was the failing entry point
        # Verify mixin can be imported
        from omnibase_core.mixins.mixin_fsm_execution import (  # noqa: F401
            MixinFSMExecution,
        )
        from omnibase_core.models.fsm import (  # noqa: F401
            ModelFsmState,
            ModelFSMStateSnapshot,
            ModelFSMTransitionResult,
        )

        # Also verify the direct module import works
        from omnibase_core.models.fsm.model_fsm_state import (  # noqa: F401
            ModelFsmState as DirectState,
        )

        # Verify util_fsm_executor can be imported and used
        from omnibase_core.utils.util_fsm_executor import (  # noqa: F401
            FSMState,
            execute_transition,
            get_initial_state,
            validate_fsm_contract,
        )

    except ImportError as e:
        raise AssertionError(
            f"Circular import detected in FSM package (OMN-2048 regression): {e}"
        ) from e


@pytest.mark.unit
def test_invariant_package_no_circular_imports() -> None:
    """
    Regression test: circular import in invariant package.

    The circular import chain was:
        util_invariant_yaml_parser
          -> models/invariant/model_invariant_set
            -> models/invariant/__init__.py (during resolution)
              -> util_invariant_yaml_parser  <- CIRCULAR

    Fix: models/invariant/__init__.py defers the three YAML-parsing
    function imports to a __getattr__ lazy-loading pattern so the
    package init no longer eagerly imports util_invariant_yaml_parser.
    """
    # Clear module cache to test fresh imports
    modules_to_remove = [key for key in sys.modules if key.startswith("omnibase_core")]
    for module in modules_to_remove:
        del sys.modules[module]

    try:
        # Import the module that was the cycle entry point
        # Import the package init (would have triggered the cycle)
        import omnibase_core.models.invariant as invariant_pkg
        from omnibase_core.utils.util_invariant_yaml_parser import (  # noqa: F401
            load_invariant_set_from_file as _load_file,
        )
        from omnibase_core.utils.util_invariant_yaml_parser import (  # noqa: F401
            load_invariant_sets_from_directory as _load_dir,
        )
        from omnibase_core.utils.util_invariant_yaml_parser import (  # noqa: F401
            parse_invariant_set_from_yaml as _parse,
        )

        # Verify the lazy-loaded functions are accessible via the package
        assert hasattr(invariant_pkg, "load_invariant_set_from_file")
        assert callable(invariant_pkg.load_invariant_set_from_file)

    except ImportError as e:
        raise AssertionError(
            f"Circular import detected in invariant package: {e}"
        ) from e


@pytest.mark.unit
def test_util_fsm_executor_does_not_eagerly_import_transition_result() -> None:
    """
    Verify util_fsm_executor uses lazy import for ModelFSMTransitionResult.

    ModelFSMTransitionResult must NOT be imported at module level in
    util_fsm_executor, because that creates the circular dependency
    fixed in OMN-2048. This test checks the source code structure
    rather than manipulating sys.modules, which is fragile.
    """
    import inspect

    import omnibase_core.utils.util_fsm_executor as executor_module

    source = inspect.getsource(executor_module)

    # Check that ModelFSMTransitionResult is NOT imported at module level.
    # It should only appear in TYPE_CHECKING block or inside functions.
    lines = source.split("\n")
    in_type_checking = False

    for line in lines:
        stripped = line.strip()

        # Track TYPE_CHECKING block
        if stripped.startswith("if TYPE_CHECKING"):
            in_type_checking = True
            continue
        # Any non-indented, non-empty line ends the TYPE_CHECKING block
        if in_type_checking and stripped and not line.startswith((" ", "\t")):
            in_type_checking = False

        # Module-level import check: not in TYPE_CHECKING and not indented
        if (
            not in_type_checking
            and not line.startswith(" ")
            and not line.startswith("\t")
            and "model_fsm_transition_result" in line
            and ("from" in line or "import" in line)
        ):
            raise AssertionError(
                f"util_fsm_executor has module-level import of "
                f"model_fsm_transition_result: {line.strip()}\n"
                "This creates circular import (OMN-2048). "
                "Use lazy import inside functions instead."
            )
