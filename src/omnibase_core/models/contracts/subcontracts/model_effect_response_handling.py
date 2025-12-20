"""
Effect Response Handling Model.

Response extraction and validation configuration for effect operations.
Defines success codes, field extraction, and extraction engine settings.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelEffectResponseHandling"]


class ModelEffectResponseHandling(BaseModel):
    """
    Response extraction and validation configuration for effect operations.

    Defines how to interpret operation responses, including success criteria
    and field extraction. Extracted fields are made available to subsequent
    operations and the final ModelEffectOutput.

    Extraction Engines:
        - jsonpath: Full JSONPath syntax via jsonpath-ng library. Supports
            complex queries like "$.data[*].items[?(@.active==true)].id".
            Fails at contract load time if jsonpath-ng is not installed.
        - dotpath: Simple dot-notation syntax ($.field.subfield). No external
            dependencies. Suitable for straightforward field access.

    Security Considerations:
        Field extraction paths are subject to security controls:

        1. **Path Depth Limit**: Dotpath extraction enforces a maximum traversal
           depth of 10 levels (DEFAULT_MAX_FIELD_EXTRACTION_DEPTH). Paths exceeding
           this limit return None, preventing denial-of-service via deeply nested
           or maliciously crafted paths. JSONPath extraction does not have this
           limit but relies on jsonpath-ng's implementation.

        2. **Character Validation**: Dotpath extraction validates paths against
           SAFE_FIELD_PATTERN (^[a-zA-Z0-9_.]+$), rejecting paths containing:
           - Special characters (parentheses, brackets, semicolons)
           - Injection patterns (__import__, eval(), etc.)
           - Path traversal attempts (../)

        3. **Type Safety**: Only primitive types (str, int, float, bool, None)
           are extracted. Complex objects (dicts, lists) are rejected to prevent
           accidental data exposure.

        These controls are enforced in MixinEffectExecution._extract_field()
        and _extract_response_fields().

    Attributes:
        success_codes: HTTP status codes considered successful. Operations
            returning other codes are treated as failures. Defaults to
            [200, 201, 202, 204] (common success codes).
        extract_fields: Map of output_name to JSONPath/dotpath expression for
            extracting values from responses. Example: {"user_id": "$.data.id"}.
        fail_on_empty: Whether to fail if extraction returns empty/null.
            Defaults to False (empty values are acceptable).
        extraction_engine: Which extraction engine to use. Defaults to "jsonpath"
            for full JSONPath support. Use "dotpath" if jsonpath-ng is unavailable.

    Example:
        >>> handling = ModelEffectResponseHandling(
        ...     success_codes=[200, 201],
        ...     extract_fields={
        ...         "user_id": "$.data.id",
        ...         "email": "$.data.email",
        ...     },
        ...     fail_on_empty=True,
        ...     extraction_engine="jsonpath",
        ... )

    See Also:
        - ModelEffectOperation.response_handling: Per-operation response handling
        - constants_effect.DEFAULT_MAX_FIELD_EXTRACTION_DEPTH: Depth limit constant
        - constants_effect.SAFE_FIELD_PATTERN: Path validation pattern
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    success_codes: list[int] = Field(default_factory=lambda: [200, 201, 202, 204])
    extract_fields: dict[str, str] = Field(
        default_factory=dict, description="Map of output_name -> JSONPath expression"
    )
    fail_on_empty: bool = Field(
        default=False, description="Fail if extraction returns empty"
    )

    # Explicit extraction engine - prevents silent fallback behavior
    extraction_engine: Literal["jsonpath", "dotpath"] = Field(
        default="jsonpath",
        description="Extraction engine. 'jsonpath' requires jsonpath-ng (fails at load if missing), "
        "'dotpath' uses simple $.field.subfield semantics.",
    )
