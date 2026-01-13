"""
Forward reference resolver utility for Pydantic models.

This module provides a reusable utility for resolving TYPE_CHECKING forward
references in Pydantic models. This pattern is commonly needed when models
use lazy imports to avoid circular dependencies.

Pattern:
    Model (TYPE_CHECKING imports) -> rebuild_model_references() -> Resolved types

Quick Start:
    from omnibase_core.utils.util_forward_reference_resolver import (
        rebuild_model_references,
        handle_subclass_forward_refs,
        auto_rebuild_on_module_load,
    )

    # Simple usage - resolve forward references
    rebuild_model_references(
        model_class=MyModel,
        type_mappings={
            "SomeType": SomeType,
            "OtherType": OtherType,
        }
    )

    # In __init_subclass__ - deferred rebuild with error handling
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        handle_subclass_forward_refs(
            parent_model=MyModel,
            subclass=cls,
            rebuild_func=_rebuild_model,
        )

    # Automatic module-load rebuild with proper error semantics
    auto_rebuild_on_module_load(
        rebuild_func=_rebuild_model,
        model_name="MyModel",
        fail_fast_errors={"CONFIGURATION_ERROR", "INITIALIZATION_FAILED"},
    )

Error Handling Overview:
    This module implements a three-tier error handling strategy:

    1. **Fail-Fast Errors** (raise immediately):
       - PydanticSchemaGenerationError: Invalid type annotations or schema issues
       - PydanticUserError: Invalid Pydantic model configuration
       - VALIDATION_ERRORS (TypeError, ValidationError, ValueError): Used by
         rebuild_model_references() and handle_subclass_forward_refs()
       - PYDANTIC_MODEL_ERRORS (AttributeError, TypeError, ValidationError, ValueError):
         Used by auto_rebuild_on_module_load() for broader attribute error coverage
       - RuntimeError: Critical failures during module manipulation

    2. **Deferred Errors** (log warning, allow retry later):
       - ImportError: Dependencies not yet available during bootstrap
       - This is expected during early module loading before circular deps resolve

    3. **Wrapped Errors** (converted to ModelOnexError):
       - All Pydantic-specific errors are wrapped with structured context
       - Error codes: INITIALIZATION_FAILED, CONFIGURATION_ERROR, IMPORT_ERROR

Error Categories Quick Reference (rebuild_model_references behavior):

    Note: handle_subclass_forward_refs() logs warnings instead of wrapping errors.
    auto_rebuild_on_module_load() re-raises PYDANTIC_MODEL_ERRORS without wrapping.

    | Error Type                    | Function Behavior                    | User Action                           |
    |-------------------------------|--------------------------------------|---------------------------------------|
    | ImportError                   | Deferred (logged as debug/warning)   | Call _rebuild_model() after deps load |
    | TypeError                     | Fail-fast (wrapped in ModelOnexError)| Fix type annotations                  |
    | ValidationError               | Fail-fast (wrapped in ModelOnexError)| Fix Pydantic model validation         |
    | ValueError                    | Fail-fast (wrapped in ModelOnexError)| Fix model configuration               |
    | PydanticSchemaGenerationError | Fail-fast (wrapped in ModelOnexError)| Fix schema definitions                |
    | PydanticUserError             | Fail-fast (wrapped in ModelOnexError)| Fix Pydantic model config             |
    | AttributeError                | Fail-fast (wrapped in ModelOnexError)| Check type_mappings completeness      |
    | RuntimeError                  | Fail-fast (raised immediately)       | Check for module manipulation issues  |

Edge Cases:

    1. **Early Bootstrap** (before dependencies loaded):
       When auto_rebuild_on_module_load() is called during early import, before
       ModelOnexError or dependent types are available:
       - ImportError is caught and logged at DEBUG level
       - Resolution is deferred until explicit _rebuild_model() call
       - This is normal during Python's module loading sequence

       Example scenario:
           # mymodel.py imports utility
           # utility.py tries to import ModelOnexError
           # ModelOnexError not yet loaded -> ImportError -> deferred

    2. **Circular Imports** (type_mappings creates cycles):
       If type_mappings references types that create circular imports:
       - ImportError is raised by the calling _rebuild_model() function
       - For handle_subclass_forward_refs(): logged as debug, deferred
       - For auto_rebuild_on_module_load(): logged as warning, deferred
       - Resolution: restructure imports or use additional TYPE_CHECKING

    3. **Missing Types** (type_mappings incomplete):
       If type_mappings doesn't include all forward-referenced types:
       - Pydantic raises PydanticSchemaGenerationError on model_rebuild()
       - rebuild_model_references() wraps this in ModelOnexError
       - Error context includes model name and original error details

    4. **Module Not In sys.modules** (inject_into_module=True with unloaded module):
       If the model's module hasn't been registered in sys.modules:
       - Module injection is silently skipped (no error)
       - model_rebuild() still receives type_mappings via _types_namespace
       - This is expected for dynamically created classes

    5. **Subclass During Early Loading** (__init_subclass__ called early):
       When subclasses are created before all dependencies are available:
       - handle_subclass_forward_refs() catches ImportError
       - Logs debug message about deferred rebuild
       - Subclass can still be used; resolution happens on first validation
       - If other errors occur, warning is logged with guidance

Best Practices:

    1. **Always define a module-level _rebuild_model() function**:
       This function should handle its own ImportError for dependent types
       and call rebuild_model_references() with complete type_mappings.

    2. **Call auto_rebuild_on_module_load() at module level**:
       Place this after the model class definition for automatic resolution.

    3. **Use handle_subclass_forward_refs() in __init_subclass__**:
       This ensures subclasses also get forward references resolved.

    4. **Test forward reference resolution**:
       Add tests that import your model and validate instances with
       forward-referenced types to catch issues early.

Note:
    This utility is designed to be stateless and thread-safe. All functions
    are pure and do not maintain any global state.

See Also:
    - docs/architecture/PAYLOAD_TYPE_ARCHITECTURE.md for payload typing patterns
    - ModelEventPublishIntent for a complete usage example
"""

from __future__ import annotations

import logging
import sys
import warnings
from typing import TYPE_CHECKING

from omnibase_core.errors.exception_groups import (
    PYDANTIC_MODEL_ERRORS,
    VALIDATION_ERRORS,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic import BaseModel


def rebuild_model_references(
    model_class: type[BaseModel],
    type_mappings: dict[str, type | object],  # Accepts types and UnionTypes
    *,
    inject_into_module: bool = True,
) -> None:
    """
    Rebuild a Pydantic model to resolve forward references.

    This function resolves TYPE_CHECKING forward references by injecting
    the actual types into the model's namespace and triggering Pydantic's
    model_rebuild() mechanism.

    Args:
        model_class: The Pydantic model class to rebuild.
        type_mappings: Mapping of forward reference names to their actual types.
            Keys should match the string names used in TYPE_CHECKING annotations.
        inject_into_module: If True, also inject types into the model's module
            globals for complete forward reference resolution. Defaults to True.

    Raises:
        ModelOnexError: Raised for all error conditions with specific error codes:

            - **INITIALIZATION_FAILED** (ONEX_CORE_087):
              - PydanticSchemaGenerationError: Invalid annotations or schema
              - VALIDATION_ERRORS (TypeError, ValidationError, ValueError):
                Type mismatch, Pydantic validation failure, or invalid configuration
              - AttributeError: Missing attribute during module injection

            - **CONFIGURATION_ERROR** (ONEX_CORE_044):
              - PydanticUserError: Invalid Pydantic model configuration

            All ModelOnexError instances include context with:
              - model: The model class name
              - error_type: Original exception type name
              - error_details: Original exception message

    Error Handling Details:
        This function implements fail-fast semantics. Any error during rebuild
        is immediately raised as a ModelOnexError. There is no retry or deferral
        logic - that is handled by the caller (e.g., handle_subclass_forward_refs
        or auto_rebuild_on_module_load).

        **PydanticSchemaGenerationError**:
            Occurs when Pydantic cannot generate a schema for the model.
            Common causes:
            - Missing type in type_mappings
            - Invalid union type annotation
            - Unsupported generic type parameter

        **PydanticUserError**:
            Occurs when model configuration is invalid.
            Common causes:
            - Invalid ConfigDict options
            - Conflicting field definitions
            - Invalid discriminator setup

        **VALIDATION_ERRORS (TypeError, ValidationError, ValueError)**:
            Occurs during the rebuild process.
            Common causes:
            - Type annotation syntax errors
            - Invalid default values for typed fields
            - Incompatible type constraints
            - Pydantic validation failures

        **AttributeError**:
            Occurs during module injection.
            Common causes:
            - Model's module not properly loaded
            - setattr fails on frozen module

    Edge Cases:
        **Module not in sys.modules**:
            If inject_into_module=True but the model's module isn't in sys.modules,
            module injection is silently skipped. The type_mappings are still
            passed to model_rebuild() via _types_namespace.

        **Already resolved forward references**:
            Calling this function multiple times is safe. Pydantic's model_rebuild()
            handles idempotent rebuilds gracefully.

        **Pydantic version compatibility**:
            For older Pydantic versions (<2.0), PydanticSchemaGenerationError and
            PydanticUserError may not exist. The function falls back to catching
            TypeError and ValueError in these cases.

    Examples:
        Basic usage with two forward-referenced types:

        >>> from omnibase_core.utils.util_forward_reference_resolver import (
        ...     rebuild_model_references,
        ... )
        >>> from mymodule import MyModel, TypeA, TypeB
        >>> rebuild_model_references(
        ...     model_class=MyModel,
        ...     type_mappings={"TypeA": TypeA, "TypeB": TypeB},
        ... )

        Handling errors in a _rebuild_model() function:

        >>> def _rebuild_model() -> None:
        ...     '''Rebuild with ImportError handling.'''
        ...     try:
        ...         from mymodule.types import TypeA, TypeB
        ...     except ImportError as e:
        ...         raise ModelOnexError(
        ...             message=f"Failed to import types: {e}",
        ...             error_code=EnumCoreErrorCode.IMPORT_ERROR,
        ...             context={"model": "MyModel"},
        ...         ) from e
        ...
        ...     rebuild_model_references(
        ...         model_class=MyModel,
        ...         type_mappings={"TypeA": TypeA, "TypeB": TypeB},
        ...     )

        Skip module injection for dynamically created classes:

        >>> # For classes created via type() or similar
        >>> rebuild_model_references(
        ...     model_class=DynamicModel,
        ...     type_mappings={"Payload": PayloadType},
        ...     inject_into_module=False,  # Module may not exist
        ... )
    """
    from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
    from omnibase_core.models.errors.model_onex_error import ModelOnexError

    # Import Pydantic-specific exceptions for precise error handling
    try:
        from pydantic import PydanticSchemaGenerationError, PydanticUserError
    except ImportError:
        # NOTE(OMN-1302): Fallback exception types for older Pydantic versions.
        # Safe because only used in except clauses where parent types work.
        PydanticSchemaGenerationError = TypeError  # type: ignore[misc, assignment]
        PydanticUserError = ValueError  # type: ignore[misc, assignment]

    model_name = model_class.__name__

    try:
        # Optionally inject types into module globals for Pydantic resolution
        if inject_into_module:
            module_name = model_class.__module__
            if module_name in sys.modules:
                current_module = sys.modules[module_name]
                for type_name, type_value in type_mappings.items():
                    setattr(current_module, type_name, type_value)

        # Rebuild model with resolved types namespace
        model_class.model_rebuild(_types_namespace=type_mappings)

    except PydanticSchemaGenerationError as e:
        raise ModelOnexError(
            message=f"Failed to generate schema for {model_name}: {e}",
            error_code=EnumCoreErrorCode.INITIALIZATION_FAILED,
            context={
                "model": model_name,
                "error_type": "PydanticSchemaGenerationError",
                "error_details": str(e),
            },
        ) from e
    except PydanticUserError as e:
        raise ModelOnexError(
            message=f"Invalid Pydantic configuration for {model_name}: {e}",
            error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
            context={
                "model": model_name,
                "error_type": "PydanticUserError",
                "error_details": str(e),
            },
        ) from e
    except VALIDATION_ERRORS as e:
        raise ModelOnexError(
            message=f"Failed to rebuild {model_name}: {e}",
            error_code=EnumCoreErrorCode.INITIALIZATION_FAILED,
            context={
                "model": model_name,
                "error_type": type(e).__name__,
                "error_details": str(e),
            },
        ) from e
    except AttributeError as e:
        raise ModelOnexError(
            message=f"Attribute error during {model_name} rebuild: {e}",
            error_code=EnumCoreErrorCode.INITIALIZATION_FAILED,
            context={
                "model": model_name,
                "error_type": "AttributeError",
                "error_details": str(e),
            },
        ) from e


def handle_subclass_forward_refs(
    parent_model: type[BaseModel],
    subclass: type[BaseModel],
    rebuild_func: Callable[[], None],
) -> None:
    """
    Handle forward reference resolution when a model is subclassed.

    This function is designed to be called from __init_subclass__ to ensure
    forward references are resolved for subclasses. It handles the common
    case where dependencies are not yet available during early module loading.

    Args:
        parent_model: The parent model class being subclassed.
        subclass: The new subclass being created.
        rebuild_func: A zero-argument function that rebuilds the parent model.
            This should be the module's _rebuild_model() function.

    Error Handling:
        This function implements deferred error semantics for ImportError and
        warning-based logging for other errors. It never raises exceptions.

        **ImportError** (deferred):
            When rebuild_func raises ImportError, it means dependencies are
            not yet available. This is expected during early module loading.

            Behavior:
            - Logged at DEBUG level (not visible in normal operation)
            - Resolution deferred until explicit _rebuild_model() call
            - Subclass creation proceeds normally

            When this happens:
            - Python is still loading dependent modules
            - Circular import resolution is in progress
            - The model will be rebuilt later when dependencies are available

        **VALIDATION_ERRORS (TypeError, ValidationError, ValueError)** (warned):
            When rebuild_func raises these errors, it indicates a configuration
            or type annotation problem that needs attention.

            Behavior:
            - Logged at WARNING level
            - UserWarning emitted (stacklevel=3 points to subclass definition)
            - Subclass creation proceeds (may fail at validation time)

            Common causes:
            - Invalid type annotations in the parent model
            - Missing types in type_mappings
            - Pydantic configuration issues
            - ValidationError from Pydantic model validation

    Edge Cases:
        **Called during early module loading**:
            This is the most common scenario. When a subclass is defined,
            Python may not have finished loading all dependent modules.

            Example sequence:
            1. subclass.py imports parent_model.py
            2. parent_model.py defines class with TYPE_CHECKING imports
            3. subclass.py defines a subclass (triggers __init_subclass__)
            4. __init_subclass__ calls handle_subclass_forward_refs()
            5. rebuild_func() tries to import TYPE_CHECKING types
            6. ImportError: types not yet available
            7. This function logs debug and returns (no error)
            8. Later, when module loading completes, _rebuild_model() succeeds

        **Multiple subclasses defined**:
            Each subclass triggers __init_subclass__ and calls this function.
            If the first call fails with ImportError, subsequent calls may
            succeed (as more modules load). This is handled gracefully.

        **rebuild_func raises other exceptions**:
            Any exception other than ImportError or VALIDATION_ERRORS
            (TypeError, ValidationError, ValueError) will propagate normally
            (not caught by this function). This includes RuntimeError,
            which indicates a critical failure.

    Examples:
        Standard usage in __init_subclass__:

        >>> class MyModel(BaseModel):
        ...     def __init_subclass__(cls, **kwargs):
        ...         super().__init_subclass__(**kwargs)
        ...         handle_subclass_forward_refs(
        ...             parent_model=MyModel,
        ...             subclass=cls,
        ...             rebuild_func=_rebuild_model,
        ...         )

        Complete implementation with _rebuild_model:

        >>> from typing import TYPE_CHECKING
        >>> from pydantic import BaseModel
        >>>
        >>> if TYPE_CHECKING:
        ...     from mymodule.types import PayloadType
        >>>
        >>> class MyModel(BaseModel):
        ...     payload: PayloadType
        ...
        ...     def __init_subclass__(cls, **kwargs):
        ...         super().__init_subclass__(**kwargs)
        ...         from omnibase_core.utils.util_forward_reference_resolver import (
        ...             handle_subclass_forward_refs,
        ...         )
        ...         handle_subclass_forward_refs(
        ...             parent_model=MyModel,
        ...             subclass=cls,
        ...             rebuild_func=_rebuild_model,
        ...         )
        >>>
        >>> def _rebuild_model() -> None:
        ...     from mymodule.types import PayloadType
        ...     from omnibase_core.utils.util_forward_reference_resolver import (
        ...         rebuild_model_references,
        ...     )
        ...     rebuild_model_references(
        ...         model_class=MyModel,
        ...         type_mappings={"PayloadType": PayloadType},
        ...     )
    """
    logger = logging.getLogger(parent_model.__module__)
    parent_name = parent_model.__name__
    subclass_name = subclass.__name__

    try:
        rebuild_func()
    except ImportError as e:
        # Dependencies not yet available during early loading
        # This is expected during bootstrap - Pydantic will lazily resolve
        logger.debug(
            "%s subclass %s: forward reference rebuild "
            "deferred (ImportError during bootstrap): %s",
            parent_name,
            subclass_name,
            e,
        )
    except VALIDATION_ERRORS as e:
        # Type annotation issues during rebuild - likely configuration error
        msg = (
            f"{parent_name} subclass {subclass_name}: forward reference "
            f"rebuild failed ({type(e).__name__}): {e}. "
            f"Call _rebuild_model() explicitly after all dependencies are loaded."
        )
        logger.warning(msg)
        warnings.warn(msg, UserWarning, stacklevel=3)


def auto_rebuild_on_module_load(  # stub-ok: fully implemented with extensive docstring
    rebuild_func: Callable[[], None],
    model_name: str,
    *,
    fail_fast_error_codes: frozenset[str] | None = None,
) -> None:
    """
    Automatically rebuild a model on module load with proper error semantics.

    This function should be called at module level (outside of any function
    or class) to trigger forward reference resolution when the module is
    first imported.

    Args:
        rebuild_func: A zero-argument function that rebuilds the model.
            This should call rebuild_model_references() with appropriate
            type mappings.
        model_name: Name of the model being rebuilt (for error messages).
        fail_fast_error_codes: Set of error code values that should cause
            immediate failure rather than deferred resolution. Defaults to
            {"ONEX_CORE_044_CONFIGURATION_ERROR", "ONEX_CORE_087_INITIALIZATION_FAILED"}.

    Error Handling:
        This function implements a tiered error handling strategy:

        **Fail-Fast Errors** (re-raised immediately):
            These errors indicate configuration problems that must be fixed:

            - ModelOnexError with CONFIGURATION_ERROR code
            - ModelOnexError with INITIALIZATION_FAILED code
            - PYDANTIC_MODEL_ERRORS (AttributeError, TypeError, ValidationError, ValueError):
              These indicate type annotation, configuration, or attribute problems
            - RuntimeError (critical module manipulation failure)

            These errors will crash the import, which is intentional - they
            indicate bugs that must be fixed before the module can be used.

        **Deferred Errors** (logged as warning, import continues):
            These errors indicate timing issues that may resolve later:

            - ModelOnexError with other error codes (e.g., IMPORT_ERROR)
            - ImportError when loading ModelOnexError itself (early bootstrap)

            These are logged with a warning message that includes:
            - Model name
            - Error type and code
            - Guidance to call _rebuild_model() explicitly

    Edge Cases:
        **ModelOnexError import fails** (early bootstrap):
            During early Python module loading, ModelOnexError itself may
            not be available. In this case:

            - ImportError is caught at the outer level
            - Logged at DEBUG level (silent in normal operation)
            - Resolution deferred until later _rebuild_model() call

            This is expected during bootstrap and is not an error condition.

            Sequence:
            1. Python starts loading your model module
            2. Module calls auto_rebuild_on_module_load() at import time
            3. This function tries to import ModelOnexError
            4. omnibase_core.models.errors not yet loaded -> ImportError
            5. ImportError caught, logged at DEBUG, function returns
            6. Your module import completes successfully
            7. Later, explicit _rebuild_model() call resolves forward refs

        **Customizing fail-fast error codes**:
            The default fail_fast_error_codes covers common configuration
            issues. You can customize this for specific scenarios:

            >>> # Example: Also fail-fast on VALIDATION_ERROR
            >>> auto_rebuild_on_module_load(
            ...     rebuild_func=_rebuild_model,
            ...     model_name="MyModel",
            ...     fail_fast_error_codes=frozenset({
            ...         "ONEX_CORE_044_CONFIGURATION_ERROR",
            ...         "ONEX_CORE_087_INITIALIZATION_FAILED",
            ...         "ONEX_CORE_045_VALIDATION_ERROR",
            ...     }),
            ... )

        **Error code string format**:
            Error codes are checked as strings using the format
            "ONEX_CORE_XXX_ERROR_NAME". The function checks the error_code
            attribute's string representation against fail_fast_error_codes.

    Examples:
        Basic usage at module level:

        >>> # mymodel.py
        >>> from pydantic import BaseModel
        >>> from typing import TYPE_CHECKING
        >>>
        >>> if TYPE_CHECKING:
        ...     from mymodule.types import PayloadType
        >>>
        >>> class MyModel(BaseModel):
        ...     payload: PayloadType
        >>>
        >>> def _rebuild_model() -> None:
        ...     from mymodule.types import PayloadType
        ...     rebuild_model_references(
        ...         model_class=MyModel,
        ...         type_mappings={"PayloadType": PayloadType},
        ...     )
        >>>
        >>> # Automatic resolution on module import
        >>> auto_rebuild_on_module_load(
        ...     rebuild_func=_rebuild_model,
        ...     model_name="MyModel",
        ... )

        Complete example with error handling in _rebuild_model:

        >>> def _rebuild_model() -> None:
        ...     '''Rebuild with proper error wrapping.'''
        ...     from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        ...     from omnibase_core.models.errors.model_onex_error import ModelOnexError
        ...
        ...     try:
        ...         from mymodule.types import PayloadType, OtherType
        ...     except ImportError as e:
        ...         raise ModelOnexError(
        ...             message=f"Failed to import types for MyModel: {e}",
        ...             error_code=EnumCoreErrorCode.IMPORT_ERROR,
        ...             context={"model": "MyModel", "missing": str(e)},
        ...         ) from e
        ...
        ...     rebuild_model_references(
        ...         model_class=MyModel,
        ...         type_mappings={
        ...             "PayloadType": PayloadType,
        ...             "OtherType": OtherType,
        ...         },
        ...     )
        >>>
        >>> # This will defer on IMPORT_ERROR, fail-fast on CONFIGURATION_ERROR
        >>> auto_rebuild_on_module_load(
        ...     rebuild_func=_rebuild_model,
        ...     model_name="MyModel",
        ... )
    """
    if fail_fast_error_codes is None:
        fail_fast_error_codes = frozenset(
            {
                "ONEX_CORE_044_CONFIGURATION_ERROR",
                "ONEX_CORE_087_INITIALIZATION_FAILED",
            }
        )

    try:
        # Import error handling infrastructure
        from omnibase_core.models.errors.model_onex_error import (
            ModelOnexError as _ModelOnexError,
        )

        try:
            rebuild_func()
        except _ModelOnexError as rebuild_error:
            # Check if this is a fail-fast error type
            error_code = rebuild_error.error_code
            if error_code is None:
                error_code_value = "UNKNOWN"
            elif hasattr(error_code, "value"):
                error_code_value = str(error_code.value)
            else:
                error_code_value = str(error_code)

            if error_code_value in fail_fast_error_codes:
                # Configuration and initialization errors should fail fast
                raise

            # For other error types (like IMPORT_ERROR), log and defer
            _log_rebuild_failure(
                model_name=model_name,
                error_code_str=error_code_value,
                error_msg=rebuild_error.message or str(rebuild_error),
                error_type="ModelOnexError",
            )
        except PYDANTIC_MODEL_ERRORS:
            # PYDANTIC_MODEL_ERRORS (AttributeError, TypeError, ValidationError, ValueError)
            # indicate configuration problems - re-raise to fail fast
            raise
        except RuntimeError:
            # RuntimeError during module manipulation is a critical failure
            raise

    except ImportError as import_error:
        # Handle case where ModelOnexError itself fails to import (early bootstrap)
        # This is expected during early module loading before all dependencies exist
        logger = logging.getLogger(__name__)
        logger.debug(
            "%s: forward reference rebuild deferred (ImportError during bootstrap): %s",
            model_name,
            import_error,
        )


def _log_rebuild_failure(
    model_name: str,
    error_code_str: str,
    error_msg: str,
    error_type: str | None = None,
) -> None:
    """
    Log and warn about rebuild failure in a consistent format.

    This is an internal helper function used by auto_rebuild_on_module_load()
    to provide consistent error messaging for deferred errors.

    Args:
        model_name: Name of the model that failed to rebuild.
        error_code_str: String representation of the error code (e.g.,
            "ONEX_CORE_086_IMPORT_ERROR").
        error_msg: The error message from the original exception.
        error_type: Optional type name of the error (e.g., "ModelOnexError").
            If provided, appears in parentheses in the log message.

    Behavior:
        1. Constructs a formatted message including:
           - Model name
           - Error type (if provided)
           - Error code
           - Original error message
           - Guidance to call _rebuild_model() explicitly

        2. Logs the message at WARNING level

        3. Emits a UserWarning with stacklevel=4 to point to the
           auto_rebuild_on_module_load() call site

    Example Output:
        >>> _log_rebuild_failure(
        ...     model_name="MyModel",
        ...     error_code_str="ONEX_CORE_086_IMPORT_ERROR",
        ...     error_msg="No module named 'mymodule.types'",
        ...     error_type="ModelOnexError",
        ... )
        # Logs: "MyModel: automatic forward reference rebuild failed
        #        (ModelOnexError): ONEX_CORE_086_IMPORT_ERROR:
        #        No module named 'mymodule.types'.
        #        Call _rebuild_model() explicitly after all dependencies are loaded."

    Note:
        This function is intentionally internal (prefixed with _). It should
        not be called directly by external code.
    """
    full_msg = (
        f"{model_name}: automatic forward reference rebuild failed"
        f"{f' ({error_type})' if error_type else ''}: "
        f"{error_code_str}: {error_msg}. "
        f"Call _rebuild_model() explicitly after all dependencies are loaded."
    )

    logger = logging.getLogger(__name__)
    logger.warning(full_msg)
    warnings.warn(full_msg, UserWarning, stacklevel=4)
