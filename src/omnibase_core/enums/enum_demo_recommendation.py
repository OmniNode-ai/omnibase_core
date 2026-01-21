"""Enumeration for demo promotion recommendation."""

from __future__ import annotations

from enum import Enum

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ["EnumDemoRecommendation"]


class EnumDemoRecommendation(StrValueHelper, str, Enum):
    """Recommendation for demo validation promotion.

    Determines the promotion recommendation based on pass rate thresholds.

    Values:
        PROMOTE: Perfect pass rate (100%), safe to promote.
        PROMOTE_WITH_REVIEW: High pass rate (90-99%), requires manual review.
        REJECT: Pass rate below threshold (<90%), not ready for promotion.

    Example:
        .. code-block:: python

            from omnibase_core.enums import EnumDemoRecommendation

            recommendation = EnumDemoRecommendation.PROMOTE
            if recommendation == EnumDemoRecommendation.REJECT:
                raise ValidationError("Demo not ready for promotion")

    .. versionadded:: 0.7.0
        Added as part of Demo V1 CLI (OMN-1397)
    """

    PROMOTE = "promote"
    """Perfect pass rate, safe to promote."""

    PROMOTE_WITH_REVIEW = "promote_with_review"
    """High pass rate but requires manual review before promotion."""

    REJECT = "reject"
    """Pass rate below threshold, not ready for promotion."""
