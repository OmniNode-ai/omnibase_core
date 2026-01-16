"""Vector store domain models for ONEX SPI handler protocols.

This module provides typed Pydantic models for vector store operations,
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

# Enums
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
from omnibase_core.models.vector.model_vector_index_config import ModelVectorIndexConfig
from omnibase_core.models.vector.model_vector_index_result import ModelVectorIndexResult
from omnibase_core.models.vector.model_vector_metadata_filter import (
    ModelVectorMetadataFilter,
)
from omnibase_core.models.vector.model_vector_search_result import (
    ModelVectorSearchResult,
)
from omnibase_core.models.vector.model_vector_search_results import (
    ModelVectorSearchResults,
)
from omnibase_core.models.vector.model_vector_store_result import ModelVectorStoreResult

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
