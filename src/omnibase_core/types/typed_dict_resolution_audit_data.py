"""
TypedDict for resolution audit data captured during capability resolution.

This TypedDict captures detailed resolution information for debugging
and audit purposes. Used internally by ServiceCapabilityResolver.

.. versionadded:: 0.4.0
"""

from __future__ import annotations

from typing import TypedDict

__all__ = ["TypedDictResolutionAuditData"]


class TypedDictResolutionAuditData(TypedDict):
    """Internal audit data captured during resolution.

    Captures detailed resolution information for debugging
    and audit purposes. Used internally by _resolve_with_audit().

    Attributes:
        candidates: List of provider IDs considered before filtering.
        scores: Mapping of provider_id -> score for providers that passed filtering.
        rejection_reasons: Mapping of provider_id -> reason for rejected providers.
    """

    candidates: list[str]
    scores: dict[str, float]
    rejection_reasons: dict[str, str]
