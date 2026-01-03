"""
Type constraints and protocols for better generic programming.

This module provides well-defined protocols, type variables with proper bounds,
and type constraints to replace overly broad generic usage patterns.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports:
- typing, pydantic (standard library)
- No imports from omnibase_core at module level (to break circular chain)

Type-Only Imports (Protected by TYPE_CHECKING):
- omnibase_core.errors.error_codes (used only for type hints)
- omnibase_core.models.base (lazy loaded via __getattr__)

Lazy Imports:
- models.base: Loaded via __getattr__ when accessed

Import Chain Position:
1. types.core_types (no external deps)
2. errors.error_codes → types.core_types
3. models.common.model_schema_value → errors.error_codes
4. THIS MODULE → TYPE_CHECKING import of errors.error_codes (NO runtime import!)
5. models.* → THIS MODULE (runtime imports)
6. THIS MODULE → models.base (lazy __getattr__ only)

Critical Rules:
- NEVER add runtime imports from errors.error_codes at module level
- NEVER add runtime imports from models.* at module level
- All imports from omnibase_core MUST be TYPE_CHECKING or lazy (inside functions/__getattr__)
"""

from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    # Type-only imports for static analysis (mypy, IDEs)
    # These don't run at runtime, avoiding circular imports
    from omnibase_core.models.base import ModelBaseCollection, ModelBaseFactory

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


# LAZY IMPORT PATTERN: Import abstract base classes from separate files
# Critical: This must remain a lazy import to break the circular dependency chain
#
# Import Chain:
# 1. models.* imports from THIS MODULE (types.constraints)
# 2. THIS MODULE needs ModelBaseCollection/ModelBaseFactory from models.base
# 3. Solution: Use TYPE_CHECKING + lazy __getattr__ to defer runtime import
#
# Why this works:
# - TYPE_CHECKING provides types for static analysis (mypy, IDEs)
# - __getattr__ defers actual import until attribute is accessed
# - By the time __getattr__ runs, models.* has already imported types.constraints
# - This breaks the circular dependency at module import time
if TYPE_CHECKING:
    # Type aliases for test compatibility
    BaseCollection = ModelBaseCollection
    BaseFactory = ModelBaseFactory
else:
    # Lazy import at runtime to avoid circular dependencies
    # WARNING: Do NOT change this to a regular import - it will break the import chain!
    def __getattr__(name: str) -> object:
        """
        Lazy import for ModelBaseCollection and ModelBaseFactory to avoid circular imports.

        This function is called when an attribute is not found in the module.
        It imports the models.base module only when needed, which happens AFTER
        models.* has already imported types.constraints, thus breaking the cycle.
        """
        if name in (
            "ModelBaseCollection",
            "ModelBaseFactory",
            "BaseCollection",
            "BaseFactory",
        ):
            # Lazy import - happens only when these names are accessed
            from omnibase_core.models.base import ModelBaseCollection, ModelBaseFactory

            globals()["ModelBaseCollection"] = ModelBaseCollection
            globals()["ModelBaseFactory"] = ModelBaseFactory
            # Add test compatibility aliases
            globals()["BaseCollection"] = ModelBaseCollection
            globals()["BaseFactory"] = ModelBaseFactory
            return globals()[name]
        msg = f"module {__name__!r} has no attribute {name!r}"
        # error-ok: AttributeError is standard Python pattern for __getattr__
        raise AttributeError(msg)


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
    # Abstract base classes
    "ModelBaseCollection",
    "ModelBaseFactory",
    # Test compatibility aliases
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
    # ONEX-compatible type validation guards
    "is_primitive_value",
    # Type guards
    "is_serializable",
    "is_validatable",
    "validate_context_value",
    "validate_primitive_value",
]
