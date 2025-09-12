"""
Hybrid retrieval configuration model.

Defines configuration options for hybrid retrieval systems that combine
multiple search strategies such as BM25 and dense vector search.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.semantic.model_embedding_model import ModelEmbeddingModel


class ModelHybridRetrievalConfig(BaseModel):
    """Configuration for hybrid retrieval strategy."""

    # Weight balancing
    bm25_weight: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Weight for BM25 scores in hybrid search",
    )

    dense_weight: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Weight for dense vector scores in hybrid search",
    )

    # Retrieval parameters
    top_k_bm25: int = Field(
        default=20,
        ge=1,
        le=1000,
        description="Number of results to retrieve from BM25",
    )

    top_k_dense: int = Field(
        default=20,
        ge=1,
        le=1000,
        description="Number of results to retrieve from dense search",
    )

    final_top_k: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Final number of results to return",
    )

    # Score normalization
    normalize_scores: bool = Field(
        default=True,
        description="Whether to normalize scores before fusion",
    )

    score_fusion_method: str = Field(
        default="weighted_sum",
        description="Score fusion method: weighted_sum, rank_fusion, max_score",
    )

    # Query analysis
    enable_query_analysis: bool = Field(
        default=True,
        description="Enable adaptive query type analysis",
    )

    keyword_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Threshold for keyword vs semantic query detection",
    )

    # Embedding model configuration
    embedding_model: ModelEmbeddingModel = Field(
        default=ModelEmbeddingModel.BGE_BASE_EN,
        description="Embedding model to use for dense retrieval",
    )

    embedding_model_device: str | None = Field(
        default=None,
        description="Device to run embedding model on (cpu, cuda, mps, auto)",
    )

    embedding_batch_size: int = Field(
        default=32,
        ge=1,
        le=512,
        description="Batch size for embedding generation",
    )

    embedding_max_length: int | None = Field(
        default=512,
        ge=64,
        le=8192,
        description="Maximum sequence length for embeddings",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )
