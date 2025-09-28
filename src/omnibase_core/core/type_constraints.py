"""
Type constraints and protocols for better generic programming.

This module provides well-defined protocols, type variables with proper bounds,
and type constraints to replace overly broad generic usage patterns.
"""

from abc import ABC, abstractmethod
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


class MetadataProvider(Protocol):
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


class Validatable(Protocol):
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
ValidatableType = TypeVar("ValidatableType", bound=Validatable)

# For configurable objects
ConfigurableType = TypeVar("ConfigurableType", bound=Configurable)

# For executable objects
ExecutableType = TypeVar("ExecutableType", bound=Executable)

# For objects with metadata
MetadataType = TypeVar("MetadataType", bound=MetadataProvider)

# Constrained type variables for specific value types
StringType = TypeVar("StringType", bound=str)
NumberType = TypeVar("NumberType", int, float)
PrimitiveType = TypeVar("PrimitiveType", str, int, bool, float)

# Result and error types with constraints
SuccessType = TypeVar("SuccessType")
ErrorType = TypeVar("ErrorType", str, Exception, BaseException)

# Collection types with constraints
CollectionItemType = TypeVar("CollectionItemType", bound=BaseModel)
DictValueType = TypeVar("DictValueType", str, int, bool, float, list[Any])


# Import abstract base classes from separate files (ONEX one-model-per-file)
from .model_base_collection import BaseCollection
from .model_base_factory import BaseFactory
from .model_base_processor import BaseProcessor

# Type guards for runtime checking


def is_serializable(obj: Any) -> bool:
    """Check if object implements Serializable protocol."""
    return hasattr(obj, "serialize") and callable(getattr(obj, "serialize"))


def is_identifiable(obj: Any) -> bool:
    """Check if object implements Identifiable protocol."""
    return hasattr(obj, "id")


def is_nameable(obj: Any) -> bool:
    """Check if object implements Nameable protocol."""
    return (
        hasattr(obj, "get_name")
        and callable(getattr(obj, "get_name"))
        and hasattr(obj, "set_name")
        and callable(getattr(obj, "set_name"))
    )


def is_validatable(obj: Any) -> bool:
    """Check if object implements Validatable protocol."""
    return hasattr(obj, "validate_instance") and callable(
        getattr(obj, "validate_instance")
    )


def is_configurable(obj: Any) -> bool:
    """Check if object implements Configurable protocol."""
    return hasattr(obj, "configure") and callable(getattr(obj, "configure"))


def is_executable(obj: Any) -> bool:
    """Check if object implements Executable protocol."""
    return hasattr(obj, "execute") and callable(getattr(obj, "execute"))


def is_metadata_provider(obj: Any) -> bool:
    """Check if object implements MetadataProvider protocol."""
    return hasattr(obj, "metadata")


# Export all types and utilities
__all__ = [
    # Protocols
    "Serializable",
    "Identifiable",
    "Nameable",
    "Validatable",
    "Configurable",
    "Executable",
    "MetadataProvider",
    # Type variables
    "ModelType",
    "SerializableType",
    "IdentifiableType",
    "NameableType",
    "ValidatableType",
    "ConfigurableType",
    "ExecutableType",
    "MetadataType",
    "StringType",
    "NumberType",
    "PrimitiveType",
    "SuccessType",
    "ErrorType",
    "CollectionItemType",
    "DictValueType",
    # Abstract base classes
    "BaseCollection",
    "BaseFactory",
    "BaseProcessor",
    # Type guards
    "is_serializable",
    "is_identifiable",
    "is_nameable",
    "is_validatable",
    "is_configurable",
    "is_executable",
    "is_metadata_provider",
]
