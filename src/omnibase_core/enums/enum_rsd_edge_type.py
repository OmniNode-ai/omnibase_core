"""
RSD Edge Type Enumeration.

Defines edge types for RSD (Rapid Service Development) ticket relationships.
"""

from enum import Enum


class EnumRsdEdgeType(str, Enum):
    """Enumeration of RSD edge types for ticket relationships."""

    DEPENDS_ON = "depends_on"
    BLOCKS = "blocks"
    RELATES_TO = "relates_to"
    PARENT_OF = "parent_of"
    CHILD_OF = "child_of"
    DUPLICATE_OF = "duplicate_of"
    CAUSED_BY = "caused_by"
