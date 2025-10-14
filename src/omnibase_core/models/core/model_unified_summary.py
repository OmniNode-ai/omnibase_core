from __future__ import annotations

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
    notes: list[str] | None = None
    details: ModelUnifiedSummaryDetails | None = None
