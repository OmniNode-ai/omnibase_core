from __future__ import annotations

from pydantic import BaseModel, Field

from .model_unified_summary_details import ModelUnifiedSummaryDetails


class ModelUnifiedSummary(BaseModel):
    """
    Summary model with totals and details for unified results
    """

    total: int = Field(..., ge=0)
    passed: int = Field(..., ge=0)
    failed: int = Field(..., ge=0)
    skipped: int = Field(..., ge=0)
    fixed: int = Field(..., ge=0)
    warnings: int = Field(..., ge=0)
    notes: list[str] | None = None
    details: ModelUnifiedSummaryDetails | None = None
