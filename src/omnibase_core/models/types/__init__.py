# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ONEX Type System - Centralized type definitions.

A centralized type system to eliminate untyped ``Any``
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

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "JsonSerializable": (
        "omnibase_core.models.types.model_json_serializable",
        "JsonSerializable",
    ),
    "CliValue": ("omnibase_core.models.types.model_onex_common_types", "CliValue"),
    "ConfigValue": (
        "omnibase_core.models.types.model_onex_common_types",
        "ConfigValue",
    ),
    "EnvValue": ("omnibase_core.models.types.model_onex_common_types", "EnvValue"),
    "MetadataValue": (
        "omnibase_core.models.types.model_onex_common_types",
        "MetadataValue",
    ),
    "ParameterValue": (
        "omnibase_core.models.types.model_onex_common_types",
        "ParameterValue",
    ),
    "PropertyValue": (
        "omnibase_core.models.types.model_onex_common_types",
        "PropertyValue",
    ),
    "ResultValue": (
        "omnibase_core.models.types.model_onex_common_types",
        "ResultValue",
    ),
    "ValidationValue": (
        "omnibase_core.models.types.model_onex_common_types",
        "ValidationValue",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        # A submodule that the old eager __init__ loaded as a side effect
        # stays reachable as ``package.submodule``: import it on first access.
        if (
            name.isidentifier()
            and not name.startswith("__")
            and importlib.util.find_spec(f"{__name__}.{name}") is not None
        ):
            return importlib.import_module(f"{__name__}.{name}")
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
