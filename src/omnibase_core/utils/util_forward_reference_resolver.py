"""
Forward reference resolver utility for Pydantic models.

This module provides a reusable utility for resolving TYPE_CHECKING forward
references in Pydantic models. This pattern is commonly needed when models
use lazy imports to avoid circular dependencies.

Pattern:
    Model (TYPE_CHECKING imports) -> rebuild_model_references() -> Resolved types

Example:
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

Note:
    This utility is designed to be stateless and thread-safe. All functions
    are pure and do not maintain any global state.
"""

from __future__ import annotations

import logging
import sys
import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic import BaseModel


def rebuild_model_references(
    model_class: type[BaseModel],
    type_mappings: dict[
        str, type
    ],  # ONEX_EXCLUDE: dict_str_type - intentional type mapping
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
        ModelOnexError: If imports fail, schema generation fails, or model
            rebuild fails due to configuration issues.

    Example:
        >>> from omnibase_core.utils.util_forward_reference_resolver import (
        ...     rebuild_model_references,
        ... )
        >>> from mymodule import MyModel, TypeA, TypeB
        >>> rebuild_model_references(
        ...     model_class=MyModel,
        ...     type_mappings={"TypeA": TypeA, "TypeB": TypeB},
        ... )
    """
    from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
    from omnibase_core.models.errors.model_onex_error import ModelOnexError

    # Import Pydantic-specific exceptions for precise error handling
    try:
        from pydantic import PydanticSchemaGenerationError, PydanticUserError
    except ImportError:
        # Fallback for older Pydantic versions
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
    except (TypeError, ValueError) as e:
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

    Example:
        >>> class MyModel(BaseModel):
        ...     def __init_subclass__(cls, **kwargs):
        ...         super().__init_subclass__(**kwargs)
        ...         handle_subclass_forward_refs(
        ...             parent_model=MyModel,
        ...             subclass=cls,
        ...             rebuild_func=_rebuild_model,
        ...         )
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
    except (TypeError, ValueError) as e:
        # Type annotation issues during rebuild - likely configuration error
        msg = (
            f"{parent_name} subclass {subclass_name}: forward reference "
            f"rebuild failed ({type(e).__name__}): {e}. "
            f"Call _rebuild_model() explicitly after all dependencies are loaded."
        )
        logger.warning(msg)
        warnings.warn(msg, UserWarning, stacklevel=3)


def auto_rebuild_on_module_load(
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
            {"CONFIGURATION_ERROR", "INITIALIZATION_FAILED"}.

    Example:
        >>> # At module level, after model definition:
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
        except (TypeError, ValueError, AttributeError):
            # These specific exceptions indicate configuration problems
            # Re-raise to fail fast
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
    to provide consistent error messaging.

    Args:
        model_name: Name of the model that failed to rebuild.
        error_code_str: String representation of the error code.
        error_msg: The error message.
        error_type: Optional type name of the error (e.g., "ModelOnexError").
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
