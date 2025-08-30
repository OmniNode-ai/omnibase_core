from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from .model_unified_summary_details import ModelUnifiedSummaryDetails


class ModelUnifiedSummary(BaseModel):
    """
    Summary model with totals and details for unified results
    """

    total: int
    passed: int
    failed: int
    skipped: int
    fixed: int
    warnings: int
    notes: Optional[List[str]] = None
    details: Optional[ModelUnifiedSummaryDetails] = None
