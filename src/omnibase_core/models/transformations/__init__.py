# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Transformation models for contract-driven NodeCompute v1.0.

This package provides the configuration models for all transformation types
supported in the v1.0 Contract-Driven NodeCompute specification.

Transformation Config Models:
    - ModelTransformRegexConfig: Configuration for REGEX transformations
    - ModelTransformCaseConfig: Configuration for CASE_CONVERSION transformations
    - ModelTransformTrimConfig: Configuration for TRIM transformations
    - ModelTransformUnicodeConfig: Configuration for NORMALIZE_UNICODE transformations
    - ModelTransformJsonPathConfig: Configuration for JSON_PATH transformations

Step Config Models:
    - ModelMappingConfig: Configuration for MAPPING step type
    - ModelValidationStepConfig: Configuration for VALIDATION step type

Union Types:
    - ModelTransformationConfig: Discriminated union of all transformation configs
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model_mapping_config import ModelMappingConfig
    from .model_transform_case_config import ModelTransformCaseConfig
    from .model_transform_json_path_config import ModelTransformJsonPathConfig
    from .model_transform_regex_config import ModelTransformRegexConfig
    from .model_transform_trim_config import ModelTransformTrimConfig
    from .model_transform_unicode_config import ModelTransformUnicodeConfig
    from .model_types import ModelTransformationConfig
    from .model_validation_step_config import ModelValidationStepConfig

__all__ = [
    "ModelTransformRegexConfig",
    "ModelTransformCaseConfig",
    "ModelTransformTrimConfig",
    "ModelTransformUnicodeConfig",
    "ModelTransformJsonPathConfig",
    "ModelMappingConfig",
    "ModelValidationStepConfig",
    "ModelTransformationConfig",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelMappingConfig": (
        "omnibase_core.models.transformations.model_mapping_config",
        "ModelMappingConfig",
    ),
    "ModelTransformCaseConfig": (
        "omnibase_core.models.transformations.model_transform_case_config",
        "ModelTransformCaseConfig",
    ),
    "ModelTransformJsonPathConfig": (
        "omnibase_core.models.transformations.model_transform_json_path_config",
        "ModelTransformJsonPathConfig",
    ),
    "ModelTransformRegexConfig": (
        "omnibase_core.models.transformations.model_transform_regex_config",
        "ModelTransformRegexConfig",
    ),
    "ModelTransformTrimConfig": (
        "omnibase_core.models.transformations.model_transform_trim_config",
        "ModelTransformTrimConfig",
    ),
    "ModelTransformUnicodeConfig": (
        "omnibase_core.models.transformations.model_transform_unicode_config",
        "ModelTransformUnicodeConfig",
    ),
    "ModelTransformationConfig": (
        "omnibase_core.models.transformations.model_types",
        "ModelTransformationConfig",
    ),
    "ModelValidationStepConfig": (
        "omnibase_core.models.transformations.model_validation_step_config",
        "ModelValidationStepConfig",
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
