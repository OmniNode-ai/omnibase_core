"""
Shared path resolution utilities for contract-driven NodeCompute v1.0+.

This module provides unified path resolution logic for navigating through nested data
structures in compute pipelines. It consolidates the path traversal patterns used by
both the pipeline executor (resolve_mapping_path) and transformations (transform_json_path).

Thread Safety:
    All functions in this module are pure and stateless - safe for concurrent use.
    Each function operates only on its input parameters and produces a new result
    without modifying any shared state.

Path Expression Grammar (EBNF):
    This grammar describes the path expression syntax supported by the resolver:

    ```ebnf
    (* Full path expression *)
    path_expr     = root_marker, path_body ;

    (* Root markers *)
    root_marker   = "$" | "" ;  (* "$" is optional for simple paths *)

    (* Path body after root *)
    path_body     = "" | (".", segment, { ".", segment }) ;

    (* Path segments *)
    segment       = identifier ;  (* No array indexing in v1.0 *)

    (* Identifiers *)
    identifier    = letter, { letter | digit | "_" } ;
    letter        = "a" | ... | "z" | "A" | ... | "Z" ;
    digit         = "0" | ... | "9" ;

    (* Extended grammar for pipeline paths *)
    pipeline_path = "$", ("input" | "steps"), [".", path_tail] ;
    path_tail     = segment, { ".", segment } ;
    ```

Path Expression Syntax (v1.0):
    The resolver supports two path contexts with different prefixes:

    **Simple paths** (for JSON_PATH transformation):
        - `$` or empty: Returns root object
        - `$.field` or `field`: Direct field access
        - `$.field.subfield` or `field.subfield`: Nested access (unlimited depth)

    **Pipeline paths** (for mapping step resolution):
        - `$.input` or `$input`: Returns full pipeline input object
        - `$.input.<field>`: Direct child field of input
        - `$.input.<field>.<subfield>`: Nested field access (unlimited depth)
        - `$.steps.<step_name>`: Returns step's output (shorthand form)
        - `$.steps.<step_name>.output`: Returns step's output (explicit form)

Path Alias Conventions:
    - `$input` is equivalent to `$.input` (convenience alias)
    - `$.steps.<name>` is equivalent to `$.steps.<name>.output` (shorthand)

    The shorthand `$.steps.<name>` form is preferred for readability. The explicit
    `.output` suffix is supported for clarity and forward compatibility (v1.1+ may
    expose additional step result fields like `.metadata` or `.duration_ms`).

Private Attribute Security:
    For security reasons, private attributes (those starting with "_") are blocked
    from path traversal when accessing object attributes. This prevents exposure of
    internal implementation details through path expressions.

    Note: Dictionary keys starting with "_" ARE accessible since dictionaries
    represent user data, not internal object state.

v1.0 Limitations:
    - No array indexing: `$.items[0]` not supported
    - No wildcards: `$.items[*]` not supported
    - No filters: `$.items[?(@.active)]` not supported
    - Step paths only support `.output` access (no `.metadata`, `.duration_ms`)

    These features are planned for v1.2. See: docs/architecture/NODECOMPUTE_VERSIONING_ROADMAP.md

Example:
    >>> from omnibase_core.utils.util_compute_path_resolver import resolve_path
    >>> data = {"user": {"name": "Alice", "profile": {"age": 30}}}
    >>> resolve_path("user.profile.age", data)
    30
    >>> resolve_path("$.user.name", data)
    'Alice'

See Also:
    - omnibase_core.utils.util_compute_executor: Pipeline execution (uses resolve_pipeline_path)
    - omnibase_core.utils.compute_transformations: JSON_PATH transformation (uses resolve_path)
    - docs/guides/node-building/03_COMPUTE_NODE_TUTORIAL.md: Compute node tutorial
"""

from collections.abc import Mapping

from pydantic import BaseModel

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.typed_dict_path_resolution_context import (
    TypedDictPathResolutionContext,
)

# Type alias for data that can be traversed during path resolution
# Includes dictionaries, Pydantic models, and arbitrary objects with attributes
TraversableData = dict[str, object] | BaseModel | object


class PathResolutionError(ModelOnexError):
    """
    Error raised when path resolution fails.

    This error provides structured context about the path resolution failure,
    including the original path, the failing segment, and available alternatives.

    Attributes:
        path: The original path expression that failed to resolve
        segment: The specific path segment where resolution failed (if applicable)
        available_keys: List of available keys/attributes at the failure point
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: EnumCoreErrorCode = EnumCoreErrorCode.OPERATION_FAILED,
        path: str | None = None,
        segment: str | None = None,
        available_keys: list[str] | None = None,
    ) -> None:
        """
        Initialize a PathResolutionError.

        Args:
            message: Human-readable error description
            error_code: The error code category (default: OPERATION_FAILED)
            path: The original path expression that failed
            segment: The specific segment where resolution failed
            available_keys: List of available keys/attributes at failure point
        """
        context: TypedDictPathResolutionContext = {}
        if path is not None:
            context["path"] = path
        if segment is not None:
            context["segment"] = segment
        if available_keys is not None:
            context["available_keys"] = available_keys

        super().__init__(message=message, error_code=error_code, context=context)


def _validate_path_start(path: str) -> None:
    """
    Validate that a pipeline path starts with the required "$" prefix.

    Pipeline paths ($.input, $.steps) require the "$" prefix to distinguish
    them from simple field paths. This validation ensures proper path format.

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.

    Args:
        path: The path expression to validate.

    Raises:
        PathResolutionError: If path doesn't start with "$" (VALIDATION_ERROR).

    Example:
        >>> _validate_path_start("$.input.field")  # OK
        >>> _validate_path_start("input.field")  # raises PathResolutionError
    """
    if not path.startswith("$"):
        raise PathResolutionError(
            message=f"Invalid path: must start with '$', got '{path}'",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            path=path,
        )


def _validate_private_attribute(part: str, path: str) -> None:
    """
    Validate that a path segment doesn't access private attributes.

    Private attributes (those starting with "_") are blocked from path
    traversal when accessing object attributes for security reasons.

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.

    Args:
        part: The path segment (attribute name) to validate.
        path: The full path expression (for error context).

    Raises:
        PathResolutionError: If part starts with "_" (VALIDATION_ERROR).

    Note:
        This check is only applied when accessing object attributes,
        not dictionary keys. Dictionary keys starting with "_" are allowed.

    Example:
        >>> _validate_private_attribute("name", "$.user.name")  # OK
        >>> _validate_private_attribute("_private", "$.user._private")  # raises
    """
    if part.startswith("_"):
        raise PathResolutionError(
            message=f"Cannot access private attribute: '{part}'",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            path=path,
            segment=part,
        )


def _traverse_path_segments(
    current: TraversableData,
    parts: list[str],
    path: str,
    *,
    check_private: bool = True,
) -> object:
    """
    Traverse through path segments to resolve nested values.

    Navigates through nested data structures (dicts, objects) following
    the provided path segments. Handles both dictionary key access and
    object attribute access.

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.

    Args:
        current: The current data context to traverse from.
        parts: List of path segments to traverse.
        path: The original full path (for error messages).
        check_private: If True, block access to private attributes on objects.
            Dictionary keys are always accessible regardless of this setting.

    Returns:
        The value found at the end of the path traversal.

    Raises:
        PathResolutionError: If any segment cannot be resolved:
            - OPERATION_FAILED: Key or attribute not found
            - VALIDATION_ERROR: Attempted private attribute access (if check_private)

    Example:
        >>> data = {"user": {"name": "Alice"}}
        >>> _traverse_path_segments(data, ["user", "name"], "$.user.name")
        'Alice'
    """
    for part in parts:
        if not part:
            continue

        if isinstance(current, dict):
            if part not in current:
                raise PathResolutionError(
                    message=f"Path '{path}' not found: key '{part}' missing",
                    error_code=EnumCoreErrorCode.OPERATION_FAILED,
                    path=path,
                    segment=part,
                    available_keys=list(current.keys()) if current else [],
                )
            current = current[part]
        else:
            # For non-dict objects, check for private attribute access
            if check_private:
                _validate_private_attribute(part, path)

            if hasattr(current, part):
                current = getattr(current, part)
            else:
                raise PathResolutionError(
                    message=f"Path '{path}' not found: cannot access '{part}' on {type(current).__name__}",
                    error_code=EnumCoreErrorCode.OPERATION_FAILED,
                    path=path,
                    segment=part,
                )

    return current


def resolve_path(
    path: str,
    data: TraversableData,
    *,
    check_private: bool = True,
) -> object:
    """
    Resolve a simple dot-notation path to its value.

    Navigates into nested data structures using dot-notation paths to extract
    specific values. Supports both dictionary access and object attribute access.
    This is the core path resolution function used by JSON_PATH transformation.

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.

    Path Formats:
        - `$` or `""` (empty): Returns the root object
        - `$.field` or `field`: Direct field access
        - `$.field.subfield` or `field.subfield`: Nested field access

    Args:
        path: The path expression to resolve. The leading "$." prefix is optional.
        data: The input data structure to navigate (dict, object, or nested).
        check_private: If True (default), block access to private attributes
            (those starting with "_") on objects. Dictionary keys are always
            accessible regardless of this setting.

    Returns:
        The value found at the specified path.

    Raises:
        PathResolutionError: If the path cannot be resolved:
            - OPERATION_FAILED: Key or attribute not found
            - VALIDATION_ERROR: Attempted private attribute access

    Example:
        >>> data = {"user": {"name": "Alice", "profile": {"age": 30}}}
        >>> resolve_path("user.profile.age", data)
        30
        >>> resolve_path("$.user.name", data)
        'Alice'
        >>> resolve_path("$", data) == data
        True
    """
    # Handle root-level access
    if not path or path == "$":
        return data

    # Normalize path: remove leading "$." or "$" if present
    if path.startswith("$."):
        path = path[2:]
    elif path.startswith("$"):
        path = path[1:]

    # Split path and traverse
    parts = path.split(".")
    return _traverse_path_segments(data, parts, path, check_private=check_private)


def resolve_input_path(
    path: str,
    input_data: TraversableData,
) -> object:
    """
    Resolve a pipeline input path expression ($.input prefix).

    Extracts values from the pipeline input data using the $.input path syntax.
    This function handles the input-specific path resolution for mapping steps.

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.

    Path Formats:
        - `$.input` or `$input`: Returns the full input object
        - `$.input.<field>`: Direct child field of input
        - `$.input.<field>.<subfield>`: Nested field access (unlimited depth)

    Args:
        path: The path expression starting with "$.input" or "$input".
        input_data: The pipeline input data (dict, Pydantic model, or object).

    Returns:
        The resolved value from the input data.

    Raises:
        PathResolutionError: If the path cannot be resolved or is malformed.

    Example:
        >>> input_data = {"user": {"name": "Alice"}}
        >>> resolve_input_path("$.input", input_data)
        {'user': {'name': 'Alice'}}
        >>> resolve_input_path("$.input.user.name", input_data)
        'Alice'
    """
    # Handle both $.input and $input as aliases
    if path == "$.input" or path == "$input":
        return input_data

    # Extract remaining path after $.input.
    if path.startswith("$.input."):
        remaining = path[8:]  # Remove "$.input."
    elif path.startswith("$input."):
        remaining = path[7:]  # Remove "$input."
    else:
        raise PathResolutionError(
            message=f"Invalid input path format: '{path}'. Expected '$.input' or '$.input.<field>'",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            path=path,
        )

    parts = remaining.split(".")
    return _traverse_path_segments(input_data, parts, path, check_private=True)


def resolve_step_path(
    path: str,
    step_results: Mapping[str, object],
) -> object:
    """
    Resolve a pipeline step path expression ($.steps prefix).

    Extracts values from previous step results using the $.steps path syntax.
    This function handles the step-specific path resolution for mapping steps.

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.

    Path Formats:
        - `$.steps.<step_name>`: Returns the step's output (shorthand form)
        - `$.steps.<step_name>.output`: Returns the step's output (explicit form)

    Note:
        Both path forms are equivalent and return the step's output value.
        The shorthand form is preferred for readability. The explicit `.output`
        suffix is supported for clarity and forward compatibility.

    v1.0 Limitations:
        Only `.output` access is supported in v1.0. Future versions may expose
        additional step result fields like `.metadata` or `.duration_ms`.

    Args:
        path: The path expression starting with "$.steps.<name>".
        step_results: Dictionary of results from previously executed steps.
            Each result should have an `.output` attribute or be the output directly.

    Returns:
        The resolved step output value.

    Raises:
        PathResolutionError: If the step is not found or path is malformed.

    Example:
        >>> from dataclasses import dataclass
        >>> @dataclass
        ... class StepResult:
        ...     output: str
        >>> step_results = {"transform": StepResult(output="HELLO")}
        >>> resolve_step_path("$.steps.transform", step_results)
        'HELLO'
        >>> resolve_step_path("$.steps.transform.output", step_results)
        'HELLO'
    """
    if not path.startswith("$.steps."):
        raise PathResolutionError(
            message=f"Invalid step path format: '{path}'. Expected '$.steps.<step_name>'",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            path=path,
        )

    # Extract step name and optional subpath
    remaining = path[8:]  # Remove "$.steps."
    parts = remaining.split(".", 1)
    step_name = parts[0]

    if not step_name:
        raise PathResolutionError(
            message=f"Invalid step path: missing step name in '{path}'",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            path=path,
        )

    if step_name not in step_results:
        raise PathResolutionError(
            message=f"Step '{step_name}' not found in executed steps",
            error_code=EnumCoreErrorCode.OPERATION_FAILED,
            path=path,
            segment=step_name,
            available_keys=list(step_results.keys()),
        )

    result = step_results[step_name]

    # Shorthand: $.steps.<name> returns output directly
    if len(parts) == 1:
        # If result has .output attribute, return it; otherwise return result directly
        if hasattr(result, "output"):
            return result.output
        return result

    # Explicit path after step name
    sub_path = parts[1]
    if sub_path == "output":
        if hasattr(result, "output"):
            return result.output
        return result
    else:
        raise PathResolutionError(
            message=f"Invalid step path: only '.output' supported in v1.0, got '.{sub_path}'",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            path=path,
            segment=sub_path,
        )


def resolve_pipeline_path(
    path: str,
    input_data: TraversableData,
    step_results: Mapping[str, object],
) -> object:
    """
    Resolve a pipeline path expression to its value.

    This is the main entry point for resolving paths in pipeline mapping steps.
    It dispatches to the appropriate resolver based on the path prefix ($.input
    or $.steps).

    Thread Safety:
        This function is pure and stateless - safe for concurrent use.

    Supported Path Formats:
        - `$.input` or `$input`: Returns the full input object
        - `$.input.<field>`: Direct child field of input
        - `$.input.<field>.<subfield>`: Nested field access (unlimited depth)
        - `$.steps.<step_name>`: Returns the step's output (shorthand form)
        - `$.steps.<step_name>.output`: Returns the step's output (explicit form)

    Path Alias Conventions:
        - `$input` is equivalent to `$.input`
        - `$.steps.<name>` is equivalent to `$.steps.<name>.output`

    Args:
        path: The path expression to resolve. Must start with "$".
        input_data: The original pipeline input (dict, Pydantic model, or object).
        step_results: Dictionary of results from previously executed steps.

    Returns:
        The resolved value. Type depends on the path target.

    Raises:
        PathResolutionError: If the path is invalid or cannot be resolved.

    Example:
        >>> from dataclasses import dataclass
        >>> @dataclass
        ... class StepResult:
        ...     output: str
        >>> input_data = {"user": {"name": "Alice"}}
        >>> step_results = {"normalize": StepResult(output="HELLO")}
        >>> resolve_pipeline_path("$.input.user.name", input_data, step_results)
        'Alice'
        >>> resolve_pipeline_path("$.steps.normalize", input_data, step_results)
        'HELLO'
    """
    _validate_path_start(path)

    # Handle input paths (including $input alias)
    if path in ("$.input", "$input") or path.startswith(("$.input.", "$input.")):
        return resolve_input_path(path, input_data)

    # Handle step paths
    if path.startswith("$.steps."):
        return resolve_step_path(path, step_results)

    # Invalid prefix
    raise PathResolutionError(
        message=f"Invalid path prefix: '{path}'. Must be '$.input', '$input', or '$.steps.<name>'",
        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        path=path,
    )


__all__ = [
    # Error type
    "PathResolutionError",
    # Core resolution functions
    "resolve_path",
    "resolve_input_path",
    "resolve_step_path",
    "resolve_pipeline_path",
]
