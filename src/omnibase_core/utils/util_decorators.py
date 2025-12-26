"""
Core decorators for model configuration.

Provides decorators for configuring Pydantic models with flexible typing
requirements for CLI and tool interoperability.
"""

from collections.abc import Callable
from typing import TypeVar

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
        reasons: list[str] = getattr(cls, "_allow_any_reasons", None) or []
        if not hasattr(cls, "_allow_any_reasons"):
            setattr(cls, "_allow_any_reasons", reasons)
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
        reasons: list[str] = getattr(cls, "_allow_string_id_reasons", None) or []
        if not hasattr(cls, "_allow_string_id_reasons"):
            setattr(cls, "_allow_string_id_reasons", reasons)
        reasons.append(reason)
        return cls

    return decorator
