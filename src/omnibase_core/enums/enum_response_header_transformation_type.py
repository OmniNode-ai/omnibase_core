"""
Response Header Transformation Type Enum.

Strongly typed response header transformation operation values.
Defines the types of transformations that can be applied to HTTP response headers.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumResponseHeaderTransformationType(StrValueHelper, str, Enum):
    """
    Strongly typed response header transformation operation values.

    Defines the types of transformations that can be applied to HTTP response headers:
    - SET: Replace the header value completely
    - APPEND: Add to the end of existing header value
    - PREFIX: Add to the beginning of existing header value
    - SUFFIX: Add to the end of existing header value (alias for APPEND)
    - REMOVE: Remove the header entirely
    - FILTER: Filter/modify header value based on rules
    """

    SET = "set"
    APPEND = "append"
    PREFIX = "prefix"
    SUFFIX = "suffix"
    REMOVE = "remove"
    FILTER = "filter"


# Export for use
__all__ = ["EnumResponseHeaderTransformationType"]
