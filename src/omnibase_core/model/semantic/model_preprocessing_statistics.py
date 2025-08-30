"""
Processing statistics model for text preprocessing operations.

Provides strongly-typed statistics to replace Dict[str, Any] usage.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ModelPreprocessingStatistics(BaseModel):
    """
    Statistics about preprocessing operation.

    Replaces Dict[str, Any] usage in preprocessing_statistics fields.
    """

    total_documents: int = Field(
        default=0, description="Total number of documents processed"
    )

    successful_documents: int = Field(
        default=0, description="Number of documents processed successfully"
    )

    failed_documents: int = Field(
        default=0, description="Number of documents that failed processing"
    )

    total_chunks: int = Field(default=0, description="Total number of chunks created")

    average_chunk_size: Optional[float] = Field(
        default=None, description="Average chunk size in characters"
    )

    total_processing_time_ms: Optional[int] = Field(
        default=None, description="Total processing time in milliseconds"
    )

    average_processing_time_per_doc_ms: Optional[float] = Field(
        default=None, description="Average processing time per document in milliseconds"
    )

    memory_usage_mb: Optional[float] = Field(
        default=None, description="Peak memory usage during processing in MB"
    )

    documents_with_warnings: int = Field(
        default=0, description="Number of documents that had warnings"
    )

    documents_skipped: int = Field(
        default=0, description="Number of documents skipped due to filters"
    )

    model_config = ConfigDict(
        use_enum_values=True, validate_assignment=True, extra="forbid"
    )
