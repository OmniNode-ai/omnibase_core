# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Degraded behavior enum for specifying fallback strategy when data is unavailable."""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper

__all__ = ["EnumDegradedBehavior"]


@unique
class EnumDegradedBehavior(UtilStrValueHelper, str, Enum):
    """Fallback strategy to apply when a data source is unavailable or stale."""

    SERVE_STALE_WITH_WARNING = "serve_stale_with_warning"
    RETURN_EMPTY = "return_empty"
    FAIL_CLOSED = "fail_closed"

    @classmethod
    def _missing_(cls, value: object) -> EnumDegradedBehavior | None:
        """Return no implicit aliases for unknown degraded-behavior values."""
        return None
