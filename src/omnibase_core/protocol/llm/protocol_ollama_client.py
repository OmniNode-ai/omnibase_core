"""
Protocol interface for Ollama client operations.

Defines the standard interface for interacting with Ollama local LLM models
for query enhancement, answer generation, and conversational capabilities.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterator

from omnibase_core.enums.enum_query_type import EnumQueryType
from omnibase_core.model.llm.model_answer_generation_result import (
    ModelAnswerGenerationResult,
)
from omnibase_core.model.llm.model_conversation_context import ModelRetrievedDocument
from omnibase_core.model.llm.model_llm_health_response import ModelLLMHealthResponse
from omnibase_core.model.llm.model_ollama_capabilities import ModelOllamaCapabilities
from omnibase_core.model.llm.model_query_enhancement_result import (
    ModelQueryEnhancementResult,
)


class ProtocolOllamaClient(ABC):
    """
    Protocol for Ollama client operations.

    Defines the interface for query enhancement, answer generation,
    and conversational capabilities using local Ollama models with
    strong typing and ONEX standards compliance.
    """

    @abstractmethod
    def get_available_models(self) -> list[str]:
        """Get list of available Ollama models."""

    @abstractmethod
    def get_model_capabilities(self, model_name: str) -> ModelOllamaCapabilities:
        """Get capabilities for a specific model."""

    @abstractmethod
    def health_check(self) -> ModelLLMHealthResponse:
        """Check health and availability of Ollama service."""

    @abstractmethod
    def enhance_query(
        self,
        query: str,
        context_documents: list[ModelRetrievedDocument] | None = None,
    ) -> ModelQueryEnhancementResult:
        """
        Enhance a natural language query for better retrieval.

        Args:
            query: Original user query
            context_documents: Optional context documents for enhancement

        Returns:
            Query enhancement result with enhanced query and metadata
        """

    @abstractmethod
    def generate_answer(
        self,
        query: str,
        context_documents: list[ModelRetrievedDocument],
        sources: list[str] | None = None,
    ) -> ModelAnswerGenerationResult:
        """
        Generate an answer from retrieved context documents.

        Args:
            query: User's original question
            context_documents: Retrieved documents providing context
            sources: Optional source references for citation

        Returns:
            Answer generation result with generated content and metadata
        """

    @abstractmethod
    def generate_answer_stream(
        self,
        query: str,
        context_documents: list[ModelRetrievedDocument],
        sources: list[str] | None = None,
    ) -> Iterator[str]:
        """
        Generate streaming answer from retrieved context documents.

        Args:
            query: User's original question
            context_documents: Retrieved documents providing context
            sources: Optional source references for citation

        Yields:
            Streaming answer chunks
        """

    @abstractmethod
    def select_best_model(self, query_type: EnumQueryType) -> str:
        """
        Select the best model for a given query type.

        Args:
            query_type: Type of query using EnumQueryType

        Returns:
            Best model name for the query type
        """

    @abstractmethod
    def validate_response_quality(
        self,
        question: str,
        answer: str,
        sources: list[str],
    ) -> float:
        """
        Validate the quality of a generated response.

        Args:
            question: Original question
            answer: Generated answer
            sources: Source documents used

        Returns:
            Quality score (0.0 to 1.0)
        """
