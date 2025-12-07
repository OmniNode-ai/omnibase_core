"""
Pure transformation functions for contract-driven NodeCompute v1.0.

All functions are pure: (data, config) → result
No side effects, deterministic output.
"""

import re
import unicodedata
from typing import Any

from omnibase_core.enums.enum_case_mode import EnumCaseMode
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_regex_flag import EnumRegexFlag
from omnibase_core.enums.enum_transformation_type import EnumTransformationType
from omnibase_core.enums.enum_trim_mode import EnumTrimMode
from omnibase_core.enums.enum_unicode_form import EnumUnicodeForm
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.transformations.model_transform_case_config import (
    ModelTransformCaseConfig,
)
from omnibase_core.models.transformations.model_transform_json_path_config import (
    ModelTransformJsonPathConfig,
)
from omnibase_core.models.transformations.model_transform_regex_config import (
    ModelTransformRegexConfig,
)
from omnibase_core.models.transformations.model_transform_trim_config import (
    ModelTransformTrimConfig,
)
from omnibase_core.models.transformations.model_transform_unicode_config import (
    ModelTransformUnicodeConfig,
)
from omnibase_core.models.transformations.types import ModelTransformationConfig


def transform_identity(data: Any) -> Any:
    """Identity transformation - returns data unchanged."""
    return data


def transform_regex(data: str, config: ModelTransformRegexConfig) -> str:
    """Apply regex substitution to string data."""
    if not isinstance(data, str):
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"REGEX transformation requires string input, got {type(data).__name__}",
        )

    # Convert EnumRegexFlag to Python re flags
    flags = 0
    for flag in config.flags:
        if flag == EnumRegexFlag.IGNORECASE:
            flags |= re.IGNORECASE
        elif flag == EnumRegexFlag.MULTILINE:
            flags |= re.MULTILINE
        elif flag == EnumRegexFlag.DOTALL:
            flags |= re.DOTALL

    try:
        return re.sub(config.pattern, config.replacement, data, flags=flags)
    except re.error as e:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.OPERATION_FAILED,
            message=f"Invalid regex pattern: {e}",
        ) from e


def transform_case(data: str, config: ModelTransformCaseConfig) -> str:
    """Apply case transformation to string data."""
    if not isinstance(data, str):
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"CASE_CONVERSION transformation requires string input, got {type(data).__name__}",
        )

    if config.mode == EnumCaseMode.UPPER:
        return data.upper()
    elif config.mode == EnumCaseMode.LOWER:
        return data.lower()
    elif config.mode == EnumCaseMode.TITLE:
        return data.title()
    else:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.OPERATION_FAILED,
            message=f"Unknown case mode: {config.mode}",
        )


def transform_trim(data: str, config: ModelTransformTrimConfig) -> str:
    """Trim whitespace from string data."""
    if not isinstance(data, str):
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"TRIM transformation requires string input, got {type(data).__name__}",
        )

    if config.mode == EnumTrimMode.BOTH:
        return data.strip()
    elif config.mode == EnumTrimMode.LEFT:
        return data.lstrip()
    elif config.mode == EnumTrimMode.RIGHT:
        return data.rstrip()
    else:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.OPERATION_FAILED,
            message=f"Unknown trim mode: {config.mode}",
        )


def transform_unicode(data: str, config: ModelTransformUnicodeConfig) -> str:
    """Normalize unicode in string data."""
    if not isinstance(data, str):
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"NORMALIZE_UNICODE transformation requires string input, got {type(data).__name__}",
        )

    return unicodedata.normalize(config.form.value, data)


def transform_json_path(data: Any, config: ModelTransformJsonPathConfig) -> Any:
    """Extract data using simple JSONPath-like path.

    v1.0 supports only simple dot-notation paths like:
    - "field" - direct field access
    - "field.subfield" - nested field access

    NOTE: This is NOT full JSONPath. Array indexing, wildcards, and filters
    are deferred to v1.2.
    """
    path = config.path

    # Handle root-level access
    if not path or path == "$":
        return data

    # Remove leading $ if present
    if path.startswith("$."):
        path = path[2:]
    elif path.startswith("$"):
        path = path[1:]

    # Split path and traverse
    parts = path.split(".")
    current = data

    for part in parts:
        if not part:
            continue

        if isinstance(current, dict):
            if part not in current:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.OPERATION_FAILED,
                    message=f"Path '{config.path}' not found: key '{part}' missing",
                )
            current = current[part]
        elif hasattr(current, part):
            current = getattr(current, part)
        else:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"Path '{config.path}' not found: cannot access '{part}' on {type(current).__name__}",
            )

    return current


# Transformation registry mapping type to handler
TRANSFORMATION_REGISTRY: dict[EnumTransformationType, Any] = {
    EnumTransformationType.IDENTITY: transform_identity,
    EnumTransformationType.REGEX: transform_regex,
    EnumTransformationType.CASE_CONVERSION: transform_case,
    EnumTransformationType.TRIM: transform_trim,
    EnumTransformationType.NORMALIZE_UNICODE: transform_unicode,
    EnumTransformationType.JSON_PATH: transform_json_path,
}


def execute_transformation(
    data: Any,
    transformation_type: EnumTransformationType,
    config: ModelTransformationConfig | None,
) -> Any:
    """
    Execute a single transformation.

    Pure function: (data, type, config) → result

    Args:
        data: Input data to transform
        transformation_type: Type of transformation to apply
        config: Configuration for the transformation (None for IDENTITY)

    Returns:
        Transformed data

    Raises:
        ModelOnexError: On transformation failure
    """
    if transformation_type == EnumTransformationType.IDENTITY:
        return transform_identity(data)

    handler = TRANSFORMATION_REGISTRY.get(transformation_type)
    if handler is None:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.OPERATION_FAILED,
            message=f"Unknown transformation type: {transformation_type}",
        )

    if config is None:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Configuration required for {transformation_type} transformation",
        )

    return handler(data, config)


__all__ = [
    "transform_identity",
    "transform_regex",
    "transform_case",
    "transform_trim",
    "transform_unicode",
    "transform_json_path",
    "execute_transformation",
    "TRANSFORMATION_REGISTRY",
]
