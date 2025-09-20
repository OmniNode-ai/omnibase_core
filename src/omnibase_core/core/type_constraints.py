"""
Type constraints and protocols for better generic programming.

This module provides well-defined protocols, type variables with proper bounds,
and type constraints to replace overly broad generic usage patterns.
"""

from abc import ABC, abstractmethod
from typing import Any, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

# Protocol definitions for common interfaces


@runtime_checkable
class Serializable(Protocol):
    """Protocol for objects that can be serialized to dict."""

    def model_dump(
        self,
    ) -> dict[
        str,
        str
        | int
        | float
        | bool
        | list[str | int | float | bool]
        | dict[str, str | int | float | bool],
    ]:
        """Serialize to dictionary."""
        ...


@runtime_checkable
class Identifiable(Protocol):
    """Protocol for objects that have an ID."""

    @property
    def id(self) -> str:
        """Get the object ID."""
        ...


@runtime_checkable
class Nameable(Protocol):
    """Protocol for objects that have a name."""

    @property
    def name(self) -> str:
        """Get the object name."""
        ...


@runtime_checkable
class Validatable(Protocol):
    """Protocol for objects that can be validated."""

    def is_valid(self) -> bool:
        """Check if the object is valid."""
        ...


@runtime_checkable
class Configurable(Protocol):
    """Protocol for objects that can be configured."""

    def configure(self, **kwargs: Any) -> None:
        """Configure the object with parameters."""
        ...


@runtime_checkable
class Executable(Protocol):
    """Protocol for objects that can be executed."""

    def execute(self) -> Any:
        """Execute the object."""
        ...


@runtime_checkable
class MetadataProvider(Protocol):
    """Protocol for objects that provide metadata."""

    def get_metadata(self) -> dict[str, str | int | bool | float]:
        """Get metadata dictionary."""
        ...


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


# Abstract base classes for common patterns


class BaseCollection(ABC, BaseModel):
    """Abstract base class for typed collections."""

    @abstractmethod
    def add_item(self, item: Any) -> None:
        """Add an item to the collection."""
        ...

    @abstractmethod
    def remove_item(self, item: Any) -> bool:
        """Remove an item from the collection."""
        ...

    @abstractmethod
    def get_item_count(self) -> int:
        """Get the number of items in the collection."""
        ...


class BaseFactory(ABC, BaseModel):
    """Abstract base class for typed factories."""

    @abstractmethod
    def create(self, **kwargs: Any) -> Any:
        """Create an object."""
        ...

    @abstractmethod
    def can_create(self, type_name: str) -> bool:
        """Check if the factory can create the given type."""
        ...


class BaseProcessor(ABC, BaseModel):
    """Abstract base class for typed processors."""

    @abstractmethod
    def process(self, input_data: Any) -> Any:
        """Process input data."""
        ...

    @abstractmethod
    def can_process(self, input_data: Any) -> bool:
        """Check if the processor can handle the input data."""
        ...


# Type guards for runtime checking


def is_serializable(obj: Any) -> bool:
    """Check if object implements Serializable protocol."""
    return isinstance(obj, Serializable)


def is_identifiable(obj: Any) -> bool:
    """Check if object implements Identifiable protocol."""
    return isinstance(obj, Identifiable)


def is_nameable(obj: Any) -> bool:
    """Check if object implements Nameable protocol."""
    return isinstance(obj, Nameable)


def is_validatable(obj: Any) -> bool:
    """Check if object implements Validatable protocol."""
    return isinstance(obj, Validatable)


def is_configurable(obj: Any) -> bool:
    """Check if object implements Configurable protocol."""
    return isinstance(obj, Configurable)


def is_executable(obj: Any) -> bool:
    """Check if object implements Executable protocol."""
    return isinstance(obj, Executable)


def is_metadata_provider(obj: Any) -> bool:
    """Check if object implements MetadataProvider protocol."""
    return isinstance(obj, MetadataProvider)


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
