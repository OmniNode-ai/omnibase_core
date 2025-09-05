"""Workflow result data model for Reducer Pattern Engine."""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ModelWorkflowResultData(BaseModel):
    """Strongly typed workflow result data model."""

    # Document processing results
    processed_content: Optional[str] = Field(
        None, description="Processed document content"
    )
    document_url: Optional[str] = Field(None, description="URL to processed document")
    document_size_bytes: Optional[int] = Field(
        None, description="Size of processed document"
    )

    # Analysis results
    analysis_summary: Optional[str] = Field(
        None, description="Summary of analysis results"
    )
    key_findings: List[str] = Field(
        default_factory=list, description="Key findings from analysis"
    )
    confidence_score: Optional[float] = Field(
        None, description="Confidence score for analysis", ge=0.0, le=1.0
    )

    # Report generation results
    report_url: Optional[str] = Field(None, description="URL to generated report")
    report_format: Optional[str] = Field(None, description="Format of generated report")
    chart_urls: List[str] = Field(
        default_factory=list, description="URLs to generated charts"
    )

    # Common result fields
    output_files: List[str] = Field(
        default_factory=list, description="List of output file paths"
    )
    metrics: List[str] = Field(default_factory=list, description="Processing metrics")

    # Quality metrics
    quality_score: Optional[float] = Field(
        None, description="Quality score of processing", ge=0.0, le=1.0
    )
    validation_passed: bool = Field(
        True, description="Whether validation checks passed"
    )

    # Resource usage
    processing_duration_ms: Optional[int] = Field(
        None, description="Processing duration in milliseconds"
    )
    memory_used_mb: Optional[float] = Field(None, description="Memory used in MB")
