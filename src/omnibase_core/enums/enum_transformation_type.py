"""
v1.0 Transformation types for contract-driven NodeCompute.

This module defines the transformation types available in v1.0 compute pipelines.
Only 6 types are supported in v1.0 - collection operations are deferred to v1.1+.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumTransformationType(StrValueHelper, str, Enum):
    """
    v1.0 Transformation types.

    Only 6 types for v1.0 - collection operations deferred to v1.1+.

    Attributes:
        IDENTITY: Returns input unchanged (no-op passthrough).
        REGEX: Applies regex pattern replacement.
        CASE_CONVERSION: Converts text case (upper/lower/title).
        TRIM: Trims whitespace from text.
        NORMALIZE_UNICODE: Normalizes unicode to a standard form.
        JSON_PATH: Extracts data using JSONPath expression.
    """

    # v1.0 Types (6 transformations)
    IDENTITY = "identity"
    REGEX = "regex"
    CASE_CONVERSION = "case_conversion"
    TRIM = "trim"
    NORMALIZE_UNICODE = "normalize_unicode"
    JSON_PATH = "json_path"
    # v1.1+: SPLIT, JOIN, TEMPLATE, TYPE_CONVERSION
    # v1.2+: FILTER, MAP, REDUCE, SORT


__all__ = ["EnumTransformationType"]
