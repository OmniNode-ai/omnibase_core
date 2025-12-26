"""
Core decorators for model configuration.

Provides decorators for configuring Pydantic models with flexible typing
requirements for CLI and tool interoperability.
"""

from collections.abc import Callable
from typing import TypeVar

__all__ = [
    "allow_any_type",
    "allow_string_id",
    "allow_dict_str_any",
]

# TypeVar for any class type (not just Pydantic models)
# This allows the decorators to work with both Pydantic models and plain classes
ClassType = TypeVar("ClassType", bound=type)


def allow_any_type(reason: str) -> Callable[[ClassType], ClassType]:
    """
    Decorator to allow Any types in model fields.

    Args:
        reason: Explanation for why Any types are needed

    Returns:
        The decorator function
    """

    def decorator(cls: ClassType) -> ClassType:
        # Add metadata to the class for documentation
        # Use setattr/getattr for dynamic attribute access to maintain type safety
        # Note: Use explicit None check instead of `or []` to handle falsy values correctly
        # (empty list should be preserved, not replaced with a new list)
        attr_value = getattr(cls, "_allow_any_reasons", None)
        if attr_value is None:
            reasons: list[str] = []
            setattr(cls, "_allow_any_reasons", reasons)
        else:
            reasons = attr_value
        reasons.append(reason)
        return cls

    return decorator


def allow_string_id(reason: str) -> Callable[[ClassType], ClassType]:
    """
    Decorator to allow string ID fields instead of UUID.

    Use this when integrating with external systems that require string identifiers
    (e.g., Consul service IDs, Kubernetes resource names, cloud provider resource IDs).

    Args:
        reason: Explanation for why string IDs are needed (e.g., external system constraint)

    Returns:
        The decorator function
    """

    def decorator(cls: ClassType) -> ClassType:
        # Add metadata to the class for documentation
        # Use setattr/getattr for dynamic attribute access to maintain type safety
        # Note: Use explicit None check instead of `or []` to handle falsy values correctly
        # (empty list should be preserved, not replaced with a new list)
        attr_value = getattr(cls, "_allow_string_id_reasons", None)
        if attr_value is None:
            reasons: list[str] = []
            setattr(cls, "_allow_string_id_reasons", reasons)
        else:
            reasons = attr_value
        reasons.append(reason)
        return cls

    return decorator


def allow_dict_str_any(reason: str) -> Callable[[ClassType], ClassType]:
    """
    Decorator to allow dict[str, Any] fields in models.

    Use this when a model requires flexible dictionary fields for dynamic or
    user-defined data (e.g., custom fields, metadata, configuration options).

    Args:
        reason: Explanation for why dict[str, Any] is needed

    Returns:
        The decorator function
    """

    def decorator(cls: ClassType) -> ClassType:
        # Add metadata to the class for documentation
        # Use setattr/getattr for dynamic attribute access to maintain type safety
        # Note: Use explicit None check instead of `or []` to handle falsy values correctly
        # (empty list should be preserved, not replaced with a new list)
        attr_value = getattr(cls, "_allow_dict_str_any_reasons", None)
        if attr_value is None:
            reasons: list[str] = []
            setattr(cls, "_allow_dict_str_any_reasons", reasons)
        else:
            reasons = attr_value
        reasons.append(reason)
        return cls

    return decorator
