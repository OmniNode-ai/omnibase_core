"""
Type constraints and protocols for better generic programming.

This module provides well-defined protocols, type variables with proper bounds,
and type constraints to replace overly broad generic usage patterns.
"""

from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

# Temporary local protocol definitions for validation purposes
# TODO: Replace with actual omnibase_spi imports when available


class Configurable(Protocol):
    """Protocol for configurable objects."""

    def configure(self, **kwargs: Any) -> bool: ...


class Executable(Protocol):
    """Protocol for executable objects."""

    def execute(self, *args: Any, **kwargs: Any) -> Any: ...


class Identifiable(Protocol):
    """Protocol for identifiable objects."""

    @property
    def id(self) -> str: ...


class ProtocolMetadataProvider(Protocol):
    """Protocol for objects that provide metadata."""

    @property
    def metadata(self) -> dict[str, Any]: ...


class Nameable(Protocol):
    """Protocol for nameable objects."""

    def get_name(self) -> str: ...

    def set_name(self, name: str) -> None: ...


class Serializable(Protocol):
    """Protocol for serializable objects."""

    def serialize(self) -> dict[str, Any]: ...


class ProtocolValidatable(Protocol):
    """Protocol for validatable objects."""

    def validate_instance(self) -> bool: ...


# Bounded type variables with proper constraints

# For Pydantic models
ModelType = TypeVar("ModelType", bound=BaseModel)

# For serializable objects
SerializableType = TypeVar("SerializableType", bound=Serializable)

# For identifiable objects
IdentifiableType = TypeVar("IdentifiableType", bound=Identifiable)

# For nameable objects
NameableType = TypeVar("NameableType", bound=Nameable)

# For validatable objects
ValidatableType = TypeVar("ValidatableType", bound=ProtocolValidatable)

# For configurable objects
ConfigurableType = TypeVar("ConfigurableType", bound=Configurable)

# For executable objects
ExecutableType = TypeVar("ExecutableType", bound=Executable)

# For objects with metadata
MetadataType = TypeVar("MetadataType", bound=ProtocolMetadataProvider)

# Simplified type variables for specific value types
# Replace overly generic TypeVars with more specific bounded types
NumericType = TypeVar("NumericType", int, float)  # More specific than NumberType
BasicValueType = TypeVar("BasicValueType", str, int, bool)  # Simplified primitive type

# Result and error types with simplified constraints
SuccessType = TypeVar("SuccessType")
# Simplified error type - use Exception as base for better type safety
ErrorType = TypeVar("ErrorType", bound=Exception)

# Collection types with simplified constraints
CollectionItemType = TypeVar("CollectionItemType", bound=BaseModel)
# Simplified dict value type - use more specific constraints
SimpleValueType = TypeVar("SimpleValueType", str, int, bool, float)

# Schema value types - standardized types for replacing hardcoded unions
# These types replace patterns like str | int | float | bool throughout the codebase

# ONEX-compliant type definitions (avoiding primitive soup anti-pattern)
# Use object with runtime validation instead of primitive soup unions

# Standard primitive value type - use object with runtime validation
# Instead of primitive soup Union[str, int, float, bool]
PrimitiveValueType = object  # Runtime validation required - see type guards below

# Context values - use object with runtime validation instead of open unions
# Instead of primitive soup Union[str, int, float, bool, list, dict]
ContextValueType = object  # Runtime validation required - see type guards below

# Complex context - use object with runtime validation
# Encourage structured models over generic fallbacks
ComplexContextValueType = object  # Runtime validation required - see type guards below


# Import abstract base classes from separate files (ONEX one-model-per-file)
from .model_base_collection import BaseCollection  # noqa: E402
from .model_base_factory import BaseFactory  # noqa: E402

# Type guards for runtime checking


def is_serializable(obj: object) -> bool:
    """Check if object implements Serializable protocol."""
    return hasattr(obj, "serialize") and callable(obj.serialize)


def is_identifiable(obj: object) -> bool:
    """Check if object implements Identifiable protocol."""
    return hasattr(obj, "id")


def is_nameable(obj: object) -> bool:
    """Check if object implements Nameable protocol."""
    return (
        hasattr(obj, "get_name")
        and callable(obj.get_name)
        and hasattr(obj, "set_name")
        and callable(obj.set_name)
    )


def is_validatable(obj: object) -> bool:
    """Check if object implements ProtocolValidatable protocol."""
    return hasattr(obj, "validate_instance") and callable(
        obj.validate_instance,
    )


def is_configurable(obj: object) -> bool:
    """Check if object implements Configurable protocol."""
    return hasattr(obj, "configure") and callable(obj.configure)


def is_executable(obj: object) -> bool:
    """Check if object implements Executable protocol."""
    return hasattr(obj, "execute") and callable(obj.execute)


def is_metadata_provider(obj: object) -> bool:
    """Check if object implements ProtocolMetadataProvider protocol."""
    return hasattr(obj, "metadata")


# Type guards for ONEX-compliant primitive value validation
# These replace primitive soup unions with runtime validation


def is_primitive_value(obj: object) -> bool:
    """Check if object is a valid primitive value (str, int, float, bool)."""
    return isinstance(obj, str | int | float | bool)


def is_context_value(obj: object) -> bool:
    """Check if object is a valid context value (primitive, list, or dict)."""
    if isinstance(obj, str | int | float | bool):
        return True
    if isinstance(obj, list):
        return True
    if isinstance(obj, dict):
        return all(isinstance(key, str) for key in obj)
    return False


def is_complex_context_value(obj: object) -> bool:
    """Check if object is a valid complex context value."""
    return is_context_value(obj)  # Same validation as context value


def validate_primitive_value(obj: object) -> bool:
    """Validate and ensure object is a primitive value."""
    if not is_primitive_value(obj):
        obj_type = type(obj).__name__
        msg = f"Expected primitive value (str, int, float, bool), got {obj_type}"
        raise TypeError(
            msg,
        )
    return True


def validate_context_value(obj: object) -> bool:
    """Validate and ensure object is a valid context value."""
    if not is_context_value(obj):
        obj_type = type(obj).__name__
        msg = f"Expected context value (primitive, list, or dict), got {obj_type}"
        raise TypeError(
            msg,
        )
    return True


# Export all types and utilities
__all__ = [
    # Abstract base classes
    "BaseCollection",
    "BaseFactory",
    "BasicValueType",
    "CollectionItemType",
    "ComplexContextValueType",
    "Configurable",
    "ConfigurableType",
    "ContextValueType",
    "ErrorType",
    "Executable",
    "ExecutableType",
    "Identifiable",
    "IdentifiableType",
    "MetadataType",
    # Type variables
    "ModelType",
    "Nameable",
    "NameableType",
    # Simplified type variables
    "NumericType",
    # Type aliases
    "PrimitiveValueType",
    "ProtocolMetadataProvider",
    "ProtocolValidatable",
    # Protocols
    "Serializable",
    "SerializableType",
    "SimpleValueType",
    "SuccessType",
    "ValidatableType",
    "is_complex_context_value",
    "is_configurable",
    "is_context_value",
    "is_executable",
    "is_identifiable",
    "is_metadata_provider",
    "is_nameable",
    # ONEX-compliant type validation guards
    "is_primitive_value",
    # Type guards
    "is_serializable",
    "is_validatable",
    "validate_context_value",
    "validate_primitive_value",
]
