"""
Core decorators for model configuration.

Provides decorators for configuring Pydantic models with flexible typing
requirements for CLI and tool interoperability.
"""

from typing import Any, Callable, Type, TypeVar

ModelType = TypeVar("ModelType", bound=Type[Any])


def allow_any_type(reason: str) -> Callable[[ModelType], ModelType]:
    """
    Decorator to allow Any types in model fields.

    Args:
        reason: Explanation for why Any types are needed

    Returns:
        The decorator function
    """

    def decorator(cls: ModelType) -> ModelType:
        # Add metadata to the class for documentation
        if not hasattr(cls, "_allow_any_reasons"):
            setattr(cls, "_allow_any_reasons", [])
        getattr(cls, "_allow_any_reasons").append(reason)
        return cls

    return decorator


def allow_dict_str_any(reason: str) -> Callable[[ModelType], ModelType]:
    """
    Decorator to allow dict[str, Any] types in model fields.

    Args:
        reason: Explanation for why dict[str, Any] is needed

    Returns:
        The decorator function
    """

    def decorator(cls: ModelType) -> ModelType:
        # Add metadata to the class for documentation
        if not hasattr(cls, "_allow_dict_str_any_reasons"):
            setattr(cls, "_allow_dict_str_any_reasons", [])
        getattr(cls, "_allow_dict_str_any_reasons").append(reason)
        return cls

    return decorator
