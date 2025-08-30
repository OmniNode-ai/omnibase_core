"""
Pydantic models for Haystack document processing operations.

This module defines the data models used for document processing workflows
using the Haystack NLP framework.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class ModelDocumentSource(BaseModel):
    """Model representing a document source for processing."""

    source_id: str = Field(..., description="Unique identifier for the document source")
    source_path: Union[str, Path] = Field(
        ..., description="Path or URL to the document"
    )
    source_type: str = Field(..., description="Type of source (file, url, s3, etc.)")
    file_format: Optional[str] = Field(None, description="Document file format")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional source metadata"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Source creation timestamp"
    )

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v):
        allowed_types = ["file", "url", "s3", "gcs", "azure_blob", "ftp"]
        if v not in allowed_types:
            raise ValueError(f"Source type must be one of {allowed_types}")
        return v


class ModelDocumentValidationResult(BaseModel):
    """Model representing document validation results."""

    source_id: str = Field(..., description="Document source identifier")
    is_valid: bool = Field(..., description="Whether the document is valid")
    validation_errors: List[str] = Field(
        default_factory=list, description="List of validation errors"
    )
    file_size_bytes: Optional[int] = Field(
        None, description="Document file size in bytes"
    )
    format_detected: Optional[str] = Field(None, description="Detected document format")
    encoding_detected: Optional[str] = Field(None, description="Detected text encoding")
    validation_timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Validation timestamp"
    )


class ModelExtractedText(BaseModel):
    """Model representing extracted text content from a document."""

    source_id: str = Field(..., description="Source document identifier")
    extracted_text: str = Field(..., description="Extracted text content")
    text_length: int = Field(..., description="Length of extracted text")
    extraction_method: str = Field(..., description="Method used for text extraction")
    language_detected: Optional[str] = Field(None, description="Detected text language")
    confidence_score: Optional[float] = Field(
        None, description="Extraction confidence score"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Extraction metadata"
    )
    extracted_at: datetime = Field(
        default_factory=datetime.utcnow, description="Extraction timestamp"
    )

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence_score(cls, v):
        if v is not None and not 0.0 <= v <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        return v


class ModelChunkingStrategy(BaseModel):
    """Model representing a text chunking strategy."""

    strategy_name: str = Field(..., description="Name of the chunking strategy")
    strategy_type: str = Field(
        ..., description="Type of strategy (sentence_based, paragraph_based, etc.)"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Strategy-specific parameters"
    )
    description: Optional[str] = Field(
        None, description="Human-readable description of the strategy"
    )


class ModelTextChunk(BaseModel):
    """Model representing a chunk of text for processing."""

    chunk_id: str = Field(..., description="Unique identifier for the text chunk")
    source_id: str = Field(..., description="Source document identifier")
    chunk_text: str = Field(..., description="Text content of the chunk")
    chunk_index: int = Field(..., description="Index of chunk within the document")
    chunk_size: int = Field(..., description="Size of chunk in characters")
    start_position: int = Field(..., description="Start position in original document")
    end_position: int = Field(..., description="End position in original document")
    overlap_size: int = Field(
        default=0, description="Overlap size with adjacent chunks"
    )
    strategy: Optional[ModelChunkingStrategy] = Field(
        None, description="Chunking strategy used"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Chunk creation timestamp"
    )


class ModelEmbeddingGeneration(BaseModel):
    """Model representing embedding generation configuration and results."""

    embedding_id: str = Field(..., description="Unique identifier for the embedding")
    chunk_id: str = Field(..., description="Source text chunk identifier")
    embedding_vector: List[float] = Field(..., description="Generated embedding vector")
    embedding_dimension: int = Field(
        ..., description="Dimension of the embedding vector"
    )
    model_name: str = Field(..., description="Name of the embedding model used")
    model_version: Optional[str] = Field(
        None, description="Version of the embedding model"
    )
    generation_time_ms: Optional[float] = Field(
        None, description="Time taken to generate embedding"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Embedding metadata"
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Generation timestamp"
    )

    @field_validator("embedding_dimension")
    @classmethod
    def validate_embedding_dimension(cls, v):
        if v <= 0:
            raise ValueError("Embedding dimension must be positive")
        return v


class ModelHaystackPipelineConfig(BaseModel):
    """Model representing Haystack pipeline configuration."""

    pipeline_name: str = Field(..., description="Name of the Haystack pipeline")
    pipeline_type: str = Field(
        ..., description="Type of pipeline (indexing, query, etc.)"
    )
    document_store_config: Dict[str, Any] = Field(
        ..., description="Document store configuration"
    )
    retriever_config: Dict[str, Any] = Field(
        default_factory=dict, description="Retriever configuration"
    )
    processor_config: Dict[str, Any] = Field(
        default_factory=dict, description="Processor configuration"
    )
    pipeline_components: List[str] = Field(
        ..., description="List of pipeline component names"
    )
    custom_components: Dict[str, Any] = Field(
        default_factory=dict, description="Custom component configurations"
    )

    @field_validator("pipeline_type")
    @classmethod
    def validate_pipeline_type(cls, v):
        allowed_types = [
            "indexing",
            "query",
            "document_classification",
            "question_answering",
            "summarization",
            "document_processing",
        ]
        if v not in allowed_types:
            raise ValueError(f"Pipeline type must be one of {allowed_types}")
        return v


class ModelDocumentProcessingBatch(BaseModel):
    """Model representing a batch of documents for processing."""

    batch_id: str = Field(..., description="Unique identifier for the processing batch")
    batch_name: Optional[str] = Field(
        None, description="Human-readable name for the batch"
    )
    document_sources: List[ModelDocumentSource] = Field(
        ..., description="List of document sources in the batch"
    )
    batch_size: int = Field(..., description="Number of documents in the batch")
    processing_config: Dict[str, Any] = Field(
        default_factory=dict, description="Configuration for batch processing"
    )
    priority: int = Field(
        default=5, description="Processing priority (1-10, higher is more priority)"
    )
    created_by: str = Field(..., description="Creator of the processing batch")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Batch creation timestamp"
    )

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v):
        if not 1 <= v <= 10:
            raise ValueError("Priority must be between 1 and 10")
        return v


class ModelDocumentProcessingResult(BaseModel):
    """Model representing the result of document processing operations."""

    batch_id: str = Field(..., description="Processing batch identifier")
    source_id: str = Field(..., description="Source document identifier")
    processing_status: str = Field(
        ..., description="Status of processing (success, failed, partial)"
    )
    extracted_text: Optional[ModelExtractedText] = Field(
        None, description="Extracted text result"
    )
    text_chunks: List[ModelTextChunk] = Field(
        default_factory=list, description="Generated text chunks"
    )
    embeddings: List[ModelEmbeddingGeneration] = Field(
        default_factory=list, description="Generated embeddings"
    )
    processing_errors: List[str] = Field(
        default_factory=list, description="List of processing errors"
    )
    processing_warnings: List[str] = Field(
        default_factory=list, description="List of processing warnings"
    )
    processing_time_seconds: Optional[float] = Field(
        None, description="Total processing time"
    )
    memory_usage_mb: Optional[float] = Field(
        None, description="Peak memory usage during processing"
    )
    processed_at: datetime = Field(
        default_factory=datetime.utcnow, description="Processing completion timestamp"
    )

    @field_validator("processing_status")
    @classmethod
    def validate_processing_status(cls, v):
        allowed_statuses = ["success", "failed", "partial", "pending", "in_progress"]
        if v not in allowed_statuses:
            raise ValueError(f"Processing status must be one of {allowed_statuses}")
        return v


class ModelHaystackPipelineMetrics(BaseModel):
    """Model representing Haystack pipeline performance metrics."""

    pipeline_name: str = Field(..., description="Name of the pipeline")
    metrics_period_start: datetime = Field(
        ..., description="Start of metrics collection period"
    )
    metrics_period_end: datetime = Field(
        ..., description="End of metrics collection period"
    )

    # Document processing metrics
    documents_processed: int = Field(default=0, description="Total documents processed")
    documents_failed: int = Field(
        default=0, description="Total documents that failed processing"
    )
    processing_success_rate: float = Field(
        default=0.0, description="Success rate of document processing"
    )

    # Performance metrics
    average_processing_time_seconds: float = Field(
        default=0.0, description="Average document processing time"
    )
    total_processing_time_seconds: float = Field(
        default=0.0, description="Total processing time"
    )
    throughput_docs_per_minute: float = Field(
        default=0.0, description="Document processing throughput"
    )

    # Resource utilization metrics
    peak_memory_usage_mb: float = Field(default=0.0, description="Peak memory usage")
    average_cpu_utilization: float = Field(
        default=0.0, description="Average CPU utilization"
    )

    # Embedding generation metrics
    embeddings_generated: int = Field(
        default=0, description="Total embeddings generated"
    )
    average_embedding_time_ms: float = Field(
        default=0.0, description="Average embedding generation time"
    )
    embedding_cache_hit_rate: float = Field(
        default=0.0, description="Embedding cache hit rate"
    )

    # Quality metrics
    text_extraction_accuracy: Optional[float] = Field(
        None, description="Text extraction accuracy score"
    )
    chunk_quality_score: Optional[float] = Field(
        None, description="Text chunk quality score"
    )
    embedding_quality_score: Optional[float] = Field(
        None, description="Embedding quality score"
    )

    @field_validator("processing_success_rate", "embedding_cache_hit_rate")
    @classmethod
    def validate_rate(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Rate must be between 0.0 and 1.0")
        return v


class ModelHaystackHealthCheck(BaseModel):
    """Model representing Haystack pipeline health check results."""

    pipeline_name: str = Field(..., description="Name of the pipeline being checked")
    health_status: str = Field(..., description="Overall health status")
    check_timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Health check timestamp"
    )

    # Component health status
    document_store_healthy: bool = Field(
        ..., description="Document store health status"
    )
    retriever_healthy: bool = Field(..., description="Retriever health status")
    embedder_healthy: bool = Field(..., description="Embedder health status")

    # Performance indicators
    response_time_ms: float = Field(
        ..., description="Pipeline response time in milliseconds"
    )
    memory_usage_mb: float = Field(..., description="Current memory usage")
    cpu_utilization: float = Field(..., description="Current CPU utilization")

    # Error tracking
    recent_errors: List[str] = Field(
        default_factory=list, description="Recent error messages"
    )
    error_count_last_hour: int = Field(
        default=0, description="Error count in the last hour"
    )

    # Additional health metrics
    connections_active: int = Field(
        default=0, description="Number of active connections"
    )
    queue_depth: int = Field(default=0, description="Current processing queue depth")
    last_successful_operation: Optional[datetime] = Field(
        None, description="Timestamp of last successful operation"
    )

    @field_validator("health_status")
    @classmethod
    def validate_health_status(cls, v):
        allowed_statuses = ["healthy", "degraded", "unhealthy", "unknown"]
        if v not in allowed_statuses:
            raise ValueError(f"Health status must be one of {allowed_statuses}")
        return v
