"""Filter operator enumeration for vector metadata filtering.

This module defines the operators supported for metadata filtering in vector queries.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumVectorFilterOperator(StrValueHelper, str, Enum):
    """Filter operators for metadata-based vector search filtering.

    These operators are used to filter vectors based on their metadata:

    - EQ: Equals (exact match)
    - NE: Not equals
    - GT: Greater than
    - GTE: Greater than or equal
    - LT: Less than
    - LTE: Less than or equal
    - IN: Value in list
    - NOT_IN: Value not in list
    - CONTAINS: String contains substring
    - STARTS_WITH: String starts with prefix
    - EXISTS: Field exists (not null)

    Example:
        >>> from omnibase_core.enums import EnumVectorFilterOperator
        >>> op = EnumVectorFilterOperator.EQ
        >>> assert op.value == "eq"
    """

    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    EXISTS = "exists"


__all__ = ["EnumVectorFilterOperator"]
