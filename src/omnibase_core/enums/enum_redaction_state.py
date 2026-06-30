# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EnumRedactionState: describes how much of a log entry has been redacted.

Canonical enum for OMN-13703 ModelStructuredLogEntry schema unification.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import UtilStrValueHelper


@unique
class EnumRedactionState(UtilStrValueHelper, str, Enum):
    """Redaction state applied to a ModelStructuredLogEntry before publishing."""

    NONE = "none"
    """No redaction applied; entry is published as-is."""

    PARTIAL = "partial"
    """Sensitive field values replaced with placeholder tokens."""

    FULL = "full"
    """All payload fields replaced; only structural metadata preserved."""


__all__ = ["EnumRedactionState"]
