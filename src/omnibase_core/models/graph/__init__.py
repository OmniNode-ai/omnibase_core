"""Graph data structure models.

Type-safe graph models for orchestrator workflows and graph-based
data structures used in the ONEX framework.

This module provides two categories of models:

1. Workflow Visualization Models:
   - ModelGraphEdge: Edge in an orchestrator workflow graph
   - ModelGraphNode: Node in an orchestrator workflow graph

2. Database CRUD Models (for Neo4j, Memgraph, etc.):
   - ModelGraphDatabaseNode: Database node representation
   - ModelGraphRelationship: Database relationship representation
   - ModelGraphTraversalResult: Result of traversal operations
   - ModelGraphQueryResult: Result of database queries
   - ModelGraphBatchResult: Result of batch operations
   - ModelGraphDeleteResult: Result of deletion operations
   - ModelGraphHealthStatus: Database connection health
   - ModelGraphHandlerMetadata: Handler capabilities metadata
   - ModelGraphTraversalFilters: Traversal filter criteria
   - ModelGraphConnectionConfig: Connection configuration
"""

# Database CRUD models
from omnibase_core.models.graph.model_graph_batch_result import ModelGraphBatchResult
from omnibase_core.models.graph.model_graph_connection_config import (
    ModelGraphConnectionConfig,
)
from omnibase_core.models.graph.model_graph_database_node import ModelGraphDatabaseNode
from omnibase_core.models.graph.model_graph_delete_result import ModelGraphDeleteResult
from omnibase_core.models.graph.model_graph_edge import ModelGraphEdge
from omnibase_core.models.graph.model_graph_handler_metadata import (
    ModelGraphHandlerMetadata,
)
from omnibase_core.models.graph.model_graph_health_status import ModelGraphHealthStatus
from omnibase_core.models.graph.model_graph_node import ModelGraphNode
from omnibase_core.models.graph.model_graph_query_counters import (
    ModelGraphQueryCounters,
)
from omnibase_core.models.graph.model_graph_query_result import ModelGraphQueryResult
from omnibase_core.models.graph.model_graph_query_summary import ModelGraphQuerySummary
from omnibase_core.models.graph.model_graph_relationship import ModelGraphRelationship
from omnibase_core.models.graph.model_graph_traversal_filters import (
    ModelGraphTraversalFilters,
)
from omnibase_core.models.graph.model_graph_traversal_result import (
    ModelGraphTraversalResult,
)

__all__ = [
    # Workflow visualization models
    "ModelGraphEdge",
    "ModelGraphNode",
    # Database CRUD models
    "ModelGraphBatchResult",
    "ModelGraphConnectionConfig",
    "ModelGraphDatabaseNode",
    "ModelGraphDeleteResult",
    "ModelGraphHandlerMetadata",
    "ModelGraphHealthStatus",
    "ModelGraphQueryCounters",
    "ModelGraphQueryResult",
    "ModelGraphQuerySummary",
    "ModelGraphRelationship",
    "ModelGraphTraversalFilters",
    "ModelGraphTraversalResult",
]
