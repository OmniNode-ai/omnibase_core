"""Enumeration for demo validation verdict."""

from __future__ import annotations

from enum import Enum

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ["EnumDemoVerdict"]


class EnumDemoVerdict(StrValueHelper, str, Enum):
    """Verdict for demo validation results.

    Determines the outcome of a demo validation run based on pass rate thresholds.

    Values:
        PASS: All invariants passed (100% pass rate).
        FAIL: Pass rate below review threshold (<80%).
        REVIEW: Pass rate between thresholds (80-99%), requires manual review.

    Example:
        .. code-block:: python

            from omnibase_core.enums import EnumDemoVerdict

            verdict = EnumDemoVerdict.PASS
            if verdict == EnumDemoVerdict.FAIL:
                raise ValidationError("Demo validation failed")

    .. versionadded:: 0.7.0
        Added as part of Demo V1 CLI (OMN-1397)
    """

    PASS = "PASS"
    """All invariants passed with 100% pass rate."""

    REVIEW = "REVIEW"
    """Pass rate requires manual review."""

    FAIL = "FAIL"
    """Pass rate below review threshold."""
