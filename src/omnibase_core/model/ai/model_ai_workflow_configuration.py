"""
Pydantic models for AI workflow configuration.

This module defines the data models used for configuring AI workflows
in the scenario-driven orchestration system.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ModelAIServiceConfiguration(BaseModel):
    """Configuration for individual AI services."""

    service_name: str = Field(..., description="Name of the AI service")
    service_type: str = Field(
        ...,
        description="Type of AI service (haystack, qdrant, etc.)",
    )
    connection_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Service connection configuration",
    )
    authentication: dict[str, str] | None = Field(
        None,
        description="Authentication credentials",
    )
    timeout_seconds: int = Field(default=300, description="Service timeout in seconds")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    enable_caching: bool = Field(default=True, description="Enable result caching")

    @field_validator("service_type")
    @classmethod
    def validate_service_type(cls, v):
        allowed_types = [
            "haystack",
            "qdrant",
            "embedding_generator",
            "text_processor",
            "validator",
        ]
        if v not in allowed_types:
            msg = f"Service type must be one of {allowed_types}"
            raise ValueError(msg)
        return v


class ModelDocumentProcessingConfiguration(BaseModel):
    """Configuration for document processing workflows."""

    input_sources: list[str] = Field(
        ...,
        description="List of document source paths or URLs",
    )
    supported_formats: list[str] = Field(
        default=["pdf", "docx", "html", "txt"],
        description="Supported document formats",
    )
    max_file_size_mb: int = Field(default=100, description="Maximum file size in MB")
    batch_size: int = Field(
        default=50,
        description="Number of documents to process in a batch",
    )
    extraction_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Text extraction configuration",
    )
    chunking_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Text chunking configuration",
    )
    enable_parallel_processing: bool = Field(
        default=True,
        description="Enable parallel document processing",
    )

    @field_validator("supported_formats")
    @classmethod
    def validate_formats(cls, v):
        allowed_formats = ["pdf", "docx", "html", "txt", "md", "rtf"]
        for format_type in v:
            if format_type not in allowed_formats:
                msg = f"Format {format_type} not in allowed formats {allowed_formats}"
                raise ValueError(
                    msg,
                )
        return v


class ModelEmbeddingConfiguration(BaseModel):
    """Configuration for embedding generation."""

    model_name: str = Field(..., description="Name of the embedding model")
    model_provider: str = Field(
        default="openai",
        description="Embedding model provider",
    )
    embedding_dimension: int = Field(
        ...,
        description="Dimension of generated embeddings",
    )
    chunk_size: int = Field(
        default=512,
        description="Size of text chunks for embedding",
    )
    chunk_overlap: int = Field(default=50, description="Overlap between chunks")
    batch_size: int = Field(
        default=100,
        description="Batch size for embedding generation",
    )
    model_parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Model-specific configuration",
    )
    cache_embeddings: bool = Field(
        default=True,
        description="Cache generated embeddings",
    )

    @field_validator("embedding_dimension")
    @classmethod
    def validate_dimension(cls, v):
        allowed_dimensions = [128, 256, 384, 512, 768, 1024, 1536, 2048]
        if v not in allowed_dimensions:
            msg = f"Embedding dimension must be one of {allowed_dimensions}"
            raise ValueError(msg)
        return v


class ModelVectorDatabaseConfiguration(BaseModel):
    """Configuration for vector database operations."""

    collection_name: str = Field(..., description="Name of the vector collection")
    vector_size: int = Field(..., description="Size of vectors in the collection")
    distance_metric: str = Field(
        default="cosine",
        description="Distance metric for similarity search",
    )
    index_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Vector index configuration",
    )
    replication_factor: int = Field(
        default=1,
        description="Number of replicas for the collection",
    )
    shard_number: int = Field(
        default=1,
        description="Number of shards for the collection",
    )
    enable_payload_index: bool = Field(
        default=True,
        description="Enable indexing of payload fields",
    )
    optimization_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Index optimization configuration",
    )

    @field_validator("distance_metric")
    @classmethod
    def validate_distance_metric(cls, v):
        allowed_metrics = ["cosine", "euclidean", "dot", "manhattan"]
        if v not in allowed_metrics:
            msg = f"Distance metric must be one of {allowed_metrics}"
            raise ValueError(msg)
        return v


class ModelSearchConfiguration(BaseModel):
    """Configuration for similarity search operations."""

    top_k: int = Field(default=10, description="Number of top results to return")
    score_threshold: float = Field(
        default=0.7,
        description="Minimum similarity score threshold",
    )
    search_timeout_seconds: int = Field(
        default=30,
        description="Search timeout in seconds",
    )
    enable_hybrid_search: bool = Field(
        default=False,
        description="Enable hybrid search with text matching",
    )
    metadata_filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata filters for search",
    )
    result_ranking_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Result ranking configuration",
    )
    cache_search_results: bool = Field(default=True, description="Cache search results")
    cache_ttl_seconds: int = Field(default=300, description="Cache TTL in seconds")

    @field_validator("score_threshold")
    @classmethod
    def validate_score_threshold(cls, v):
        if not 0.0 <= v <= 1.0:
            msg = "Score threshold must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v


class ModelPerformanceConfiguration(BaseModel):
    """Configuration for performance monitoring and optimization."""

    max_processing_time_minutes: int = Field(
        default=30,
        description="Maximum processing time in minutes",
    )
    memory_limit_gb: int = Field(default=16, description="Memory limit in GB")
    cpu_cores: int | None = Field(None, description="Number of CPU cores to use")
    enable_gpu: bool = Field(default=False, description="Enable GPU acceleration")
    parallel_workers: int = Field(default=4, description="Number of parallel workers")
    monitoring_interval_seconds: int = Field(
        default=60,
        description="Monitoring interval in seconds",
    )
    performance_thresholds: dict[str, float] = Field(
        default_factory=dict,
        description="Performance thresholds",
    )

    @field_validator("parallel_workers")
    @classmethod
    def validate_workers(cls, v):
        if v < 1 or v > 32:
            msg = "Parallel workers must be between 1 and 32"
            raise ValueError(msg)
        return v


class ModelValidationConfiguration(BaseModel):
    """Configuration for workflow validation."""

    enable_input_validation: bool = Field(
        default=True,
        description="Enable input validation",
    )
    enable_output_validation: bool = Field(
        default=True,
        description="Enable output validation",
    )
    enable_performance_validation: bool = Field(
        default=True,
        description="Enable performance validation",
    )
    validation_thresholds: dict[str, float] = Field(
        default_factory=dict,
        description="Validation thresholds",
    )
    quality_metrics: list[str] = Field(
        default_factory=list,
        description="Quality metrics to track",
    )
    failure_handling: str = Field(
        default="retry",
        description="How to handle validation failures",
    )

    @field_validator("failure_handling")
    @classmethod
    def validate_failure_handling(cls, v):
        allowed_handling = ["retry", "skip", "abort", "continue"]
        if v not in allowed_handling:
            msg = f"Failure handling must be one of {allowed_handling}"
            raise ValueError(msg)
        return v


class ModelAIWorkflowConfiguration(BaseModel):
    """Complete configuration for AI workflows."""

    workflow_name: str = Field(..., description="Name of the AI workflow")
    workflow_version: str = Field(
        default="1.0.0",
        description="Version of the workflow",
    )
    description: str = Field(..., description="Description of the workflow")
    environment: str = Field(
        default="development",
        description="Environment (development, staging, production)",
    )
    created_by: str = Field(..., description="Creator of the workflow configuration")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Configuration creation timestamp",
    )

    # Service configurations
    services: list[ModelAIServiceConfiguration] = Field(
        ...,
        description="List of AI service configurations",
    )

    # Workflow-specific configurations
    document_processing: ModelDocumentProcessingConfiguration | None = Field(
        None,
        description="Document processing configuration",
    )
    embedding: ModelEmbeddingConfiguration | None = Field(
        None,
        description="Embedding generation configuration",
    )
    vector_database: ModelVectorDatabaseConfiguration | None = Field(
        None,
        description="Vector database configuration",
    )
    search: ModelSearchConfiguration | None = Field(
        None,
        description="Search configuration",
    )
    performance: ModelPerformanceConfiguration = Field(
        default_factory=ModelPerformanceConfiguration,
        description="Performance configuration",
    )
    validation: ModelValidationConfiguration = Field(
        default_factory=ModelValidationConfiguration,
        description="Validation configuration",
    )

    # Additional workflow parameters
    custom_parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom workflow parameters",
    )
    feature_flags: dict[str, bool] = Field(
        default_factory=dict,
        description="Feature flags for the workflow",
    )

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        allowed_environments = ["development", "staging", "production"]
        if v not in allowed_environments:
            msg = f"Environment must be one of {allowed_environments}"
            raise ValueError(msg)
        return v

    @field_validator("services")
    @classmethod
    def validate_services_not_empty(cls, v):
        if not v:
            msg = "At least one service configuration is required"
            raise ValueError(msg)
        return v

    def get_service_config(
        self,
        service_name: str,
    ) -> ModelAIServiceConfiguration | None:
        """Get configuration for a specific service by name."""
        for service in self.services:
            if service.service_name == service_name:
                return service
        return None

    def get_services_by_type(
        self,
        service_type: str,
    ) -> list[ModelAIServiceConfiguration]:
        """Get all services of a specific type."""
        return [
            service for service in self.services if service.service_type == service_type
        ]

    def to_scenario_parameters(self) -> dict[str, Any]:
        """Convert configuration to scenario parameters format."""
        return {
            "workflow_config": self.model_dump(),
            "pipeline_name": self.workflow_name,
            "environment": self.environment,
            "performance_config": self.performance.model_dump(),
            "validation_config": self.validation.model_dump(),
        }
