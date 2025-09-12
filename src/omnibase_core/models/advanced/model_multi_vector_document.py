"""
Multi-vector document model for DPR-style passage retrieval.

Enables granular passage-level indexing and retrieval with document context.
Each document is split into passages with individual embeddings while maintaining
document-level relationships for contextual understanding.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_semver import ModelSemVer


class ModelPassageEmbedding(BaseModel):
    """Individual passage embedding within a multi-vector document."""

    passage_id: str = Field(
        ...,
        description="Unique identifier for this passage within the document",
    )
    start_char: int = Field(
        ...,
        description="Start character position of passage in original document",
    )
    end_char: int = Field(
        ...,
        description="End character position of passage in original document",
    )
    content: str = Field(..., description="Text content of this passage")
    embedding: list[float] = Field(
        ...,
        description="Dense vector embedding for this passage",
    )
    embedding_model: str = Field(
        ...,
        description="Model used to generate this embedding",
    )
    passage_type: str = Field(
        default="text",
        description="Type of passage (text, code, table, list, etc.)",
    )
    semantic_density: float = Field(
        default=0.0,
        description="Semantic density score (0.0 to 1.0)",
    )
    contextual_weight: float = Field(
        default=1.0,
        description="Contextual importance weight within document",
    )
    metadata: dict[str, str | int | float | bool] = Field(
        default_factory=dict,
        description="Additional passage metadata",
    )


class ModelDocumentStructure(BaseModel):
    """Document structure information for hierarchical indexing."""

    section_title: str | None = Field(None, description="Section or heading title")
    section_level: int = Field(
        default=0,
        description="Hierarchical level (0=root, 1=h1, 2=h2, etc.)",
    )
    section_path: list[str] = Field(
        default_factory=list,
        description="Hierarchical path to this section",
    )
    parent_section: str | None = Field(None, description="Parent section identifier")
    child_sections: list[str] = Field(
        default_factory=list,
        description="Child section identifiers",
    )


class ModelMultiVectorDocument(BaseModel):
    """
    Multi-vector document model for DPR-style passage retrieval.

    Supports fine-grained passage-level embeddings while maintaining
    document-level context and hierarchical structure awareness.
    """

    # Document Identity
    document_id: str = Field(..., description="Unique document identifier")
    document_title: str | None = Field(
        None,
        description="Document title or filename",
    )
    document_url: str | None = Field(None, description="Source URL or file path")
    document_hash: str = Field(..., description="Content hash for change detection")

    # Content and Structure
    full_content: str = Field(..., description="Complete document content")
    passages: list[ModelPassageEmbedding] = Field(
        ...,
        description="Individual passage embeddings",
    )
    document_structure: ModelDocumentStructure | None = Field(
        None,
        description="Hierarchical document structure information",
    )

    # Multi-Vector Configuration
    chunking_strategy: str = Field(
        ...,
        description="Strategy used for passage creation (adaptive, fixed, semantic, etc.)",
    )
    chunk_size: int = Field(..., description="Target chunk size in characters")
    chunk_overlap: int = Field(
        default=0,
        description="Character overlap between chunks",
    )

    # Document-Level Embedding
    document_embedding: list[float] | None = Field(
        None,
        description="Document-level embedding for coarse-grained retrieval",
    )
    document_summary: str | None = Field(
        None,
        description="Generated document summary",
    )

    # Indexing Metadata
    indexed_at: str = Field(..., description="ISO timestamp when document was indexed")
    indexing_version: ModelSemVer = Field(
        ...,
        description="Version of indexing system used",
    )
    total_passages: int = Field(
        ...,
        description="Total number of passages in this document",
    )

    # Quality Metrics
    semantic_coherence: float = Field(
        default=0.0,
        description="Semantic coherence score across passages",
    )
    passage_diversity: float = Field(
        default=0.0,
        description="Semantic diversity score across passages",
    )

    # Additional Metadata
    language: str | None = Field(
        None,
        description="Document language (ISO 639-1 code)",
    )
    content_type: str = Field(
        default="text",
        description="Content type (text, code, markdown, etc.)",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Document tags for filtering",
    )
    metadata: dict[str, str | int | float | bool] = Field(
        default_factory=dict,
        description="Additional document metadata",
    )

    def get_passage_by_id(self, passage_id: str) -> ModelPassageEmbedding | None:
        """Retrieve a specific passage by ID."""
        for passage in self.passages:
            if passage.passage_id == passage_id:
                return passage
        return None

    def get_passages_by_type(self, passage_type: str) -> list[ModelPassageEmbedding]:
        """Retrieve all passages of a specific type."""
        return [p for p in self.passages if p.passage_type == passage_type]

    def get_context_for_passage(
        self,
        passage_id: str,
        context_size: int = 1,
    ) -> list[ModelPassageEmbedding]:
        """Get surrounding context passages for a given passage."""
        passage_idx = None
        for i, passage in enumerate(self.passages):
            if passage.passage_id == passage_id:
                passage_idx = i
                break

        if passage_idx is None:
            return []

        start_idx = max(0, passage_idx - context_size)
        end_idx = min(len(self.passages), passage_idx + context_size + 1)

        return self.passages[start_idx:end_idx]

    def calculate_semantic_density(self) -> float:
        """Calculate overall semantic density of the document."""
        if not self.passages:
            return 0.0

        total_density = sum(p.semantic_density for p in self.passages)
        return total_density / len(self.passages)

    def get_high_density_passages(
        self,
        threshold: float = 0.7,
    ) -> list[ModelPassageEmbedding]:
        """Get passages with high semantic density."""
        return [p for p in self.passages if p.semantic_density >= threshold]
