"""
EnumCoercionMode

Float-to-int coercion modes for ModelOptionalInt.

Defines how floating-point values should be converted to integers
during validation.

Values:
    STRICT: Only exact floats allowed (3.0 → 3, 3.5 raises error)
    FLOOR: Floor division (3.7 → 3, -3.7 → -4)
    CEIL: Ceiling division (3.2 → 4, -3.2 → -3)
    ROUND: Standard rounding (3.5 → 4, 3.4 → 3)

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""

from __future__ import annotations

from enum import Enum


class EnumCoercionMode(str, Enum):
    """
    Float-to-int coercion modes for ModelOptionalInt.

    Defines how floating-point values should be converted to integers
    during validation.

    Values:
        STRICT: Only exact floats allowed (3.0 → 3, 3.5 raises error)
        FLOOR: Floor division (3.7 → 3, -3.7 → -4)
        CEIL: Ceiling division (3.2 → 4, -3.2 → -3)
        ROUND: Standard rounding (3.5 → 4, 3.4 → 3)
    """

    STRICT = "strict"
    FLOOR = "floor"
    CEIL = "ceil"
    ROUND = "round"
