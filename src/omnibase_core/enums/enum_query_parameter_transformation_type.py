"""
Query Parameter Transformation Type Enum.

Strongly typed query parameter transformation operation values.
Defines the types of transformations that can be applied to URL query parameters.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumQueryParameterTransformationType(StrValueHelper, str, Enum):
    """
    Strongly typed query parameter transformation operation values.

    Defines the types of transformations that can be applied to URL query parameters:
    - SET: Replace the parameter value completely
    - APPEND: Add to the end of existing parameter value
    - PREFIX: Add to the beginning of existing parameter value
    - SUFFIX: Add to the end of existing parameter value (alias for APPEND)
    - REMOVE: Remove the parameter entirely
    - ENCODE: URL-encode the parameter value
    """

    SET = "set"
    APPEND = "append"
    PREFIX = "prefix"
    SUFFIX = "suffix"
    REMOVE = "remove"
    ENCODE = "encode"


# Export for use
__all__ = ["EnumQueryParameterTransformationType"]
