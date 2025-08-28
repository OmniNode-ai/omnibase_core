"""
Testing block model.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelTestingBlock(BaseModel):
    """Testing configuration and requirements."""

    canonical_test_case_ids: List[str] = Field(default_factory=list)
    required_ci_tiers: List[str] = Field(default_factory=list)
    minimum_coverage_percentage: Optional[float] = None
