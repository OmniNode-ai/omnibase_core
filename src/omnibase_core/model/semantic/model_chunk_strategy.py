"""
Chunk strategy enumeration for text preprocessing.

Defines the available strategies for chunking text during preprocessing
operations in the semantic discovery engine.
"""

from enum import Enum


class ModelChunkStrategy(str, Enum):
    """Chunking strategy for text preprocessing."""

    TOKEN_BASED = "token_based"
    SENTENCE_BASED = "sentence_based"
    PARAGRAPH_BASED = "paragraph_based"
    SEMANTIC_BASED = "semantic_based"
    HYBRID = "hybrid"
