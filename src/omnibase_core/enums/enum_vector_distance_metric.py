# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Distance metric enumeration for vector similarity search.

This module defines the distance metrics supported by vector store operations.
"""

from enum import Enum, unique


@unique
class EnumVectorDistanceMetric(str, Enum):
    """Distance metrics for vector similarity calculations.

    These metrics determine how similarity between vectors is computed:

    - COSINE: Measures angle between vectors (range: 0-2, lower = more similar)
    - EUCLIDEAN: Measures straight-line distance (L2 norm)
    - DOT_PRODUCT: Dot product similarity (higher = more similar)
    - MANHATTAN: Sum of absolute differences (L1 norm)

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
