"""
Model for extraction metadata in debug intelligence system.

This model represents metadata about how debug context was extracted
and processed for analysis.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ModelExtractionMetadata(BaseModel):
    """Model for extraction metadata."""

    extraction_method: str = Field(description="Method used for extraction")
    extraction_timestamp: datetime = Field(
        default_factory=datetime.now, description="When the extraction was performed"
    )
    data_sources_used: List[str] = Field(
        default_factory=list, description="List of data sources used for extraction"
    )
    processing_time_seconds: Optional[float] = Field(
        default=None, description="Time taken to process the extraction"
    )
    confidence_level: float = Field(
        description="Confidence in the extraction quality (0.0 to 1.0)"
    )
    records_processed: Optional[int] = Field(
        default=None, description="Number of records processed during extraction"
    )
    extraction_version: str = Field(
        default="1.0", description="Version of the extraction algorithm used"
    )
    filters_applied: List[str] = Field(
        default_factory=list, description="Filters applied during extraction"
    )
    errors_encountered: List[str] = Field(
        default_factory=list, description="Any errors encountered during extraction"
    )
