"""
Overlap strategy enumeration for chunk boundaries.

Defines the available strategies for handling overlap between text chunks
during preprocessing operations in the semantic discovery engine.
"""

from enum import Enum


class ModelOverlapStrategy(str, Enum):
    """Overlap strategy for chunk boundaries."""

    FIXED_OVERLAP = "fixed_overlap"
    STRIDE_BASED = "stride_based"
    SENTENCE_BOUNDARY = "sentence_boundary"
    SEMANTIC_BOUNDARY = "semantic_boundary"
