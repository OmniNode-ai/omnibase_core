"""Distance metric enumeration for vector similarity search.

This module defines the distance metrics supported by vector store operations.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumVectorDistanceMetric(StrValueHelper, str, Enum):
    """Distance metrics for vector similarity calculations.

    These metrics determine how similarity between vectors is computed:

    - COSINE: Angular similarity between vectors. This enum value represents the
      metric type; actual return values depend on the backend implementation:
        - Qdrant: Returns cosine distance (1 - cosine_similarity), range 0-2
        - Pinecone: Returns cosine similarity directly, range -1 to 1
        - Other backends may vary; consult backend documentation
      Generally, values closer to 0 (distance) or 1 (similarity) indicate more
      similar vectors.
    - EUCLIDEAN: Measures straight-line distance (L2 norm)
    - DOT_PRODUCT: Dot product similarity (higher = more similar)
    - MANHATTAN: Sum of absolute differences (L1 norm)

    Note:
        This enum specifies which metric algorithm to use. The interpretation of
        returned values (distance vs similarity, value ranges) is backend-specific.
        Always consult the documentation of your vector store backend.

    Example:
        >>> from omnibase_core.enums import EnumVectorDistanceMetric
        >>> metric = EnumVectorDistanceMetric.COSINE
        >>> assert metric.value == "cosine"
    """

    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot_product"
    MANHATTAN = "manhattan"


__all__ = ["EnumVectorDistanceMetric"]
