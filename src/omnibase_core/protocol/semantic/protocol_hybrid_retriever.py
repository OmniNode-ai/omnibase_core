"""
Protocol interface for hybrid retrieval systems.

Defines the contract for retrieval systems that combine multiple search
strategies such as BM25 and dense vector search.
"""

from typing import Protocol

from omnibase_core.model.semantic.model_retrieval_input_state import \
    ModelRetrievalInputState
from omnibase_core.model.semantic.model_retrieval_output_state import \
    ModelRetrievalOutputState


class ProtocolHybridRetriever(Protocol):
    """
    Protocol for hybrid retrieval tools.

    This protocol defines the interface for tools that combine multiple
    retrieval strategies to improve search relevance and coverage.
    """

    def retrieve(
        self, input_state: ModelRetrievalInputState
    ) -> ModelRetrievalOutputState:
        """
        Perform hybrid retrieval combining multiple search strategies.

        Args:
            input_state: Input state containing query and search parameters

        Returns:
            Output state with retrieved documents and metadata
        """
        ...
