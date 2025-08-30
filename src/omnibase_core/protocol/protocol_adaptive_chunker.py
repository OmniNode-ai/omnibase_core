"""
Protocol interface for adaptive chunkers in ONEX.

Defines the contract for LangExtract-enhanced adaptive chunking tools.
"""

from typing import List, Optional, Protocol, Tuple

from omnibase_core.core.onex_container import ONEXContainer
from omnibase_core.intelligence.services.langextract_intelligence_service import \
    ModelIntelligenceResult
from omnibase_core.model.advanced.model_adaptive_chunk import \
    ModelModelAdaptiveChunk
from omnibase_core.model.advanced.model_chunking_quality_metrics import \
    ModelModelChunkingQualityMetrics
from omnibase_core.tools.discovery.advanced.tool_multi_vector_indexer.v1_0_0.models.model_tool_multi_vector_indexer_input_state import \
    ModelIndexingConfiguration


class ProtocolAdaptiveChunker(Protocol):
    """Protocol for adaptive chunking tools."""

    def __init__(self, container: ONEXContainer) -> None:
        """Initialize adaptive chunker with container injection."""
        ...

    def chunk_content_adaptive(
        self,
        content: str,
        config: ModelIndexingConfiguration,
        intelligence_result: Optional[ModelIntelligenceResult] = None,
        entities: Optional[List] = None,
    ) -> Tuple[List[ModelModelAdaptiveChunk], ModelModelChunkingQualityMetrics]:
        """
        Perform LangExtract-enhanced adaptive chunking.

        Args:
            content: Text content to chunk
            config: Chunking configuration
            intelligence_result: LangExtract intelligence analysis
            entities: Extracted entities from content

        Returns:
            Tuple of (chunks, metrics)
        """
        ...
