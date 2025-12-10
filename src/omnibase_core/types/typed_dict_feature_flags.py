from __future__ import annotations

"""
TypedDict for feature flags.
"""


from datetime import datetime
from typing import NotRequired, TypedDict


class TypedDictFeatureFlags(TypedDict):
    """TypedDict for feature flags."""

    feature_name: str
    enabled: bool
    environment: str
    updated_at: datetime
    updated_by: str
    description: NotRequired[str]


__all__ = ["TypedDictFeatureFlags"]
