# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Vector store domain models for ONEX SPI handler protocols.

Typed Pydantic models for vector store operations,
replacing untyped dict[str, Any] placeholders in SPI handler protocols.

The models are organized into these categories:

**Enums:**
    - EnumVectorDistanceMetric: Distance metrics (cosine, euclidean, etc.)
    - EnumVectorFilterOperator: Filter operators (eq, ne, gt, etc.)

**Core Models:**
    - ModelEmbedding: Single embedding with metadata
    - ModelVectorSearchResult: Single search result
    - ModelVectorMetadataFilter: Metadata filter condition

**Configuration Models:**
    - ModelVectorConnectionConfig: Connection parameters
    - ModelVectorIndexConfig: Index configuration
    - ModelHnswConfig: HNSW index tuning
    - ModelQuantizationConfig: Vector quantization settings

**Result Models:**
    - ModelVectorStoreResult: Single store operation result
    - ModelVectorBatchStoreResult: Batch store operation result
    - ModelVectorSearchResults: Search results container
    - ModelVectorDeleteResult: Delete operation result
    - ModelVectorIndexResult: Index operation result

**Metadata Models:**
    - ModelVectorHealthStatus: Health check result
    - ModelVectorHandlerMetadata: Handler capabilities

Example:
    Basic vector store operations::

        from omnibase_core.models.vector import (
            ModelEmbedding,
            ModelVectorSearchResults,
            EnumVectorDistanceMetric,
        )

        # Create an embedding
        embedding = ModelEmbedding(
            id="doc_123",
            vector=[0.1, 0.2, 0.3, 0.4],
        )

        # Search results
        results = ModelVectorSearchResults(
            results=[...],
            total_results=10,
            query_time_ms=15,
        )
"""

from __future__ import annotations

# Enums
import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.enums.enum_vector_distance_metric import EnumVectorDistanceMetric
    from omnibase_core.enums.enum_vector_filter_operator import EnumVectorFilterOperator

    # Core models
    from omnibase_core.models.vector.model_embedding import ModelEmbedding

    # Configuration models
    from omnibase_core.models.vector.model_hnsw_config import ModelHnswConfig
    from omnibase_core.models.vector.model_quantization_config import (
        ModelQuantizationConfig,
    )

    # Result models
    from omnibase_core.models.vector.model_vector_batch_store_result import (
        ModelVectorBatchStoreResult,
    )
    from omnibase_core.models.vector.model_vector_connection_config import (
        ModelVectorConnectionConfig,
    )
    from omnibase_core.models.vector.model_vector_delete_result import (
        ModelVectorDeleteResult,
    )

    # Metadata models
    from omnibase_core.models.vector.model_vector_handler_metadata import (
        ModelVectorHandlerMetadata,
    )
    from omnibase_core.models.vector.model_vector_health_status import (
        ModelVectorHealthStatus,
    )
    from omnibase_core.models.vector.model_vector_index_config import (
        ModelVectorIndexConfig,
    )
    from omnibase_core.models.vector.model_vector_index_result import (
        ModelVectorIndexResult,
    )
    from omnibase_core.models.vector.model_vector_metadata_filter import (
        ModelVectorMetadataFilter,
    )
    from omnibase_core.models.vector.model_vector_search_result import (
        ModelVectorSearchResult,
    )
    from omnibase_core.models.vector.model_vector_search_results import (
        ModelVectorSearchResults,
    )
    from omnibase_core.models.vector.model_vector_store_result import (
        ModelVectorStoreResult,
    )

__all__ = [
    # Enums
    "EnumVectorDistanceMetric",
    "EnumVectorFilterOperator",
    # Core models
    "ModelEmbedding",
    "ModelVectorMetadataFilter",
    "ModelVectorSearchResult",
    # Configuration models
    "ModelHnswConfig",
    "ModelQuantizationConfig",
    "ModelVectorConnectionConfig",
    "ModelVectorIndexConfig",
    # Result models
    "ModelVectorBatchStoreResult",
    "ModelVectorDeleteResult",
    "ModelVectorIndexResult",
    "ModelVectorSearchResults",
    "ModelVectorStoreResult",
    # Metadata models
    "ModelVectorHandlerMetadata",
    "ModelVectorHealthStatus",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "EnumVectorDistanceMetric": (
        "omnibase_core.enums.enum_vector_distance_metric",
        "EnumVectorDistanceMetric",
    ),
    "EnumVectorFilterOperator": (
        "omnibase_core.enums.enum_vector_filter_operator",
        "EnumVectorFilterOperator",
    ),
    "ModelEmbedding": ("omnibase_core.models.vector.model_embedding", "ModelEmbedding"),
    "ModelHnswConfig": (
        "omnibase_core.models.vector.model_hnsw_config",
        "ModelHnswConfig",
    ),
    "ModelQuantizationConfig": (
        "omnibase_core.models.vector.model_quantization_config",
        "ModelQuantizationConfig",
    ),
    "ModelVectorBatchStoreResult": (
        "omnibase_core.models.vector.model_vector_batch_store_result",
        "ModelVectorBatchStoreResult",
    ),
    "ModelVectorConnectionConfig": (
        "omnibase_core.models.vector.model_vector_connection_config",
        "ModelVectorConnectionConfig",
    ),
    "ModelVectorDeleteResult": (
        "omnibase_core.models.vector.model_vector_delete_result",
        "ModelVectorDeleteResult",
    ),
    "ModelVectorHandlerMetadata": (
        "omnibase_core.models.vector.model_vector_handler_metadata",
        "ModelVectorHandlerMetadata",
    ),
    "ModelVectorHealthStatus": (
        "omnibase_core.models.vector.model_vector_health_status",
        "ModelVectorHealthStatus",
    ),
    "ModelVectorIndexConfig": (
        "omnibase_core.models.vector.model_vector_index_config",
        "ModelVectorIndexConfig",
    ),
    "ModelVectorIndexResult": (
        "omnibase_core.models.vector.model_vector_index_result",
        "ModelVectorIndexResult",
    ),
    "ModelVectorMetadataFilter": (
        "omnibase_core.models.vector.model_vector_metadata_filter",
        "ModelVectorMetadataFilter",
    ),
    "ModelVectorSearchResult": (
        "omnibase_core.models.vector.model_vector_search_result",
        "ModelVectorSearchResult",
    ),
    "ModelVectorSearchResults": (
        "omnibase_core.models.vector.model_vector_search_results",
        "ModelVectorSearchResults",
    ),
    "ModelVectorStoreResult": (
        "omnibase_core.models.vector.model_vector_store_result",
        "ModelVectorStoreResult",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        # A submodule that the old eager __init__ loaded as a side effect
        # stays reachable as ``package.submodule``: import it on first access.
        if (
            name.isidentifier()
            and not name.startswith("__")
            and importlib.util.find_spec(f"{__name__}.{name}") is not None
        ):
            return importlib.import_module(f"{__name__}.{name}")
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
