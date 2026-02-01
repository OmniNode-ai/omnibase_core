"""
Decorator for automatic conversion of Pydantic fields to ModelSchemaValue.

This decorator reduces boilerplate by automatically generating field validators
that convert list[Any] or dict[str, Any] fields to their type-safe ModelSchemaValue
equivalents.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
This module uses deferred imports to avoid circular dependencies.
ModelSchemaValue is imported inside functions, not at module level.

PYDANTIC INTERNAL API USAGE (Documented Limitation):
TECH_DEBT: This module uses Pydantic internal APIs because there is no public API
for dynamically adding model validators to an existing class post-creation.
When Pydantic 3.x is released, audit this module for breaking changes.
Issue tracking: If Pydantic adds a public API for dynamic validators, migrate to it.

Internal APIs used:
- pydantic._internal._decorators.Decorator
- pydantic._internal._decorators.ModelValidatorDecoratorInfo
- cls.__pydantic_decorators__ (semi-public, used in Pydantic docs)

Version Compatibility:
- Tested with Pydantic 2.6+ through 2.11+ (including pre-release versions)
- These internals are stable across Pydantic 2.x but may change in 3.x
- If Pydantic adds a public API for dynamic validators, migrate to it

Workaround Implementation Pattern:
1. Import internal classes with graceful fallback (try/except ImportError)
2. Store availability flag for runtime checks before decorator use
3. Create Decorator wrapper object matching Pydantic's internal structure
4. Register via cls.__pydantic_decorators__.model_validators dict
5. Call model_rebuild(force=True) to apply the new validator

What to Monitor in Future Pydantic Releases:
- Any public API for dynamic validator registration (preferred migration target)
- Changes to __pydantic_decorators__ structure or model_rebuild behavior
- New class decorator patterns that don't require internal API access
- Deprecation warnings in Pydantic's internal modules

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

import logging
import warnings
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar

# Module-level logger for conversion diagnostics
_logger = logging.getLogger(__name__)

from pydantic import VERSION as PYDANTIC_VERSION
from pydantic import BaseModel

# Import error codes for structured error handling
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import ModelOnexError
from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS

# Type-only imports for type checker satisfaction
if TYPE_CHECKING:
    from pydantic._internal._decorators import (
        Decorator as DecoratorType,
    )
    from pydantic._internal._decorators import (
        ModelValidatorDecoratorInfo as ModelValidatorDecoratorInfoType,
    )

    from omnibase_core.models.common.model_schema_value import ModelSchemaValue

# Pydantic internal API import with proper fallback handling.
# This is documented as a known limitation - no public API exists for
# dynamically adding model validators post-creation.
#
# Runtime imports stored in module-level variables with explicit types
# to satisfy type checkers while handling ImportError gracefully.
# Note: Using type[Any] since Decorator is a generic class and we don't
# need to track the specific type parameter at runtime.
#
# Import structure explanation (for type checker satisfaction):
# - We declare module-level variables with union types (X | None)
# - The try block imports and assigns the actual classes
# - The except block captures any import error for later diagnostics
# - Runtime checks verify availability before use
_PYDANTIC_INTERNALS_AVAILABLE: bool = False
_PYDANTIC_IMPORT_ERROR: ImportError | None = None

# Declare with explicit None initialization for type checker clarity
_Decorator: type[DecoratorType[Any]] | None = None
_ModelValidatorDecoratorInfo: type[ModelValidatorDecoratorInfoType] | None = None

try:
    # PYDANTIC INTERNAL API IMPORTS (Pydantic 2.x specific)
    # =====================================================
    # These imports access Pydantic's internal decorator registration mechanism.
    # This is a documented limitation - no public API exists for dynamically
    # adding model validators to an existing class post-creation.
    #
    # Decorator: Wrapper object that holds validator function + metadata
    #   - cls_ref: String identifying the class (module.ClassName:id)
    #   - cls_var_name: Name of the validator method on the class
    #   - func: The actual validator function
    #   - shim: Optional wrapper (we use None)
    #   - info: ModelValidatorDecoratorInfo with validation mode
    #
    # ModelValidatorDecoratorInfo: Metadata for model validators
    #   - mode: "before" (wrap) or "after" (plain) validation mode
    #
    # PYDANTIC 3.x MIGRATION NOTES:
    # - These internal classes may be relocated or renamed in Pydantic 3.x
    # - Monitor Pydantic changelog for changes to _internal._decorators module
    # - If a public API for dynamic validators is added, migrate to it
    # - Key change indicator: deprecation warnings in Pydantic 2.x releases
    from pydantic._internal._decorators import Decorator as _DecoratorImport
    from pydantic._internal._decorators import (
        ModelValidatorDecoratorInfo as _ModelValidatorDecoratorInfoImport,
    )

    # Assign to module-level variables (type checker sees these as potentially None)
    _Decorator = _DecoratorImport
    _ModelValidatorDecoratorInfo = _ModelValidatorDecoratorInfoImport
    _PYDANTIC_INTERNALS_AVAILABLE = True
except ImportError as e:
    # Capture error for diagnostic messages in runtime checks.
    # This typically happens when:
    # 1. Pydantic version < 2.0 (internal structure different)
    # 2. Pydantic 3.x changes internal module layout
    # 3. Pydantic is installed without full dependencies
    #
    # We log at WARNING level (not DEBUG) to ensure visibility of the issue.
    # The decorator will raise RuntimeError with full context when actually used,
    # but this warning helps with early diagnosis during module import.
    _PYDANTIC_IMPORT_ERROR = e
    _logger.warning(
        "Pydantic internal APIs not available (pydantic._internal._decorators): %s. "
        "convert_to_schema decorators will raise RuntimeError if used. "
        "Current Pydantic version: %s. Ensure Pydantic 2.6+ is installed.",
        e,
        PYDANTIC_VERSION,
    )


# Version compatibility check - fail fast for Pydantic 3.x, warn if outside tested range.
# Pre-release versions (e.g., "2.11.0a1", "2.11-dev", "2.11.0b1") may have non-numeric suffixes.
# Extract numeric portion only using a helper function for robust parsing.
#
# PYDANTIC 3.x MIGRATION WARNING:
# This module WILL LIKELY BREAK with Pydantic 3.x due to internal API changes.
# When Pydantic 3.x is released:
# 1. Check if pydantic._internal._decorators module still exists
# 2. Check if Decorator and ModelValidatorDecoratorInfo classes are still present
# 3. Check if __pydantic_decorators__ structure has changed
# 4. Monitor for any new public API for dynamic validator registration


def _parse_version_component(version_str: str, index: int) -> int:
    """Parse a version component, handling pre-release suffixes.

    This function safely extracts numeric version components from version strings
    that may contain pre-release identifiers, build metadata, or other non-numeric
    suffixes according to SemVer and PEP 440 conventions.

    Args:
        version_str: Full version string. Supported formats include:
            - Standard: "2.11.0", "3.0.0"
            - Pre-release alpha/beta/rc: "2.11.0a1", "2.11.0b1", "2.11.0rc1"
            - Development: "2.11-dev", "2.11.0.dev1"
            - Post-release: "2.11.0.post1"
            - Build metadata: "2.11.0+local"
        index: Which component to extract (0=major, 1=minor, 2=patch)

    Returns:
        The numeric portion of the version component.
        Returns 0 for any of these cases:
            - Parsing fails
            - Index exceeds available components
            - Component has no leading digits (e.g., "dev" -> 0)
            - Empty version string

    Examples:
        >>> _parse_version_component("2.11.0b1", 0)  # major
        2
        >>> _parse_version_component("2.11.0b1", 1)  # minor
        11
        >>> _parse_version_component("2.11.0b1", 2)  # patch (extracts "0" from "0b1")
        0
        >>> _parse_version_component("2.11-dev", 1)  # minor (extracts "11" from "11-dev")
        11
        >>> _parse_version_component("2", 1)  # missing component
        0
    """
    try:
        parts = version_str.split(".")
        if index >= len(parts):
            return 0
        component = parts[index]
        # Extract leading digits only (handles "11a1" -> 11, "0-dev" -> 0, "0b1" -> 0)
        numeric_chars: list[str] = []
        for char in component:
            if char.isdigit():
                numeric_chars.append(char)
            else:
                break
        if not numeric_chars:
            return 0
        return int("".join(numeric_chars))
    except (IndexError, ValueError):
        return 0


_PYDANTIC_MAJOR = _parse_version_component(PYDANTIC_VERSION, 0)
_PYDANTIC_MINOR = _parse_version_component(PYDANTIC_VERSION, 1)

# FAIL FAST for Pydantic 3.x - internal APIs will likely have changed
# This prevents silent failures and ensures developers are aware of the migration need
if _PYDANTIC_MAJOR >= 3:
    raise ImportError(  # error-ok: fail fast for incompatible Pydantic version
        f"convert_to_schema decorator is NOT compatible with Pydantic {_PYDANTIC_MAJOR}.x. "
        f"Current version: {PYDANTIC_VERSION}. "
        f"This module relies on Pydantic 2.x internal APIs (pydantic._internal._decorators) "
        f"which may have changed in Pydantic 3.x. "
        f"See TECH_DEBT comments in this module for migration guidance. "
        f"If Pydantic 3.x preserves these internal APIs unchanged, "
        f"update the version check in this module after testing."
    )

# Warn for older versions outside tested range
if _PYDANTIC_MAJOR != 2 or _PYDANTIC_MINOR < 6:
    warnings.warn(
        f"convert_to_schema decorator is tested with Pydantic 2.6+. "
        f"Current version: {PYDANTIC_VERSION}. Internal APIs may differ.",
        UserWarning,
        stacklevel=2,
    )

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


def _escape_field_name_for_validator(name: str) -> str:
    """Escape field name for use in validator name to prevent collisions.

    The validator name uses '__' (double underscore) as a separator between
    field names. To prevent collisions when field names themselves contain '__',
    we escape '__' to '___' (triple underscore).

    This ensures unambiguous parsing:
    - '__' in the result always means separator
    - '___' in the result always means escaped '__' from the original name

    Examples:
        >>> _escape_field_name_for_validator("a_b")  # Single underscore: unchanged
        'a_b'
        >>> _escape_field_name_for_validator("a__b")  # Double underscore: escaped
        'a___b'
        >>> _escape_field_name_for_validator("a___b")  # Triple underscore: still escapes __
        'a____b'

    Args:
        name: The field name to escape.

    Returns:
        The escaped field name safe for use in validator names.
    """
    return name.replace("__", "___")


def _convert_list_value(
    value: list[Any] | None, schema_cls: type[ModelSchemaValue]
) -> list[Any] | None:
    """Convert a list value to list of ModelSchemaValue.

    Returns None if input is None (preserves optional field semantics).
    Returns [] if input is an empty list.
    """
    if value is None:
        return None
    if not value:  # Empty list
        return []
    # Homogeneous list assumption: if first element is ModelSchemaValue,
    # all elements are (lists come from single serialization source)
    # Note: len(value) > 0 check removed - guaranteed non-empty after early return
    if isinstance(value[0], schema_cls):
        return value
    # Check if first element is a serialized ModelSchemaValue dict
    # (from model_dump round-trip)
    # Note: len(value) > 0 check removed - guaranteed non-empty after early return
    if isinstance(value[0], dict) and _is_serialized_schema_value(value[0]):
        # Let Pydantic handle deserialization
        return value
    try:
        return [schema_cls.from_value(item) for item in value]
    except PYDANTIC_MODEL_ERRORS as e:
        first_item_type = type(value[0]).__name__ if value else "N/A"
        _logger.warning(
            "Failed to convert list items to ModelSchemaValue. "
            "List had %d items, first item type: %s. Error: %s",
            len(value),
            first_item_type,
            str(e),
        )
        raise ModelOnexError(
            message=(
                f"Failed to convert list to ModelSchemaValue: {e}. "
                f"Ensure list items are convertible (primitives, dicts, or lists)."
            ),
            error_code=EnumCoreErrorCode.CONVERSION_ERROR,
            context={
                "list_length": len(value),
                "first_item_type": first_item_type,
                "original_error": str(e),
            },
        ) from e


# ONEX_EXCLUDE: dict_str_any - schema conversion utility for dynamic types
def _convert_dict_value(
    value: dict[str, Any] | None,
    schema_cls: type[ModelSchemaValue],
) -> dict[str, Any] | None:
    """Convert a dict value to dict of ModelSchemaValue.

    Returns None if input is None (preserves optional field semantics).
    Returns {} if input is an empty dict.

    Note on None handling:
        When checking if values are already ModelSchemaValue, we skip None values
        because None can appear in both raw dicts (to be converted to null) and
        in dicts with mixed ModelSchemaValue instances. By finding the first
        non-None value, we can reliably determine if conversion is needed.

    Note on serialized value handling:
        Dict values may be serialized ModelSchemaValue dicts (from model_dump).
        We detect this by checking if the first non-None value is a dict with
        'value_type' key. In this case, we pass through for Pydantic deserialization
        rather than wrapping in another ModelSchemaValue.
    """
    if value is None:
        return None
    if not value:  # Empty dict
        return {}
    # Check if values are already ModelSchemaValue
    # Skip None values when determining conversion status, as None can appear
    # in both raw dicts and dicts that are already partially converted.
    first_non_none_value = None
    for v in value.values():
        if v is not None:
            first_non_none_value = v
            break

    # If all values are None, we still need to convert them to null ModelSchemaValue
    if first_non_none_value is None:
        try:
            return {k: schema_cls.from_value(v) for k, v in value.items()}
        except PYDANTIC_MODEL_ERRORS as e:
            sample_keys = list(value.keys())[:5]
            _logger.warning(
                "Failed to convert dict with all-None values to ModelSchemaValue. "
                "Dict had %d keys (sample: %s). Error: %s",
                len(value),
                sample_keys,
                str(e),
            )
            raise ModelOnexError(
                message=(
                    f"Failed to convert dict to ModelSchemaValue: {e}. "
                    f"Ensure dict values are convertible (primitives, dicts, or lists)."
                ),
                error_code=EnumCoreErrorCode.CONVERSION_ERROR,
                context={
                    "dict_key_count": len(value),
                    "sample_keys": sample_keys,
                    "original_error": str(e),
                },
            ) from e

    # If we found a non-None value and it's already a ModelSchemaValue,
    # assume the dict is already converted (homogeneous assumption).
    # However, we still need to convert any None values to ModelSchemaValue.
    if isinstance(first_non_none_value, schema_cls):
        # Check if there are any None values that need conversion
        has_none_values = any(v is None for v in value.values())
        if has_none_values:
            # Convert None values while preserving already-converted values
            return {
                k: schema_cls.from_value(v) if v is None else v
                for k, v in value.items()
            }
        return value

    # Check if first non-None value is a serialized ModelSchemaValue dict
    # (from model_dump round-trip). If so, let Pydantic handle deserialization.
    # However, we still need to convert any None values to ModelSchemaValue
    # since raw None cannot be deserialized by Pydantic into ModelSchemaValue.
    if isinstance(first_non_none_value, dict) and _is_serialized_schema_value(
        first_non_none_value
    ):
        # Check if there are any None values that need conversion
        has_none_values = any(v is None for v in value.values())
        if has_none_values:
            # Convert None values while preserving already-serialized values
            return {
                k: schema_cls.from_value(v) if v is None else v
                for k, v in value.items()
            }
        return value

    # Convert raw values to ModelSchemaValue
    try:
        return {k: schema_cls.from_value(v) for k, v in value.items()}
    except PYDANTIC_MODEL_ERRORS as e:
        sample_keys = list(value.keys())[:5]
        _logger.warning(
            "Failed to convert dict values to ModelSchemaValue. "
            "Dict had %d keys (sample: %s). Error: %s",
            len(value),
            sample_keys,
            str(e),
        )
        raise ModelOnexError(
            message=(
                f"Failed to convert dict to ModelSchemaValue: {e}. "
                f"Ensure dict values are convertible (primitives, dicts, or lists)."
            ),
            error_code=EnumCoreErrorCode.CONVERSION_ERROR,
            context={
                "dict_key_count": len(value),
                "sample_keys": sample_keys,
                "original_error": str(e),
            },
        ) from e


def _convert_value(value: Any, schema_cls: type[ModelSchemaValue]) -> Any:
    """Convert a value (list or dict) to ModelSchemaValue format.

    This function handles conversion of raw values to ModelSchemaValue instances.
    It preserves the collection type (list vs dict) to ensure proper field semantics.

    Args:
        value: The value to convert. Can be None, list, dict, or already-converted
               ModelSchemaValue instances.
        schema_cls: The ModelSchemaValue class to use for conversion.

    Returns:
        The converted value, or the original value if already converted or unexpected type.

    Note:
        None values are returned as-is to allow Pydantic's default_factory
        to provide the appropriate default. This ensures dict fields don't
        incorrectly receive an empty list, and vice versa.

        Empty collections are returned as their respective types ([] or {})
        to preserve the field's expected collection type.
    """
    if value is None:
        return None

    # Handle empty collections explicitly - preserve collection type
    # Type-safe checks: verify type first, then check emptiness.
    # This avoids calling helper functions for empty collections (optimization)
    # and is safer than equality comparison (e.g., numpy arrays return arrays
    # from == comparisons, not booleans).
    if isinstance(value, list) and not value:
        return []
    if isinstance(value, dict) and not value:
        return {}

    # Convert based on collection type
    if isinstance(value, list):
        return _convert_list_value(value, schema_cls)
    if isinstance(value, dict):
        # Note: We do NOT check _is_serialized_schema_value here for dict fields.
        # For dict[str, ModelSchemaValue] fields, we always want to convert the
        # values of the dict, not treat the dict itself as a serialized value.
        # The _convert_dict_value function handles serialized values within
        # the dict (i.e., when dict VALUES are serialized ModelSchemaValue dicts).
        #
        # A dict like {"value_type": "string", "value": "hello"} passed to a
        # dict[str, ModelSchemaValue] field should have both keys converted to
        # ModelSchemaValue instances, NOT be passed through as a single value.
        return _convert_dict_value(value, schema_cls)

    # For unexpected types, raise an error instead of silently passing through.
    # The decorator is designed for list[ModelSchemaValue] or dict[str, ModelSchemaValue]
    # fields only. Unexpected types indicate a configuration error that should be
    # surfaced to the developer, not silently ignored.
    value_repr = (
        repr(value) if not isinstance(value, (bytes, bytearray)) else "<binary data>"
    )
    _logger.error(
        "Unexpected value type in schema conversion: %s (value: %s). "
        "Expected list or dict for schema conversion. Check field type annotations.",
        type(value).__name__,
        value_repr,
    )
    raise ModelOnexError(
        message=(
            f"Cannot convert value of type '{type(value).__name__}' to ModelSchemaValue. "
            f"The @convert_to_schema decorator only supports list[ModelSchemaValue] or "
            f"dict[str, ModelSchemaValue] fields. Received: {value_repr}"
        ),
        error_code=EnumCoreErrorCode.CONVERSION_ERROR,
        context={
            "value_type": type(value).__name__,
            "expected_types": ["list", "dict"],
        },
    )


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

        # NOTE(OMN-1302): Dynamic attribute for collision detection. Safe because read via getattr.
        # Must set before creating classmethod since bound methods don't accept new attributes.
        convert_schema_fields._convert_to_schema_generated = True  # type: ignore[attr-defined]

        # Create a bound classmethod
        validator_method = classmethod(convert_schema_fields).__get__(None, cls)

        # Generate a unique, deterministic validator name
        # Collision prevention strategy:
        # 1. Sort field names for determinism - same fields always produce same validator name
        # 2. Use '__' (double underscore) as separator between field names
        # 3. Escape '__' in field names to '___' to prevent ambiguity
        #
        # Example collision prevention:
        #   ("a_b", "c") -> "a_b__c" vs ("a", "b_c") -> "a__b_c" (different!)
        #   ("a__b",) -> "a___b" vs ("a", "b") -> "a__b" (different!)
        escaped_names = [
            _escape_field_name_for_validator(n) for n in sorted(field_names)
        ]
        validator_name = f"_convert_to_schema_{'__'.join(escaped_names)}"

        # Check for validator name collision with existing class attributes.
        # This prevents silently overwriting user-defined methods or validators.
        # Note: We check the class's __dict__ directly to avoid picking up inherited attrs,
        # but also check hasattr for completeness (catches inherited validators with same name).
        if hasattr(cls, validator_name):
            existing_attr = getattr(cls, validator_name, None)
            # Check for marker on the underlying function (__func__ for bound methods)
            # If the existing attr has our marker, it's from a previous decoration - allow override
            underlying_func = getattr(existing_attr, "__func__", existing_attr)
            if not getattr(underlying_func, "_convert_to_schema_generated", False):
                _logger.warning(
                    "Validator name collision detected: %s already exists on %s. "
                    "The existing attribute will be replaced. If this is unintentional, "
                    "check for field names that might create colliding validator names.",
                    validator_name,
                    cls.__name__,
                )

        # Add method to class (marker already set on the function before classmethod creation)
        setattr(cls, validator_name, validator_method)

        # Create Decorator object matching Pydantic's internal structure
        # Explicit None check for type narrowing - runtime check above guarantees availability
        if _Decorator is None or _ModelValidatorDecoratorInfo is None:
            raise ModelOnexError(
                message=(
                    "Pydantic internal decorator classes are not available. "
                    "This should not occur after the availability check above."
                ),
                error_code=EnumCoreErrorCode.DEPENDENCY_UNAVAILABLE,
                context={
                    "decorator_available": _Decorator is not None,
                    "validator_info_available": _ModelValidatorDecoratorInfo
                    is not None,
                    "pydantic_version": PYDANTIC_VERSION,
                },
            )

        # Assign to local variables for type narrowing - type checkers cannot narrow
        # module-level variables after guard checks due to potential concurrent modification.
        # We add explicit assertions after assignment to guarantee type narrowing for all
        # type checkers (mypy, pyright) that may not track the module-level None check.
        DecoratorClass = _Decorator
        ValidatorInfoClass = _ModelValidatorDecoratorInfo

        # Explicit assertions for type narrowing - guaranteed by the None check above.
        # These assertions satisfy strict type checkers that don't narrow module-level vars.
        assert DecoratorClass is not None, "Guaranteed non-None by availability check"
        assert ValidatorInfoClass is not None, (
            "Guaranteed non-None by availability check"
        )

        # PYDANTIC INTERNAL: Create Decorator object matching Pydantic's internal structure
        # This is the core workaround for dynamic validator registration.
        # The Decorator class wraps our validator with the metadata Pydantic needs.
        # Pydantic 3.x migration: Check if Decorator signature/structure changes.
        decorator_obj = DecoratorClass(
            cls_ref=f"{cls.__module__}.{cls.__name__}:{id(cls)}",
            cls_var_name=validator_name,
            func=validator_method,
            shim=None,  # No wrapper needed for simple validators
            info=ValidatorInfoClass(
                mode="before"
            ),  # "before" = runs before field validation
        )

        # PYDANTIC INTERNAL: Register via __pydantic_decorators__ (semi-public API)
        # This dict is documented in Pydantic but its structure may change.
        # Pydantic 3.x migration: Monitor for changes to model_validators dict structure.
        cls.__pydantic_decorators__.model_validators[validator_name] = decorator_obj

        # PYDANTIC INTERNAL: model_rebuild() applies the new validator
        # force=True ensures the model is rebuilt even if it appears unchanged.
        # This is required because we modified __pydantic_decorators__ directly.
        # Pydantic 3.x migration: Check if model_rebuild signature/behavior changes.
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

        # NOTE(OMN-1302): Dynamic attribute for collision detection. Safe because read via getattr.
        # Must set before creating classmethod since bound methods don't accept new attributes.
        convert_list_fields._convert_to_schema_generated = True  # type: ignore[attr-defined]

        validator_method = classmethod(convert_list_fields).__get__(None, cls)
        # Generate a unique, deterministic validator name (see convert_to_schema for details)
        escaped_names = [
            _escape_field_name_for_validator(n) for n in sorted(field_names)
        ]
        validator_name = f"_convert_list_to_schema_{'__'.join(escaped_names)}"

        # Check for validator name collision (see convert_to_schema for detailed explanation)
        if hasattr(cls, validator_name):
            existing_attr = getattr(cls, validator_name, None)
            underlying_func = getattr(existing_attr, "__func__", existing_attr)
            if not getattr(underlying_func, "_convert_to_schema_generated", False):
                _logger.warning(
                    "Validator name collision detected: %s already exists on %s. "
                    "The existing attribute will be replaced.",
                    validator_name,
                    cls.__name__,
                )

        # Add method to class (marker already set on the function before classmethod creation)
        setattr(cls, validator_name, validator_method)

        # Explicit None check for type narrowing - runtime check above guarantees availability
        if _Decorator is None or _ModelValidatorDecoratorInfo is None:
            raise ModelOnexError(
                message=(
                    "Pydantic internal decorator classes are not available. "
                    "This should not occur after the availability check above."
                ),
                error_code=EnumCoreErrorCode.DEPENDENCY_UNAVAILABLE,
                context={
                    "decorator_available": _Decorator is not None,
                    "validator_info_available": _ModelValidatorDecoratorInfo
                    is not None,
                    "pydantic_version": PYDANTIC_VERSION,
                },
            )

        # Assign to local variables for type narrowing - type checkers cannot narrow
        # module-level variables after guard checks due to potential concurrent modification.
        # We add explicit assertions after assignment to guarantee type narrowing for all
        # type checkers (mypy, pyright) that may not track the module-level None check.
        DecoratorClass = _Decorator
        ValidatorInfoClass = _ModelValidatorDecoratorInfo

        # Explicit assertions for type narrowing - guaranteed by the None check above.
        # These assertions satisfy strict type checkers that don't narrow module-level vars.
        assert DecoratorClass is not None, "Guaranteed non-None by availability check"
        assert ValidatorInfoClass is not None, (
            "Guaranteed non-None by availability check"
        )

        # PYDANTIC INTERNAL: See convert_to_schema for detailed documentation
        decorator_obj = DecoratorClass(
            cls_ref=f"{cls.__module__}.{cls.__name__}:{id(cls)}",
            cls_var_name=validator_name,
            func=validator_method,
            shim=None,
            info=ValidatorInfoClass(mode="before"),
        )
        # PYDANTIC INTERNAL: Register and rebuild (see convert_to_schema for details)
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

        # NOTE(OMN-1302): Dynamic attribute for collision detection. Safe because read via getattr.
        # Must set before creating classmethod since bound methods don't accept new attributes.
        convert_dict_fields._convert_to_schema_generated = True  # type: ignore[attr-defined]

        validator_method = classmethod(convert_dict_fields).__get__(None, cls)
        # Generate a unique, deterministic validator name (see convert_to_schema for details)
        escaped_names = [
            _escape_field_name_for_validator(n) for n in sorted(field_names)
        ]
        validator_name = f"_convert_dict_to_schema_{'__'.join(escaped_names)}"

        # Check for validator name collision (see convert_to_schema for detailed explanation)
        if hasattr(cls, validator_name):
            existing_attr = getattr(cls, validator_name, None)
            underlying_func = getattr(existing_attr, "__func__", existing_attr)
            if not getattr(underlying_func, "_convert_to_schema_generated", False):
                _logger.warning(
                    "Validator name collision detected: %s already exists on %s. "
                    "The existing attribute will be replaced.",
                    validator_name,
                    cls.__name__,
                )

        # Add method to class (marker already set on the function before classmethod creation)
        setattr(cls, validator_name, validator_method)

        # Explicit None check for type narrowing - runtime check above guarantees availability
        if _Decorator is None or _ModelValidatorDecoratorInfo is None:
            raise ModelOnexError(
                message=(
                    "Pydantic internal decorator classes are not available. "
                    "This should not occur after the availability check above."
                ),
                error_code=EnumCoreErrorCode.DEPENDENCY_UNAVAILABLE,
                context={
                    "decorator_available": _Decorator is not None,
                    "validator_info_available": _ModelValidatorDecoratorInfo
                    is not None,
                    "pydantic_version": PYDANTIC_VERSION,
                },
            )

        # Assign to local variables for type narrowing - type checkers cannot narrow
        # module-level variables after guard checks due to potential concurrent modification.
        # We add explicit assertions after assignment to guarantee type narrowing for all
        # type checkers (mypy, pyright) that may not track the module-level None check.
        DecoratorClass = _Decorator
        ValidatorInfoClass = _ModelValidatorDecoratorInfo

        # Explicit assertions for type narrowing - guaranteed by the None check above.
        # These assertions satisfy strict type checkers that don't narrow module-level vars.
        assert DecoratorClass is not None, "Guaranteed non-None by availability check"
        assert ValidatorInfoClass is not None, (
            "Guaranteed non-None by availability check"
        )

        # PYDANTIC INTERNAL: See convert_to_schema for detailed documentation
        decorator_obj = DecoratorClass(
            cls_ref=f"{cls.__module__}.{cls.__name__}:{id(cls)}",
            cls_var_name=validator_name,
            func=validator_method,
            shim=None,
            info=ValidatorInfoClass(mode="before"),
        )
        # PYDANTIC INTERNAL: Register and rebuild (see convert_to_schema for details)
        cls.__pydantic_decorators__.model_validators[validator_name] = decorator_obj
        cls.model_rebuild(force=True)

        return cls

    return decorator
