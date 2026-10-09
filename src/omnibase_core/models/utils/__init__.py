# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Utility models for YAML processing, contract validation, and data conversion.

Utility models that support core ONEX operations including
YAML serialization, contract validation, and field conversion between different
representations.

Key Components:
    ModelYamlDumpOptions:
        Type-safe configuration for YAML serialization with options for
        formatting, indentation, and encoding.

    ModelYamlOption:
        Individual YAML configuration option with type and default value.

    ModelYamlValue:
        Typed wrapper for YAML values with validation and conversion support.

    ModelFieldConverterRegistry:
        Registry for field converters that transform data between different
        representations (e.g., model to dict, dict to YAML).

    FieldConverter:
        Protocol for implementing custom field conversion logic.

    ModelSubcontractConstraintValidator:
        Validator for ensuring subcontract constraints are satisfied during
        contract validation.

Usage Notes:
    - ModelValidationRulesConverter is intentionally excluded from this module
      to avoid circular imports. Import it directly when needed:
      ``from omnibase_core.models.utils.model_validation_rules_converter import ModelValidationRulesConverter``

Example:
    >>> from omnibase_core.models.utils import ModelYamlDumpOptions
    >>>
    >>> # Configure YAML output formatting
    >>> yaml_options = ModelYamlDumpOptions(
    ...     indent=4,
    ...     sort_keys=True,
    ...     allow_unicode=True,
    ... )

See Also:
    - omnibase_core.utils.yaml_utils: YAML utility functions
    - omnibase_core.models.contracts: Contract model definitions
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model_field_converter import FieldConverter, ModelFieldConverterRegistry
    from .model_subcontract_constraint_validator import (
        ModelSubcontractConstraintValidator,
    )
    from .model_yaml_dump_options import ModelYamlDumpOptions
    from .model_yaml_option import ModelYamlOption
    from .model_yaml_value import ModelYamlValue

# ModelValidationRulesConverter not imported here to avoid circular import
# Import it directly where needed: from omnibase_core.models.utils.model_validation_rules_converter import ModelValidationRulesConverter

__all__ = [
    "FieldConverter",
    "ModelFieldConverterRegistry",
    "ModelSubcontractConstraintValidator",
    "ModelYamlDumpOptions",
    "ModelYamlOption",
    "ModelYamlValue",
    # "ModelValidationRulesConverter",  # Excluded to break circular import
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "FieldConverter": (
        "omnibase_core.models.utils.model_field_converter",
        "FieldConverter",
    ),
    "ModelFieldConverterRegistry": (
        "omnibase_core.models.utils.model_field_converter",
        "ModelFieldConverterRegistry",
    ),
    "ModelSubcontractConstraintValidator": (
        "omnibase_core.models.utils.model_subcontract_constraint_validator",
        "ModelSubcontractConstraintValidator",
    ),
    "ModelYamlDumpOptions": (
        "omnibase_core.models.utils.model_yaml_dump_options",
        "ModelYamlDumpOptions",
    ),
    "ModelYamlOption": (
        "omnibase_core.models.utils.model_yaml_option",
        "ModelYamlOption",
    ),
    "ModelYamlValue": ("omnibase_core.models.utils.model_yaml_value", "ModelYamlValue"),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
