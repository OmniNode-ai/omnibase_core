"""
Testing block model.
"""

from pydantic import BaseModel, Field


class ModelTestingBlock(BaseModel):
    """Testing configuration and requirements."""

    canonical_test_case_ids: list[str] = Field(default_factory=list)
    required_ci_tiers: list[str] = Field(default_factory=list)
    minimum_coverage_percentage: float | None = None
