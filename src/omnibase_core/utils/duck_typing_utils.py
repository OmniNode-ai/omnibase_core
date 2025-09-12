"""
ONEX Utility: Duck Typing Helper

Utilities to simplify verbose duck typing patterns and improve code readability.
"""

from typing import Any, TypeVar

from omnibase_core.decorators.decorator_allow_any_type import allow_any_type

T = TypeVar("T")


@allow_any_type("duck_typing_requires_flexible_object_handling")
def safe_get(obj: Any, key: str, default: T | None = None) -> T | Any:
    """Safely get a value from an object using duck typing.

    Tries multiple access patterns:
    1. obj.get(key, default) for dict-like objects
    2. getattr(obj, key, default) for attribute access
    3. returns default if all fail

    Args:
        obj: Object to get value from
        key: Key or attribute name to access
        default: Default value to return if key not found

    Returns:
        Value from object or default
    """
    try:
        # Try dict-like access first
        if hasattr(obj, "get") and callable(obj.get):
            return obj.get(key, default)
    except (AttributeError, TypeError):
        pass

    try:
        # Try attribute access
        return getattr(obj, key, default)
    except (AttributeError, TypeError):
        pass

    # Return default if all access methods fail
    return default


@allow_any_type("duck_typing_requires_flexible_object_handling")
def safe_get_nested(obj: Any, *keys: str, default: T | None = None) -> T | Any:
    """Safely get a nested value from an object using duck typing.

    Args:
        obj: Object to get value from
        *keys: Sequence of keys to access nested values
        default: Default value to return if any key not found

    Returns:
        Nested value from object or default

    Example:
        safe_get_nested(data, "result", "collections", default=[])
        # equivalent to data.get("result", {}).get("collections", [])
    """
    current = obj
    for key in keys:
        current = safe_get(current, key, {})
        if current == {}:
            return default
    return current if current != {} else default


@allow_any_type("duck_typing_requires_flexible_object_handling")
def is_dict_like(obj: Any) -> bool:
    """Check if object is dict-like (has .get method).

    Args:
        obj: Object to check

    Returns:
        True if object has dict-like interface
    """
    return hasattr(obj, "get") and callable(getattr(obj, "get", None))


@allow_any_type("duck_typing_requires_flexible_object_handling")
def is_list_like(obj: Any) -> bool:
    """Check if object is list-like (iterable but not string).

    Args:
        obj: Object to check

    Returns:
        True if object is list-like
    """
    try:
        return (
            hasattr(obj, "__iter__")
            and not isinstance(obj, str | bytes)
            and not is_dict_like(obj)
        )
    except TypeError:
        return False


@allow_any_type("duck_typing_requires_flexible_object_handling")
def safe_iterate(obj: Any, default_empty: bool = True) -> list:
    """Safely iterate over an object, handling various types.

    Args:
        obj: Object to iterate over
        default_empty: Return empty list if iteration fails

    Returns:
        List of items from object or empty list
    """
    if obj is None:
        return []

    if is_list_like(obj):
        try:
            return list(obj)
        except (TypeError, ValueError) as e:
            # Re-raise validation errors for fail-fast behavior
            if "Validation" in type(e).__name__:
                raise

    if is_dict_like(obj):
        try:
            return list(obj.values())
        except (TypeError, ValueError) as e:
            # Re-raise validation errors for fail-fast behavior
            if "Validation" in type(e).__name__:
                raise

    # Single item -> wrap in list
    if default_empty:
        return [obj] if obj is not None else []
    return []


@allow_any_type("duck_typing_requires_flexible_object_handling")
def safe_cast(obj: Any, target_type: type, default: T | None = None) -> T | Any:
    """Safely cast object to target type with fallback.

    Args:
        obj: Object to cast
        target_type: Target type to cast to
        default: Default value if cast fails

    Returns:
        Cast object or default
    """
    if obj is None:
        return default

    try:
        return target_type(obj)
    except (TypeError, ValueError, AttributeError) as e:
        # Re-raise validation errors for fail-fast behavior
        if "Validation" in type(e).__name__:
            raise
        return default


class DuckTypingHelper:
    """Helper class for common duck typing operations."""

    @allow_any_type("duck_typing_requires_flexible_object_handling")
    def __init__(self, obj: Any):
        """Initialize with target object.

        Args:
            obj: Object to perform duck typing operations on
        """
        self.obj = obj

    def get(self, key: str, default: T | None = None) -> T | Any:
        """Get value using duck typing.

        Args:
            key: Key to access
            default: Default value

        Returns:
            Value or default
        """
        return safe_get(self.obj, key, default)

    def get_nested(self, *keys: str, default: T | None = None) -> T | Any:
        """Get nested value using duck typing.

        Args:
            *keys: Keys to access nested values
            default: Default value

        Returns:
            Nested value or default
        """
        return safe_get_nested(self.obj, *keys, default=default)

    def iterate(self, default_empty: bool = True) -> list:
        """Iterate over object safely.

        Args:
            default_empty: Return empty list if iteration fails

        Returns:
            List of items
        """
        return safe_iterate(self.obj, default_empty)

    def cast(self, target_type: type, default: T | None = None) -> T | Any:
        """Cast object to target type.

        Args:
            target_type: Target type
            default: Default value

        Returns:
            Cast object or default
        """
        return safe_cast(self.obj, target_type, default)

    @property
    def is_dict_like(self) -> bool:
        """Check if object is dict-like."""
        return is_dict_like(self.obj)

    @property
    def is_list_like(self) -> bool:
        """Check if object is list-like."""
        return is_list_like(self.obj)


# Convenience function to create helper
@allow_any_type("duck_typing_requires_flexible_object_handling")
def duck(obj: Any) -> DuckTypingHelper:
    """Create duck typing helper for object.

    Args:
        obj: Object to wrap

    Returns:
        Duck typing helper instance
    """
    return DuckTypingHelper(obj)
