"""Canonical report model for demo validation results."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.demo.model_demo_config import ModelDemoConfig
from omnibase_core.models.demo.model_demo_summary import ModelDemoSummary
from omnibase_core.models.demo.model_sample_result import ModelSampleResult
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Current schema version for demo validation reports
DEMO_REPORT_SCHEMA_VERSION = ModelSemVer(major=1, minor=0, patch=0)


class ModelDemoValidationReport(BaseModel):
    """Canonical report for demo validation results.

    Top-level model aggregating all demo validation data including configuration,
    summary statistics, and detailed per-sample results. Includes schema version
    for future evolution.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    schema_version: ModelSemVer = Field(
        default_factory=lambda: DEMO_REPORT_SCHEMA_VERSION,
        description="Schema version for report format evolution",
    )
    scenario: str = Field(..., description="Name of the executed scenario")
    timestamp: str = Field(..., description="ISO-8601 timestamp of report generation")
    config: ModelDemoConfig = Field(
        ..., description="Configuration used for the demo run"
    )
    summary: ModelDemoSummary = Field(
        ..., description="Aggregated summary of validation results"
    )
    results: list[ModelSampleResult] = Field(
        ..., description="Per-sample validation results"
    )


__all__ = ["DEMO_REPORT_SCHEMA_VERSION", "ModelDemoValidationReport"]
