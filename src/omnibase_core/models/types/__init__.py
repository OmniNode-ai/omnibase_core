"""
ONEX Type System - Centralized type definitions.

This module provides a centralized type system to eliminate untyped ``Any``
usage across the codebase. All type aliases follow a consistent naming
convention and are designed for specific domains within the ONEX framework.

Type Categories:
    Serialization Types:
        JsonSerializable: Recursive type for JSON-compatible values following
            RFC 8259 specification.

    Value Types:
        CliValue: Command-line argument values (strings, numbers, booleans, lists).
        ConfigValue: Configuration file values with hierarchical structure support.
        EnvValue: Environment variable values (strings with optional parsing).
        MetadataValue: Metadata dictionary values for annotations and tracking.
        ParameterValue: Function/method parameter values with type constraints.
        PropertyValue: Object property values for dynamic attribute access.
        ResultValue: Operation result values with success/failure semantics.
        ValidationValue: Validation rule values for schema enforcement.

Design Principles:
    1. Domain-Specific Types: Each type is designed for a specific use case
       rather than being a generic catch-all.
    2. Type Safety: All types are fully compatible with mypy strict mode.
    3. Serialization-Ready: Types are designed to be JSON-serializable where
       appropriate.
    4. Self-Documenting: Type names clearly indicate their intended usage.

Example:
    >>> from omnibase_core.models.types import JsonSerializable, ConfigValue
    >>>
    >>> # Type-safe configuration value
    >>> config: ConfigValue = {"host": "localhost", "port": 8080}
    >>>
    >>> # JSON-serializable data for API responses
    >>> response: JsonSerializable = {"status": "ok", "data": [1, 2, 3]}

See Also:
    - omnibase_core.models.types.model_json_serializable: PEP 695 recursive type
    - omnibase_core.models.types.model_onex_common_types: Common type definitions
"""

from .model_json_serializable import JsonSerializable
from .model_onex_common_types import (
    CliValue,
    ConfigValue,
    EnvValue,
    MetadataValue,
    ParameterValue,
    PropertyValue,
    ResultValue,
    ValidationValue,
)

# JsonSerializable is now imported from model_json_serializable.py
# which uses PEP 695 recursive type statements for proper type safety

__all__ = [
    "CliValue",
    "ConfigValue",
    "EnvValue",
    "JsonSerializable",
    "MetadataValue",
    "ParameterValue",
    "PropertyValue",
    "ResultValue",
    "ValidationValue",
]
