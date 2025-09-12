"""
Protocol interface for adaptive chunkers in ONEX.

Defines the contract for LangExtract-enhanced adaptive chunking tools.
"""

from typing import Protocol

from omnibase_core.core.onex_container import ModelONEXContainer
from omnibase_core.intelligence.services.langextract_intelligence_service import (
    ModelIntelligenceResult,
)
from omnibase_core.models.advanced.model_adaptive_chunk import ModelModelAdaptiveChunk
from omnibase_core.models.advanced.model_chunking_quality_metrics import (
    ModelModelChunkingQualityMetrics,
)
from omnibase_core.tools.discovery.advanced.tool_multi_vector_indexer.v1_0_0.models.model_tool_multi_vector_indexer_input_state import (
    ModelIndexingConfiguration,
)


class ProtocolAdaptiveChunker(Protocol):
    """Protocol for adaptive chunking tools."""

    def __init__(self, container: ModelONEXContainer) -> None:
        """Initialize adaptive chunker with container injection."""
        ...

    def chunk_content_adaptive(
        self,
        content: str,
        config: ModelIndexingConfiguration,
        intelligence_result: ModelIntelligenceResult | None = None,
        entities: list | None = None,
    ) -> tuple[list[ModelModelAdaptiveChunk], ModelModelChunkingQualityMetrics]:
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
