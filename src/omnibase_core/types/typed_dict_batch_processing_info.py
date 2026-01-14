"""
TypedDict for batch processing information.
"""

from __future__ import annotations

from datetime import datetime
from typing import NotRequired, TypedDict
from uuid import UUID


class TypedDictBatchProcessingInfo(TypedDict):
    batch_id: UUID
    total_items: int
    processed_items: int
    successful_items: int
    failed_items: int
    started_at: datetime
    estimated_completion: NotRequired[datetime]


__all__ = ["TypedDictBatchProcessingInfo"]
