"""Workflow result data model for Reducer Pattern Engine."""

from pydantic import BaseModel, Field


class ModelWorkflowResultData(BaseModel):
    """Strongly typed workflow result data model."""

    # Document processing results
    processed_content: str | None = Field(
        None,
        description="Processed document content",
    )
    document_url: str | None = Field(None, description="URL to processed document")
    document_size_bytes: int | None = Field(
        None,
        description="Size of processed document",
    )

    # Analysis results
    analysis_summary: str | None = Field(
        None,
        description="Summary of analysis results",
    )
    key_findings: list[str] = Field(
        default_factory=list,
        description="Key findings from analysis",
    )
    confidence_score: float | None = Field(
        None,
        description="Confidence score for analysis",
        ge=0.0,
        le=1.0,
    )

    # Report generation results
    report_url: str | None = Field(None, description="URL to generated report")
    report_format: str | None = Field(None, description="Format of generated report")
    chart_urls: list[str] = Field(
        default_factory=list,
        description="URLs to generated charts",
    )

    # Common result fields
    output_files: list[str] = Field(
        default_factory=list,
        description="List of output file paths",
    )
    metrics: list[str] = Field(default_factory=list, description="Processing metrics")

    # Quality metrics
    quality_score: float | None = Field(
        None,
        description="Quality score of processing",
        ge=0.0,
        le=1.0,
    )
    validation_passed: bool = Field(
        True,
        description="Whether validation checks passed",
    )

    # Resource usage
    processing_duration_ms: int | None = Field(
        None,
        description="Processing duration in milliseconds",
    )
    memory_used_mb: float | None = Field(None, description="Memory used in MB")
