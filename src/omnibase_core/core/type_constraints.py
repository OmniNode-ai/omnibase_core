"""
Type constraints and protocols for better generic programming.

This module provides well-defined protocols, type variables with proper bounds,
and type constraints to replace overly broad generic usage patterns.
"""

from abc import ABC, abstractmethod
from typing import TypeVar

from omnibase_spi.protocols.types import ProtocolConfigurable as Configurable
from omnibase_spi.protocols.types import ProtocolExecutable as Executable
from omnibase_spi.protocols.types import ProtocolIdentifiable as Identifiable
from omnibase_spi.protocols.types import ProtocolMetadataProvider as MetadataProvider
from omnibase_spi.protocols.types import ProtocolNameable as Nameable
from omnibase_spi.protocols.types import ProtocolSerializable as Serializable
from omnibase_spi.protocols.types import ProtocolValidatable as Validatable
from pydantic import BaseModel

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
DictValueType = TypeVar("DictValueType", str, int, bool, float, list[object])


# Import abstract base classes from separate files (ONEX one-model-per-file)
from .model_base_collection import BaseCollection
from .model_base_factory import BaseFactory
from .model_base_processor import BaseProcessor

# Type guards for runtime checking


def is_serializable(obj: object) -> bool:
    """Check if object implements Serializable protocol."""
    return isinstance(obj, Serializable)


def is_identifiable(obj: object) -> bool:
    """Check if object implements Identifiable protocol."""
    return isinstance(obj, Identifiable)


def is_nameable(obj: object) -> bool:
    """Check if object implements Nameable protocol."""
    return isinstance(obj, Nameable)


def is_validatable(obj: object) -> bool:
    """Check if object implements Validatable protocol."""
    return isinstance(obj, Validatable)


def is_configurable(obj: object) -> bool:
    """Check if object implements Configurable protocol."""
    return isinstance(obj, Configurable)


def is_executable(obj: object) -> bool:
    """Check if object implements Executable protocol."""
    return isinstance(obj, Executable)


def is_metadata_provider(obj: object) -> bool:
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
