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
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

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
