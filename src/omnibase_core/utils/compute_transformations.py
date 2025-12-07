"""
Pure transformation functions for contract-driven NodeCompute v1.0.

This module provides a collection of pure transformation functions for processing
data in compute pipelines. Each function follows the pattern (data, config) -> result
with no side effects and deterministic output.

Thread Safety:
    All functions in this module are pure and stateless - safe for concurrent use.
    Each function operates only on its input parameters and produces a new result
    without modifying any shared state.

Supported Transformations:
    - IDENTITY: Pass-through transformation (no change)
    - REGEX: Regular expression substitution
    - CASE_CONVERSION: Uppercase, lowercase, title case
    - TRIM: Whitespace trimming (left, right, both)
    - NORMALIZE_UNICODE: Unicode normalization (NFC, NFD, NFKC, NFKD)
    - JSON_PATH: Simple dot-notation path extraction

Example:
    >>> from omnibase_core.utils.compute_transformations import execute_transformation
    >>> from omnibase_core.enums import EnumTransformationType
    >>> from omnibase_core.models.transformations import ModelTransformCaseConfig
    >>> from omnibase_core.enums import EnumCaseMode
    >>>
    >>> config = ModelTransformCaseConfig(mode=EnumCaseMode.UPPER)
    >>> result = execute_transformation("hello", EnumTransformationType.CASE_CONVERSION, config)
    >>> # result == "HELLO"

See Also:
    - omnibase_core.utils.compute_executor: Pipeline execution
    - omnibase_core.models.transformations: Transformation config models
    - docs/guides/node-building/03_COMPUTE_NODE_TUTORIAL.md: Compute node tutorial
"""

import re
import unicodedata
from collections.abc import Callable
from typing import Any, Union

# Type alias for JSON-compatible data structures
# Used for documenting expected data shapes in transformation functions
JsonValue = Union[str, int, float, bool, None]
JsonType = Union[dict[str, "JsonType"], list["JsonType"], JsonValue]

# Type alias for transformation handler functions
# Handlers have varying signatures (some take config, some don't), so we use Callable[..., Any]
TransformationHandler = Callable[..., Any]

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


def transform_identity(
    data: Any,  # Any: intentionally polymorphic - accepts any input type unchanged
) -> Any:  # Any: output type mirrors input type
    """
    Identity transformation - returns data unchanged.

    This is a no-op transformation that passes data through without modification.
    Useful as a placeholder or for testing pipeline mechanics.

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.

    Args:
        data: Any input data to pass through unchanged.

    Returns:
        The input data, unchanged.

    Example:
        >>> result = transform_identity({"key": "value"})
        >>> result == {"key": "value"}
        True
    """
    return data


def transform_regex(data: str, config: ModelTransformRegexConfig) -> str:
    """
    Apply regex substitution to string data.

    Performs a regular expression search-and-replace operation on the input string
    using the pattern and replacement defined in the configuration.

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.

    Args:
        data: The input string to transform.
        config: Configuration containing:
            - pattern: The regex pattern to match
            - replacement: The replacement string
            - flags: Optional list of regex flags (IGNORECASE, MULTILINE, DOTALL)

    Returns:
        The transformed string with all pattern matches replaced.

    Raises:
        ModelOnexError: If data is not a string (VALIDATION_ERROR) or
            if the regex pattern is invalid (OPERATION_FAILED).

    Example:
        >>> from omnibase_core.models.transformations import ModelTransformRegexConfig
        >>> config = ModelTransformRegexConfig(pattern=r"\\d+", replacement="NUM")
        >>> transform_regex("Order 123 has 456 items", config)
        'Order NUM has NUM items'
    """
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
    """
    Apply case transformation to string data.

    Converts the input string to the specified case format.

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.

    Args:
        data: The input string to transform.
        config: Configuration containing the target case mode:
            - UPPER: Convert to uppercase
            - LOWER: Convert to lowercase
            - TITLE: Convert to title case

    Returns:
        The string converted to the specified case.

    Raises:
        ModelOnexError: If data is not a string (VALIDATION_ERROR) or
            if an unknown case mode is specified (OPERATION_FAILED).

    Example:
        >>> from omnibase_core.models.transformations import ModelTransformCaseConfig
        >>> from omnibase_core.enums import EnumCaseMode
        >>> config = ModelTransformCaseConfig(mode=EnumCaseMode.UPPER)
        >>> transform_case("hello world", config)
        'HELLO WORLD'
    """
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
    """
    Trim whitespace from string data.

    Removes leading and/or trailing whitespace from the input string
    based on the specified trim mode.

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.

    Args:
        data: The input string to trim.
        config: Configuration containing the trim mode:
            - BOTH: Remove whitespace from both ends
            - LEFT: Remove leading whitespace only
            - RIGHT: Remove trailing whitespace only

    Returns:
        The trimmed string.

    Raises:
        ModelOnexError: If data is not a string (VALIDATION_ERROR) or
            if an unknown trim mode is specified (OPERATION_FAILED).

    Example:
        >>> from omnibase_core.models.transformations import ModelTransformTrimConfig
        >>> from omnibase_core.enums import EnumTrimMode
        >>> config = ModelTransformTrimConfig(mode=EnumTrimMode.BOTH)
        >>> transform_trim("  hello world  ", config)
        'hello world'
    """
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
    """
    Normalize unicode in string data.

    Applies Unicode normalization to ensure consistent character representation.
    This is important for comparing strings that may contain characters with
    multiple valid Unicode representations.

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.

    Args:
        data: The input string to normalize.
        config: Configuration containing the normalization form:
            - NFC: Canonical Decomposition, followed by Canonical Composition
            - NFD: Canonical Decomposition
            - NFKC: Compatibility Decomposition, followed by Canonical Composition
            - NFKD: Compatibility Decomposition

    Returns:
        The Unicode-normalized string.

    Raises:
        ModelOnexError: If data is not a string (VALIDATION_ERROR).

    Example:
        >>> from omnibase_core.models.transformations import ModelTransformUnicodeConfig
        >>> from omnibase_core.enums import EnumUnicodeForm
        >>> config = ModelTransformUnicodeConfig(form=EnumUnicodeForm.NFC)
        >>> # Normalize a string with combining characters
        >>> transform_unicode("cafe\\u0301", config)  # e + combining acute
        'cafe'  # Single precomposed character
    """
    if not isinstance(data, str):
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"NORMALIZE_UNICODE transformation requires string input, got {type(data).__name__}",
        )

    return unicodedata.normalize(config.form.value, data)


def transform_json_path(
    data: Any,  # Any: accepts dict, Pydantic models, or other objects with attributes
    config: ModelTransformJsonPathConfig,
) -> Any:  # Any: return type depends on the path being resolved
    """
    Extract data using simple JSONPath-like path notation.

    Navigates into nested data structures using dot-notation paths to extract
    specific values. Supports both dictionary access and object attribute access.

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.

    v1.0 Limitations:
        This implementation supports only simple dot-notation paths. Array indexing,
        wildcards, filters, and other advanced JSONPath features are deferred to v1.2.

    Args:
        data: The input data structure to navigate (dict, object, or nested structure).
        config: Configuration containing the path to extract:
            - "field": Direct field access
            - "field.subfield": Nested field access
            - "$" or "$.field": JSONPath-style notation ($ is optional)

    Returns:
        The value found at the specified path.

    Raises:
        ModelOnexError: If the path cannot be resolved (key missing, attribute not found)
            or if attempting to access private attributes (those starting with "_").

    Example:
        >>> from omnibase_core.models.transformations import ModelTransformJsonPathConfig
        >>> data = {"user": {"name": "Alice", "profile": {"age": 30}}}
        >>> config = ModelTransformJsonPathConfig(path="user.profile.age")
        >>> transform_json_path(data, config)
        30
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
        # Block private attribute access for security
        elif part.startswith("_"):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Cannot access private attribute: '{part}'",
            )
        elif hasattr(current, part):
            current = getattr(current, part)
        else:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"Path '{config.path}' not found: cannot access '{part}' on {type(current).__name__}",
            )

    return current


# Transformation registry mapping type to handler
# TransformationHandler used because handlers have varying signatures
TRANSFORMATION_REGISTRY: dict[EnumTransformationType, TransformationHandler] = {
    EnumTransformationType.IDENTITY: transform_identity,
    EnumTransformationType.REGEX: transform_regex,
    EnumTransformationType.CASE_CONVERSION: transform_case,
    EnumTransformationType.TRIM: transform_trim,
    EnumTransformationType.NORMALIZE_UNICODE: transform_unicode,
    EnumTransformationType.JSON_PATH: transform_json_path,
}


def execute_transformation(
    data: Any,  # Any: input varies based on transformation_type (str for regex/case, any for json_path)
    transformation_type: EnumTransformationType,
    config: ModelTransformationConfig | None,
) -> Any:  # Any: output type depends on transformation_type
    """
    Execute a single transformation on input data.

    This is the main entry point for executing transformations. It dispatches
    to the appropriate transformation function based on the transformation type.

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.

    Args:
        data: Input data to transform. The expected type depends on the transformation:
            - IDENTITY: Any type (passed through unchanged)
            - REGEX, CASE_CONVERSION, TRIM, NORMALIZE_UNICODE: str
            - JSON_PATH: dict, object, or nested structure
        transformation_type: The type of transformation to apply, from EnumTransformationType.
        config: Configuration for the transformation. Required for all types except IDENTITY.
            Must match the expected config type for the transformation.

    Returns:
        The transformed data. Return type depends on the transformation type.

    Raises:
        ModelOnexError: If transformation fails due to:
            - VALIDATION_ERROR: Wrong input type or missing required config
            - OPERATION_FAILED: Unknown transformation type or transformation failure

    Example:
        >>> from omnibase_core.enums import EnumTransformationType, EnumCaseMode
        >>> from omnibase_core.models.transformations import ModelTransformCaseConfig
        >>>
        >>> config = ModelTransformCaseConfig(mode=EnumCaseMode.UPPER)
        >>> result = execute_transformation(
        ...     "hello world",
        ...     EnumTransformationType.CASE_CONVERSION,
        ...     config
        ... )
        >>> result
        'HELLO WORLD'
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
    # Type aliases
    "JsonValue",
    "JsonType",
    "TransformationHandler",
    # Transformation functions
    "transform_identity",
    "transform_regex",
    "transform_case",
    "transform_trim",
    "transform_unicode",
    "transform_json_path",
    "execute_transformation",
    "TRANSFORMATION_REGISTRY",
]
