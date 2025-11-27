"""
Version Testing Model - Tier 3 Metadata.

Pydantic model for version-specific testing information.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_version_file import ModelVersionFile


class ModelVersionTesting(BaseModel):
    """Version-specific testing information."""

    test_files: list[ModelVersionFile] = Field(
        default_factory=list,
        description="Test implementation files",
    )
    test_coverage_percentage: float | None = Field(
        default=None,
        description="Actual test coverage percentage",
    )
    test_results: dict[str, str] = Field(
        default_factory=dict,
        description="Test execution results by test type",
    )
    performance_benchmarks: dict[str, float] = Field(
        default_factory=dict,
        description="Performance benchmark results",
    )
    last_test_date: datetime | None = Field(
        default=None,
        description="Date when tests were last executed",
    )
