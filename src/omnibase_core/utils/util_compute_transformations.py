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
    >>> from omnibase_core.utils.util_compute_transformations import execute_transformation
    >>> from omnibase_core.enums import EnumTransformationType
    >>> from omnibase_core.models.transformations import ModelTransformCaseConfig
    >>> from omnibase_core.enums import EnumCaseMode
    >>>
    >>> config = ModelTransformCaseConfig(mode=EnumCaseMode.UPPER)
    >>> result = execute_transformation("hello", EnumTransformationType.CASE_CONVERSION, config)
    >>> # result == "HELLO"

See Also:
    - omnibase_core.utils.util_compute_executor: Pipeline execution
    - omnibase_core.models.transformations: Transformation config models
    - docs/guides/node-building/03_COMPUTE_NODE_TUTORIAL.md: Compute node tutorial
"""

import re
import unicodedata
from collections.abc import Callable
from typing import Literal, cast

from omnibase_core.enums.enum_case_mode import EnumCaseMode
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_regex_flag import EnumRegexFlag
from omnibase_core.enums.enum_transformation_type import EnumTransformationType
from omnibase_core.enums.enum_trim_mode import EnumTrimMode
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
from omnibase_core.models.transformations.model_types import ModelTransformationConfig


def _validate_string_input(value: object, transform_name: str) -> str:
    """
    Validate that input is a string type for string transformation functions.

    This is a DRY helper function used by string transformations (REGEX,
    CASE_CONVERSION, TRIM, NORMALIZE_UNICODE) to validate input type
    before processing.

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.

    Args:
        value: The input value to validate.
        transform_name: Name of the transformation for error messaging
            (e.g., "REGEX", "CASE_CONVERSION").

    Returns:
        The input value unchanged, typed as str.

    Raises:
        ModelOnexError: If value is not a string (VALIDATION_ERROR).

    Example:
        >>> data = _validate_string_input("hello", "CASE_CONVERSION")
        >>> data
        'hello'
        >>> _validate_string_input(123, "CASE_CONVERSION")  # raises ModelOnexError
    """
    if not isinstance(value, str):
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"{transform_name} transformation requires string input, got {type(value).__name__}",
            context={
                "transform_type": transform_name,
                "input_type": type(value).__name__,
                "expected_type": "str",
            },
        )
    return value


# TODO(OMN-TBD): Create TransformationError for more specific error handling.  [NEEDS TICKET]
# Currently uses ModelOnexError which is generic. A dedicated TransformationError would:
# - Enable more precise error handling in pipeline execution
# - Allow callers to distinguish transformation failures from other error types
# - Support structured transformation-specific error context (e.g., step_name, input_type)
# See: docs/architecture/NODECOMPUTE_VERSIONING_ROADMAP.md


def transform_identity[T](
    data: T,
    config: (
        ModelTransformationConfig | None
    ),  # Aligned with other handlers for uniform registry usage
) -> T:
    """
    Identity transformation - returns data unchanged.

    This is a no-op transformation that passes data through without modification.
    Useful as a placeholder or for testing pipeline mechanics.

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.

    Note:
        The signature uses `config: ModelTransformationConfig | None` to align with
        other transformation handler functions which all take `(data, config)`. This
        maintains uniform `handler(data, config)` call pattern in the registry and
        enables safer type checking when handlers are stored in the registry.

        The config parameter should be None for IDENTITY transformation - no
        configuration is required or used. This is enforced at the contract level by
        ModelComputePipelineStep validation, which rejects any IDENTITY step that has
        transformation_config set.

    Args:
        data: Any input data to pass through unchanged.
        config: Should be None. IDENTITY transformation requires no configuration.
            This parameter exists for uniform registry handler signature,
            allowing the registry to call all handlers with `handler(data, config)`.
            The type allows ModelTransformationConfig for registry compatibility,
            but IDENTITY steps should always pass None.

    Returns:
        The input data, unchanged.

    Example:
        >>> result = transform_identity({"key": "value"}, None)
        >>> result == {"key": "value"}
        True
    """
    # config parameter is intentionally unused - exists for registry uniformity
    del config  # Explicitly mark as unused to satisfy linters
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
    _validate_string_input(data, "REGEX")

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
            context={
                "transform_type": "REGEX",
                "pattern": config.pattern,
                "replacement": config.replacement,
                "regex_error": str(e),
            },
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
    _validate_string_input(data, "CASE_CONVERSION")

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
            context={
                "transform_type": "CASE_CONVERSION",
                "mode": str(config.mode),
            },
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
    _validate_string_input(data, "TRIM")

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
            context={
                "transform_type": "TRIM",
                "mode": str(config.mode),
            },
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
        'café'  # Single precomposed character (e with acute, U+00E9)
    """
    _validate_string_input(data, "NORMALIZE_UNICODE")

    form = cast(Literal["NFC", "NFD", "NFKC", "NFKD"], config.form.value)
    return unicodedata.normalize(form, data)


# TODO(OMN-TBD): Consider using shared utility omnibase_core.utils.compute_path_resolver  [NEEDS TICKET]
# The shared utility has resolve_path() which provides equivalent functionality.
# This function could be replaced with a thin wrapper that extracts config.path:
#   from omnibase_core.utils.util_compute_path_resolver import resolve_path
#   def transform_json_path(data, config): return resolve_path(config.path, data)
# See: compute_path_resolver.py for unified path resolution logic with EBNF grammar docs
def transform_json_path(
    data: dict[str, object] | object,
    config: ModelTransformJsonPathConfig,
) -> object:
    """
    Extract data using simple JSONPath-like path notation.

    Navigates into nested data structures using dot-notation paths to extract
    specific values. Supports both dictionary access and object attribute access.

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.

    v1.0 Limitations:
        This implementation supports only simple dot-notation paths. Array indexing,
        wildcards, filters, and other advanced JSONPath features are deferred to v1.2.

    Private Attribute Security:
        For security reasons, private attributes (those starting with "_") are
        blocked from path traversal when accessing object attributes. This prevents
        exposure of internal implementation details through path expressions.
        Dictionary keys starting with "_" ARE accessible since dictionaries
        represent user data, not internal state.

    Args:
        data: The input data structure to navigate (dict, object, or nested structure).
        config: Configuration containing the path to extract:
            - "$": Root-level access (returns entire data)
            - "$.field": Direct field access
            - "$.field.subfield": Nested field access
            Note: Path must start with "$" (validated by ModelTransformJsonPathConfig).

    Returns:
        The value found at the specified path.

    Raises:
        ModelOnexError: If the path cannot be resolved (key missing, attribute not found)
            or if attempting to access private attributes (those starting with "_")
            on objects (not dictionaries).

    Example:
        >>> from omnibase_core.models.transformations import ModelTransformJsonPathConfig
        >>> data = {"user": {"name": "Alice", "profile": {"age": 30}}}
        >>> config = ModelTransformJsonPathConfig(path="$.user.profile.age")
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
                    context={
                        "transform_type": "JSON_PATH",
                        "path": config.path,
                        "missing_key": part,
                        "available_keys": list(current.keys()) if current else [],
                    },
                )
            current = current[part]
        # Block private attribute access for security
        elif part.startswith("_"):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Cannot access private attribute: '{part}'",
                context={
                    "transform_type": "JSON_PATH",
                    "path": config.path,
                    "private_attribute": part,
                },
            )
        elif hasattr(current, part):
            current = getattr(current, part)
        else:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"Path '{config.path}' not found: cannot access '{part}' on {type(current).__name__}",
                context={
                    "transform_type": "JSON_PATH",
                    "path": config.path,
                    "missing_attribute": part,
                    "object_type": type(current).__name__,
                },
            )

    return current


# Transformation registry mapping type to handler
# Handlers take (data, config) and return transformed data
# Using Callable[..., object] because handlers have heterogeneous signatures
# that share the (data, config) pattern but with specific types per transformation.
# The ellipsis indicates unspecified argument types (distinct from Any).
TRANSFORMATION_REGISTRY: dict[EnumTransformationType, Callable[..., object]] = {
    EnumTransformationType.IDENTITY: transform_identity,
    EnumTransformationType.REGEX: transform_regex,
    EnumTransformationType.CASE_CONVERSION: transform_case,
    EnumTransformationType.TRIM: transform_trim,
    EnumTransformationType.NORMALIZE_UNICODE: transform_unicode,
    EnumTransformationType.JSON_PATH: transform_json_path,
}


def execute_transformation(
    data: str | dict[str, object] | object,
    transformation_type: EnumTransformationType,
    config: ModelTransformationConfig | None,
) -> str | dict[str, object] | object:
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
    handler = TRANSFORMATION_REGISTRY.get(transformation_type)
    if handler is None:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.OPERATION_FAILED,
            message=f"Unknown transformation type: {transformation_type}",
            context={
                "transform_type": str(transformation_type),
                "available_types": [t.value for t in TRANSFORMATION_REGISTRY],
            },
        )

    # Validate config requirements:
    # - IDENTITY: config must be None (no configuration needed)
    # - All others: config is required
    # Contract-level validation (ModelComputePipelineStep) ensures IDENTITY steps
    # never have transformation_config set, so config will be None here.
    if transformation_type != EnumTransformationType.IDENTITY and config is None:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Configuration required for {transformation_type} transformation",
            context={
                "transform_type": (
                    transformation_type.value
                    if hasattr(transformation_type, "value")
                    else str(transformation_type)
                ),
                "input_type": type(data).__name__,
            },
        )

    # Uniform handler call - all handlers take (data, config)
    # For IDENTITY, config is None; for others, config is the specific config type
    return handler(data, config)


__all__ = [
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
