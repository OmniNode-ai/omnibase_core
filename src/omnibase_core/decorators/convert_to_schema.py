"""
Decorator for automatic conversion of Pydantic fields to ModelSchemaValue.

This decorator reduces boilerplate by automatically generating field validators
that convert list[Any] or dict[str, Any] fields to their type-safe ModelSchemaValue
equivalents.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module uses deferred imports to avoid circular dependencies.
ModelSchemaValue is imported inside functions, not at module level.

PYDANTIC INTERNAL API USAGE (Documented Limitation):
=====================================================
This module uses Pydantic internal APIs because there is no public API
for dynamically adding model validators to an existing class post-creation.

Internal APIs used:
- pydantic._internal._decorators.Decorator
- pydantic._internal._decorators.ModelValidatorDecoratorInfo
- cls.__pydantic_decorators__ (semi-public, used in Pydantic docs)

Version Compatibility:
- Tested with Pydantic 2.6+ through 2.11+
- These internals are stable across Pydantic 2.x but may change in 3.x
- If Pydantic adds a public API for dynamic validators, migrate to it

Alternative approaches considered and rejected:
- create_model() with __validators__: Changes class identity, breaks isinstance checks
- Subclass wrapping: Creates new class, incompatible with existing type hints
- __init_subclass__: Requires modifying the decorated class's metaclass

Usage:
    @convert_to_schema("field_name")
    class MyModel(BaseModel):
        field_name: list[ModelSchemaValue] = Field(...)

The decorator will generate a model_validator that:
1. Handles empty collections gracefully
2. Passes through already-converted ModelSchemaValue instances
3. Converts raw values to ModelSchemaValue using from_value()
"""

from __future__ import annotations

import warnings
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import VERSION as PYDANTIC_VERSION
from pydantic import BaseModel

# Pydantic internal API import with proper fallback handling.
# This is documented as a known limitation - no public API exists for
# dynamically adding model validators post-creation.
try:
    from pydantic._internal._decorators import Decorator, ModelValidatorDecoratorInfo

    _PYDANTIC_INTERNALS_AVAILABLE = True
except ImportError as e:
    _PYDANTIC_INTERNALS_AVAILABLE = False
    _PYDANTIC_IMPORT_ERROR = e
    # Provide type stubs to prevent NameError at module load time
    Decorator = None  # type: ignore[assignment, misc]
    ModelValidatorDecoratorInfo = None  # type: ignore[assignment, misc]

# Version compatibility check - warn if outside tested range
_PYDANTIC_MAJOR = int(PYDANTIC_VERSION.split(".")[0])
_PYDANTIC_MINOR = int(PYDANTIC_VERSION.split(".")[1])
if _PYDANTIC_MAJOR != 2 or _PYDANTIC_MINOR < 6:
    warnings.warn(
        f"convert_to_schema decorator is tested with Pydantic 2.6+. "
        f"Current version: {PYDANTIC_VERSION}. Internal APIs may differ.",
        UserWarning,
        stacklevel=2,
    )

if TYPE_CHECKING:
    from omnibase_core.models.common.model_schema_value import ModelSchemaValue

T = TypeVar("T", bound=BaseModel)


def _get_model_schema_value() -> type[ModelSchemaValue]:
    """
    Lazy import of ModelSchemaValue to avoid circular dependencies.

    Returns:
        The ModelSchemaValue class.
    """
    from omnibase_core.models.common.model_schema_value import ModelSchemaValue

    return ModelSchemaValue


def _is_serialized_schema_value(
    value: dict[str, Any],  # ONEX_EXCLUDE: dict_str_any - deserializing unknown schema
) -> bool:
    """Check if a dict looks like a serialized ModelSchemaValue."""
    # Serialized ModelSchemaValue always has 'value_type' key with specific values
    if "value_type" not in value:
        return False
    valid_types = {"string", "number", "boolean", "null", "array", "object"}
    return value.get("value_type") in valid_types


def _convert_list_value(
    value: list[Any] | None, schema_cls: type[ModelSchemaValue]
) -> list[Any]:
    """Convert a list value to list of ModelSchemaValue."""
    if not value:
        return []
    # Homogeneous list assumption: if first element is ModelSchemaValue,
    # all elements are (lists come from single serialization source)
    if len(value) > 0 and isinstance(value[0], schema_cls):
        return value
    # Check if first element is a serialized ModelSchemaValue dict
    # (from model_dump round-trip)
    if (
        len(value) > 0
        and isinstance(value[0], dict)
        and _is_serialized_schema_value(value[0])
    ):
        # Let Pydantic handle deserialization
        return value
    return [schema_cls.from_value(item) for item in value]


# ONEX_EXCLUDE: dict_str_any - schema conversion utility for dynamic types
def _convert_dict_value(
    value: dict[str, Any] | None,
    schema_cls: type[ModelSchemaValue],
) -> dict[str, Any]:
    """Convert a dict value to dict of ModelSchemaValue."""
    if not value:
        return {}
    # Check if values are already ModelSchemaValue
    first_value = next(iter(value.values()))
    if isinstance(first_value, schema_cls):
        return value
    return {k: schema_cls.from_value(v) for k, v in value.items()}


def _convert_value(value: Any, schema_cls: type[ModelSchemaValue]) -> Any:
    """Convert a value (list or dict) to ModelSchemaValue format.

    Note: None values are returned as-is to allow Pydantic's default_factory
    to provide the appropriate default. This ensures dict fields don't
    incorrectly receive an empty list.
    """
    if value is None:
        return None
    if value == []:
        return []
    if isinstance(value, list):
        return _convert_list_value(value, schema_cls)
    if isinstance(value, dict):
        # Check if this is a serialized ModelSchemaValue (from model_dump)
        # If so, let Pydantic handle the deserialization directly
        if _is_serialized_schema_value(value):
            return value
        return _convert_dict_value(value, schema_cls)
    # For unexpected types, return as-is
    return value


def convert_to_schema(
    *field_names: str,
) -> Callable[[type[T]], type[T]]:
    """
    Class decorator that adds model validators for automatic ModelSchemaValue conversion.

    This decorator reduces validator boilerplate by automatically generating
    validators that convert list[Any] or dict[str, Any] fields to their
    type-safe ModelSchemaValue equivalents.

    Args:
        *field_names: One or more field names to apply the conversion to.
                     Each field should be typed as list[ModelSchemaValue] or
                     dict[str, ModelSchemaValue].

    Returns:
        A class decorator that adds the necessary validators.

    Example:
        @convert_to_schema("values", "items")
        class MyModel(BaseModel):
            values: list[ModelSchemaValue] = Field(...)
            items: list[ModelSchemaValue] = Field(...)

        # The decorator automatically generates validators equivalent to:
        # @model_validator(mode="before")
        # @classmethod
        # def convert_schema_fields(cls, data):
        #     ...conversion logic...

    Pattern Applied:
        For lists:
            - Empty list -> []
            - list[ModelSchemaValue] -> pass through unchanged
            - list[Any] -> [ModelSchemaValue.from_value(item) for item in v]

        For dicts:
            - Empty dict -> {}
            - dict[str, ModelSchemaValue] -> pass through unchanged
            - dict[str, Any] -> {k: ModelSchemaValue.from_value(v) for k, v in v.items()}

    Note:
        This uses a homogeneous list assumption: if the first element is a
        ModelSchemaValue, all elements are assumed to be (since lists typically
        come from a single serialization source).
    """

    def decorator(cls: type[T]) -> type[T]:
        # Runtime check for Pydantic internal API availability
        if not _PYDANTIC_INTERNALS_AVAILABLE:
            raise RuntimeError(  # error-ok: Pydantic internal API unavailable at import time
                f"convert_to_schema decorator requires Pydantic internal APIs "
                f"(pydantic._internal._decorators) which are not available. "
                f"Import error: {_PYDANTIC_IMPORT_ERROR}. "
                f"This may indicate an incompatible Pydantic version. "
                f"Current version: {PYDANTIC_VERSION}. "
                f"Tested with: Pydantic 2.6+ through 2.11+."
            )

        # Capture field names in closure
        fields_to_convert = set(field_names)

        # ONEX_EXCLUDE: dict_str_any - pydantic validator requires flexible input/output types
        def convert_schema_fields(
            cls_inner: type[Any],
            data: dict[str, Any] | Any,
        ) -> dict[str, Any] | Any:
            """
            Convert specified field values to ModelSchemaValue for type safety.

            This validator runs before Pydantic's type validation.
            """
            # If data is not a dict, let Pydantic handle it
            if not isinstance(data, dict):
                return data

            # Lazy import to avoid circular dependencies
            schema_value_cls = _get_model_schema_value()

            # Convert each field that needs conversion
            for field_name in fields_to_convert:
                if field_name in data:
                    data[field_name] = _convert_value(
                        data[field_name], schema_value_cls
                    )

            return data

        # Create a bound classmethod
        validator_method = classmethod(convert_schema_fields).__get__(None, cls)

        # Generate a unique validator name
        validator_name = f"_convert_to_schema_{'_'.join(sorted(field_names))}"

        # Add method to class
        setattr(cls, validator_name, validator_method)

        # Create Decorator object matching Pydantic's internal structure
        decorator_obj = Decorator(
            cls_ref=f"{cls.__module__}.{cls.__name__}:{id(cls)}",
            cls_var_name=validator_name,
            func=validator_method,
            shim=None,
            info=ModelValidatorDecoratorInfo(mode="before"),
        )

        # Add to pydantic_decorators
        cls.__pydantic_decorators__.model_validators[validator_name] = decorator_obj

        # Rebuild the model to register the new validator with Pydantic
        cls.model_rebuild(force=True)

        return cls

    return decorator


def convert_list_to_schema(
    *field_names: str,
) -> Callable[[type[T]], type[T]]:
    """
    Specialized decorator for list fields only.

    Use this when you want explicit typing and only have list[ModelSchemaValue] fields.
    For mixed list and dict fields, use convert_to_schema() instead.

    Args:
        *field_names: One or more field names to apply the conversion to.

    Returns:
        A class decorator that adds the necessary validators.

    Example:
        @convert_list_to_schema("route_hops", "values")
        class MyModel(BaseModel):
            route_hops: list[ModelSchemaValue] = Field(...)
            values: list[ModelSchemaValue] = Field(...)
    """

    def decorator(cls: type[T]) -> type[T]:
        # Runtime check for Pydantic internal API availability
        if not _PYDANTIC_INTERNALS_AVAILABLE:
            raise RuntimeError(  # error-ok: Pydantic internal API unavailable at import time
                f"convert_list_to_schema decorator requires Pydantic internal APIs "
                f"(pydantic._internal._decorators) which are not available. "
                f"Import error: {_PYDANTIC_IMPORT_ERROR}. "
                f"Current version: {PYDANTIC_VERSION}. "
                f"Tested with: Pydantic 2.6+ through 2.11+."
            )

        fields_to_convert = set(field_names)

        # ONEX_EXCLUDE: dict_str_any - pydantic validator requires flexible input/output types
        def convert_list_fields(
            cls_inner: type[Any],
            data: dict[str, Any] | Any,
        ) -> dict[str, Any] | Any:
            """Convert specified list fields to ModelSchemaValue."""
            if not isinstance(data, dict):
                return data

            schema_value_cls = _get_model_schema_value()

            for field_name in fields_to_convert:
                if field_name in data:
                    data[field_name] = _convert_list_value(
                        data[field_name], schema_value_cls
                    )

            return data

        validator_method = classmethod(convert_list_fields).__get__(None, cls)
        validator_name = f"_convert_list_to_schema_{'_'.join(sorted(field_names))}"
        setattr(cls, validator_name, validator_method)

        decorator_obj = Decorator(
            cls_ref=f"{cls.__module__}.{cls.__name__}:{id(cls)}",
            cls_var_name=validator_name,
            func=validator_method,
            shim=None,
            info=ModelValidatorDecoratorInfo(mode="before"),
        )
        cls.__pydantic_decorators__.model_validators[validator_name] = decorator_obj
        cls.model_rebuild(force=True)

        return cls

    return decorator


def convert_dict_to_schema(
    *field_names: str,
) -> Callable[[type[T]], type[T]]:
    """
    Specialized decorator for dict fields only.

    Use this when you want explicit typing and only have dict[str, ModelSchemaValue] fields.
    For mixed list and dict fields, use convert_to_schema() instead.

    Args:
        *field_names: One or more field names to apply the conversion to.

    Returns:
        A class decorator that adds the necessary validators.

    Example:
        @convert_dict_to_schema("metadata", "properties")
        class MyModel(BaseModel):
            metadata: dict[str, ModelSchemaValue] = Field(...)
            properties: dict[str, ModelSchemaValue] = Field(...)
    """

    def decorator(cls: type[T]) -> type[T]:
        # Runtime check for Pydantic internal API availability
        if not _PYDANTIC_INTERNALS_AVAILABLE:
            raise RuntimeError(  # error-ok: Pydantic internal API unavailable at import time
                f"convert_dict_to_schema decorator requires Pydantic internal APIs "
                f"(pydantic._internal._decorators) which are not available. "
                f"Import error: {_PYDANTIC_IMPORT_ERROR}. "
                f"Current version: {PYDANTIC_VERSION}. "
                f"Tested with: Pydantic 2.6+ through 2.11+."
            )

        fields_to_convert = set(field_names)

        # ONEX_EXCLUDE: dict_str_any - pydantic validator requires flexible input/output types
        def convert_dict_fields(
            cls_inner: type[Any],
            data: dict[str, Any] | Any,
        ) -> dict[str, Any] | Any:
            """Convert specified dict fields to ModelSchemaValue."""
            if not isinstance(data, dict):
                return data

            schema_value_cls = _get_model_schema_value()

            for field_name in fields_to_convert:
                if field_name in data:
                    data[field_name] = _convert_dict_value(
                        data[field_name], schema_value_cls
                    )

            return data

        validator_method = classmethod(convert_dict_fields).__get__(None, cls)
        validator_name = f"_convert_dict_to_schema_{'_'.join(sorted(field_names))}"
        setattr(cls, validator_name, validator_method)

        decorator_obj = Decorator(
            cls_ref=f"{cls.__module__}.{cls.__name__}:{id(cls)}",
            cls_var_name=validator_name,
            func=validator_method,
            shim=None,
            info=ModelValidatorDecoratorInfo(mode="before"),
        )
        cls.__pydantic_decorators__.model_validators[validator_name] = decorator_obj
        cls.model_rebuild(force=True)

        return cls

    return decorator
