"""
TypedDict for feature flags.
"""

from __future__ import annotations

from datetime import datetime
from typing import NotRequired, TypedDict


class TypedDictFeatureFlags(TypedDict):
    feature_name: str
    enabled: bool
    environment: str
    updated_at: datetime
    updated_by: str
    description: NotRequired[str]


__all__ = ["TypedDictFeatureFlags"]
