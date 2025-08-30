"""
Output state model for hybrid retrieval operations.

Defines the output results and metadata from hybrid retrieval
operations that combine multiple search strategies.
"""

from typing import List, Optional

from pydantic import ConfigDict, Field

from omnibase_core.model.core.model_onex_output_state import OnexOutputState
from omnibase_core.model.semantic.model_query_analysis import \
    ModelQueryAnalysis
from omnibase_core.model.semantic.model_retrieval_operation_statistics import \
    ModelRetrievalOperationStatistics
from omnibase_core.model.semantic.model_retrieved_document import \
    ModelRetrievedDocument


class ModelRetrievalOutputState(OnexOutputState):
    """
    Output state for hybrid retrieval operations.

    Contains retrieved documents, relevance scores,
    and metadata from hybrid search operations.
    """

    documents: List[ModelRetrievedDocument] = Field(
        description="List of retrieved documents with scores", default_factory=list
    )

    retrieval_statistics: ModelRetrievalOperationStatistics = Field(
        description="Statistics about the retrieval operation",
        default_factory=ModelRetrievalOperationStatistics,
    )

    query_analysis: ModelQueryAnalysis = Field(
        description="Analysis of the input query", default_factory=ModelQueryAnalysis
    )

    bm25_results_count: int = Field(
        default=0, description="Number of results from BM25 retrieval"
    )

    dense_results_count: int = Field(
        default=0, description="Number of results from dense retrieval"
    )

    total_search_time_ms: Optional[int] = Field(
        default=None, description="Total search time in milliseconds"
    )

    cache_hit: bool = Field(
        default=False, description="Whether results were served from cache"
    )

    fusion_method: Optional[str] = Field(
        default=None, description="Method used to combine retrieval results"
    )

    model_config = ConfigDict(
        use_enum_values=True, validate_assignment=True, extra="forbid"
    )
