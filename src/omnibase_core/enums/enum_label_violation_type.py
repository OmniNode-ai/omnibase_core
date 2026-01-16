"""Label violation type enum for metrics policy enforcement."""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumLabelViolationType(StrValueHelper, str, Enum):
    """Type of label policy violation detected.

    Used by ModelLabelViolation to categorize what kind of
    policy rule was violated.

    Types:
        FORBIDDEN_KEY: Label key is in the forbidden list.
        KEY_NOT_ALLOWED: Label key is not in the allowed list (strict mode).
        VALUE_TOO_LONG: Label value exceeds max_label_value_length.
    """

    FORBIDDEN_KEY = "forbidden_key"
    KEY_NOT_ALLOWED = "key_not_allowed"
    VALUE_TOO_LONG = "value_too_long"


__all__ = ["EnumLabelViolationType"]
