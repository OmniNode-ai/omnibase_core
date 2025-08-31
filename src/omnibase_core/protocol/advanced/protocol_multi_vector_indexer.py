"""
Protocol interface for multi-vector indexing implementations.

Defines the contract for tools that implement DPR-style multi-vector
document indexing with passage-level granularity and document context.
"""

from typing import Protocol, runtime_checkable

from omnibase_core.model.advanced.model_multi_vector_document import (
    ModelMultiVectorDocument,
)
from omnibase_core.model.semantic.model_input_document import ModelInputDocument


@runtime_checkable
class ProtocolMultiVectorIndexer(Protocol):
    """
    Protocol interface for multi-vector indexing implementations.

    ONEX PATTERNS:
    - Uses @runtime_checkable for type checking at runtime
    - Defines clear contract for indexing implementations
    - Supports dependency injection via duck typing
    - Uses specific Pydantic models, not generic types
    """

    def index_document(
        self,
        input_document: ModelInputDocument,
    ) -> ModelMultiVectorDocument:
        """
        Index a single document with multi-vector passage embeddings.

        Args:
            input_document: Input document to process and index

        Returns:
            Multi-vector document with passage-level embeddings
        """
        ...

    def index_documents(
        self,
        input_documents: list[ModelInputDocument],
    ) -> list[ModelMultiVectorDocument]:
        """
        Batch index multiple documents with multi-vector passage embeddings.

        Args:
            input_documents: List of input documents to process and index

        Returns:
            List of multi-vector documents with passage-level embeddings
        """
        ...

    def update_document_index(
        self,
        document_id: str,
        input_document: ModelInputDocument,
    ) -> ModelMultiVectorDocument:
        """
        Update an existing document's multi-vector index.

        Args:
            document_id: Existing document ID to update
            input_document: Updated document content

        Returns:
            Updated multi-vector document
        """
        ...

    def delete_document_index(self, document_id: str) -> bool:
        """
        Delete a document's multi-vector index.

        Args:
            document_id: Document ID to delete

        Returns:
            True if deletion successful, False otherwise
        """
        ...

    def optimize_index(self) -> dict:
        """
        Optimize the multi-vector index for better performance.

        Returns:
            Dictionary with optimization statistics
        """
        ...

    def get_index_statistics(self) -> dict:
        """
        Get statistics about the multi-vector index.

        Returns:
            Dictionary with index statistics and metrics
        """
        ...

    def health_check(self) -> dict:
        """
        Perform health check for the indexer.

        Returns:
            Dictionary with health status information
        """
        ...
