# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Type constraints and protocols for better generic programming.

Well-defined protocols, type variables with proper bounds,
and type constraints to replace overly broad generic usage patterns.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
-----------------------------------------------
This module is part of a carefully managed import chain to avoid circular
dependencies. It imports only ``typing``, ``pydantic``, and
``omnibase_core.protocols`` at module level — never ``omnibase_core.models.*``.

Critical Rules:
- NEVER add a runtime OR TYPE_CHECKING import from ``omnibase_core.models.*``
  here. ``models.*`` imports this module, so a back-import re-introduces a cycle
  (and a types->models import-layering back-edge; see .importlinter,
  OMN-3210 / OMN-14337).
- All ``omnibase_core`` imports must stay within the protocols seam.
"""

from typing import TypeVar

# Import protocols from omnibase_core (Core-native protocols)
from pydantic import BaseModel

from omnibase_core.protocols import ProtocolConfigurable as Configurable
from omnibase_core.protocols import ProtocolExecutable as Executable
from omnibase_core.protocols import ProtocolIdentifiable as Identifiable
from omnibase_core.protocols import ProtocolMetadataProvider, ProtocolValidatable
from omnibase_core.protocols import ProtocolNameable as Nameable
from omnibase_core.protocols import ProtocolSerializable as Serializable

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
# Simplified dict[str, Any]value type - use more specific constraints
SimpleValueType = TypeVar("SimpleValueType", str, int, bool, float)

# Schema value types - standardized types for replacing hardcoded unions
# These types replace patterns like str | int | float | bool throughout the codebase

# ONEX-compatible type definitions (avoiding primitive soup anti-pattern)
# Use object with runtime validation instead of primitive soup unions

# Standard primitive value type - use object with runtime validation
# Instead of primitive soup Union[str, int, float, bool]
PrimitiveValueType = object  # Runtime validation required - see type guards below

# Context values - use object with runtime validation instead of open unions
# Instead of primitive soup Union[str, int, float, bool, list[Any], dict[str, Any]]
ContextValueType = object  # Runtime validation required - see type guards below

# Complex context - use object with runtime validation
# Encourage structured models over generic fallbacks
ComplexContextValueType = object  # Runtime validation required - see type guards below


# NOTE(OMN-14337): the former lazy ``__getattr__`` re-export of
# ModelBaseCollection/ModelBaseFactory from ``omnibase_core.models.base`` was
# removed. It was the last ``types -> models`` back-edge in this module and had
# zero importers (verified across omnibase_core/infra/spi). Import those classes
# directly from ``omnibase_core.models.base`` where needed.


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


# Type guards for ONEX-compatible primitive value validation
# These replace primitive soup unions with runtime validation


def is_primitive_value(obj: object) -> bool:
    """Check if object is a valid primitive value (str, int, float, bool)."""
    return isinstance(obj, (str, int, float, bool))


def is_context_value(obj: object) -> bool:
    """Check if object is a valid context value (primitive, list[Any], or dict[str, Any])."""
    if isinstance(obj, (str, int, float, bool)):
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
    """
    Validate and ensure object is a primitive value.

    Raises TypeError for invalid values.
    """
    if not is_primitive_value(obj):
        obj_type = type(obj).__name__
        msg = f"Expected primitive value (str, int, float, bool), got {obj_type}"
        raise TypeError(msg)  # error-ok: Standard Python type validation pattern
    return True


def validate_context_value(obj: object) -> bool:
    """
    Validate and ensure object is a valid context value.

    Raises TypeError for invalid values.
    """
    if not is_context_value(obj):
        obj_type = type(obj).__name__
        msg = f"Expected context value (primitive, list[Any], or dict[str, Any]), got {obj_type}"
        raise TypeError(msg)  # error-ok: Standard Python type validation pattern
    return True


# Export all types and utilities
__all__ = [
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
    # ONEX-compatible type validation guards
    "is_primitive_value",
    # Type guards
    "is_serializable",
    "is_validatable",
    "validate_context_value",
    "validate_primitive_value",
]
