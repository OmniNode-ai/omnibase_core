"""
Retrieved document model for search results.

Provides strongly-typed document structure to replace Dict[str, Any] usage.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelRetrievedDocument(BaseModel):
    """
    A single retrieved document with metadata and scoring.

    Replaces Dict[str, Any] usage in documents fields.
    """

    document_id: str = Field(description="Unique identifier for the document")

    content: str = Field(description="Document content or excerpt")

    title: str | None = Field(
        default=None,
        description="Document title if available",
    )

    source_path: str | None = Field(
        default=None,
        description="Original file path or URL",
    )

    similarity_score: float | None = Field(
        default=None,
        description="Similarity score from vector search (0-1)",
    )

    bm25_score: float | None = Field(
        default=None,
        description="BM25 relevance score",
    )

    hybrid_score: float | None = Field(
        default=None,
        description="Combined hybrid search score",
    )

    rank: int | None = Field(
        default=None,
        description="Rank position in search results",
    )

    chunk_index: int | None = Field(
        default=None,
        description="Chunk index within original document",
    )

    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Additional document metadata (string values only)",
    )

    tags: list[str] = Field(
        default_factory=list,
        description="Document tags or categories",
    )

    excerpt_start: int | None = Field(
        default=None,
        description="Start position of excerpt in original document",
    )

    excerpt_end: int | None = Field(
        default=None,
        description="End position of excerpt in original document",
    )

    relevance_explanation: str | None = Field(
        default=None,
        description="Explanation of why this document was retrieved",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )
