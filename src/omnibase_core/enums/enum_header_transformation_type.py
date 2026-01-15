"""
Header Transformation Type Enum.

Strongly typed header transformation operation values.
Defines the types of transformations that can be applied to HTTP headers.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumHeaderTransformationType(StrValueHelper, str, Enum):
    """
    Strongly typed header transformation operation values.

    Defines the types of transformations that can be applied to HTTP headers:
    - SET: Replace the header value completely
    - APPEND: Add to the end of existing header value
    - PREFIX: Add to the beginning of existing header value
    - SUFFIX: Add to the end of existing header value (alias for APPEND)
    - REMOVE: Remove the header entirely
    """

    SET = "set"
    APPEND = "append"
    PREFIX = "prefix"
    SUFFIX = "suffix"
    REMOVE = "remove"


# Export for use
__all__ = ["EnumHeaderTransformationType"]
