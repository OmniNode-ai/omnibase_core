"""
Task configuration models for LLM task queue.

Provides strongly-typed configuration models to replace Dict[str, Any] usage
while maintaining flexibility for different task types and execution contexts.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelLLMTaskConfiguration(BaseModel):
    """
    Strongly-typed configuration for LLM tasks.

    Replaces Dict[str, Any] with specific typed fields while maintaining
    flexibility for different task types and execution scenarios.
    """

    # Analysis configuration
    analysis_depth: str | None = Field(
        default=None,
        description="Analysis depth level: 'basic', 'detailed', 'comprehensive'",
    )

    output_format: str | None = Field(
        default=None,
        description="Desired output format: 'text', 'json', 'markdown', 'structured'",
    )

    # Document processing configuration
    document_id: str | None = Field(
        default=None,
        description="Document ID for document-related tasks",
    )

    document_sections: list[str] | None = Field(
        default=None,
        description="Specific document sections to process",
    )

    # Batch processing configuration
    batch_size: int | None = Field(
        default=None,
        ge=1,
        le=1000,
        description="Number of items to process per batch",
    )

    parallel_processing: bool | None = Field(
        default=None,
        description="Whether to enable parallel processing",
    )

    # Generation configuration
    creativity_level: str | None = Field(
        default=None,
        description="Creativity level: 'conservative', 'balanced', 'creative'",
    )

    tone: str | None = Field(
        default=None,
        description="Desired tone: 'formal', 'casual', 'technical', 'friendly'",
    )

    language: str | None = Field(
        default=None,
        description="Target language code (e.g., 'en', 'es', 'fr')",
    )

    # Embeddings configuration
    embedding_model: str | None = Field(
        default=None,
        description="Specific embedding model to use",
    )

    vector_dimensions: int | None = Field(
        default=None,
        ge=1,
        description="Number of vector dimensions for embeddings",
    )

    # Quality and safety configuration
    content_filter_level: str | None = Field(
        default=None,
        description="Content filtering level: 'none', 'basic', 'strict'",
    )

    quality_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum quality threshold for output",
    )

    # Custom parameters for extensibility
    custom_parameters: dict | None = Field(
        default_factory=dict,
        description="Custom task-specific parameters (use sparingly)",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "analysis_depth": "comprehensive",
                "output_format": "structured_json",
                "document_id": "doc_12345",
                "batch_size": 50,
                "creativity_level": "balanced",
                "tone": "technical",
                "language": "en",
                "content_filter_level": "basic",
                "quality_threshold": 0.8,
            },
        },
    )


class ModelLLMExecutionContext(BaseModel):
    """
    Strongly-typed execution context for LLM task results.

    Replaces Dict[str, Any] with specific typed fields for execution
    metadata and runtime information.
    """

    # Worker information
    worker_id: str | None = Field(
        default=None,
        description="ID of the worker that processed the task",
    )

    worker_type: str | None = Field(
        default=None,
        description="Type of worker: 'dramatiq_llm_actor', 'manual', 'batch_processor'",
    )

    # Queue information
    queue_name: str | None = Field(
        default=None,
        description="Name of the queue that processed the task",
    )

    routing_decision: str | None = Field(
        default=None,
        description="Details about why this queue was selected",
    )

    # Processing information
    task_type: str | None = Field(
        default=None,
        description="Type of LLM task that was executed",
    )

    model_router_version: str | None = Field(
        default=None,
        description="Version of the model router used",
    )

    # Error context (if applicable)
    error_type: str | None = Field(
        default=None,
        description="Type of error that occurred (if task failed)",
    )

    error_phase: str | None = Field(
        default=None,
        description="Phase where error occurred: 'initialization', 'execution', 'finalization'",
    )

    retry_count: int | None = Field(
        default=None,
        ge=0,
        description="Number of retries attempted",
    )

    # Performance context
    cpu_usage_percent: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="CPU usage percentage during execution",
    )

    memory_peak_mb: int | None = Field(
        default=None,
        ge=0,
        description="Peak memory usage in MB",
    )

    # Custom context for extensibility
    custom_context: dict | None = Field(
        default_factory=dict,
        description="Custom execution context (use sparingly)",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "worker_id": "worker_001",
                "worker_type": "dramatiq_llm_actor",
                "queue_name": "llm_analysis",
                "routing_decision": "local_preference_high_context",
                "task_type": "llm_analysis",
                "model_router_version": "v1_0_0",
                "retry_count": 0,
                "cpu_usage_percent": 45.2,
                "memory_peak_mb": 1840,
            },
        },
    )


class ModelLLMStructuredOutput(BaseModel):
    """
    Strongly-typed structured output for LLM task results.

    Replaces Dict[str, Any] for structured output data with common
    patterns while maintaining flexibility.
    """

    # Text analysis results
    summary: str | None = Field(
        default=None,
        description="Generated summary or key points",
    )

    key_insights: list[str] | None = Field(
        default=None,
        description="List of key insights or findings",
    )

    sentiment_score: float | None = Field(
        default=None,
        ge=-1.0,
        le=1.0,
        description="Sentiment score from -1 (negative) to 1 (positive)",
    )

    confidence_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score for the analysis",
    )

    # Generation results
    generated_text: str | None = Field(
        default=None,
        description="Main generated text content",
    )

    alternative_versions: list[str] | None = Field(
        default=None,
        description="Alternative generated versions",
    )

    # Embeddings results
    embeddings: list[float] | None = Field(
        default=None,
        description="Generated embedding vectors",
    )

    embedding_model_used: str | None = Field(
        default=None,
        description="Model used for generating embeddings",
    )

    # Classification results
    categories: list[str] | None = Field(
        default=None,
        description="Identified categories or classifications",
    )

    tags: list[str] | None = Field(
        default=None,
        description="Generated tags or labels",
    )

    # Quality metrics
    quality_metrics: dict | None = Field(
        default_factory=dict,
        description="Quality assessment metrics",
    )

    # Custom structured data for extensibility
    custom_data: dict | None = Field(
        default_factory=dict,
        description="Custom structured output data (use sparingly)",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "summary": "The document discusses quarterly revenue growth...",
                "key_insights": [
                    "Revenue increased 15% year-over-year",
                    "Customer satisfaction improved",
                    "New market opportunities identified",
                ],
                "sentiment_score": 0.8,
                "confidence_score": 0.92,
                "categories": ["financial_report", "quarterly_analysis"],
                "tags": ["growth", "revenue", "performance"],
            },
        },
    )
