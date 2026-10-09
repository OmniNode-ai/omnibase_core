# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Graph data structure models.

Type-safe graph models for orchestrator workflows and graph-based
data structures used in the ONEX framework.

Two categories of models:

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

from __future__ import annotations

# Database CRUD models
import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.graph.model_graph_batch_result import (
        ModelGraphBatchResult,
    )
    from omnibase_core.models.graph.model_graph_connection_config import (
        ModelGraphConnectionConfig,
    )
    from omnibase_core.models.graph.model_graph_database_node import (
        ModelGraphDatabaseNode,
    )
    from omnibase_core.models.graph.model_graph_delete_result import (
        ModelGraphDeleteResult,
    )
    from omnibase_core.models.graph.model_graph_edge import ModelGraphEdge
    from omnibase_core.models.graph.model_graph_handler_metadata import (
        ModelGraphHandlerMetadata,
    )
    from omnibase_core.models.graph.model_graph_health_status import (
        ModelGraphHealthStatus,
    )
    from omnibase_core.models.graph.model_graph_node import ModelGraphNode
    from omnibase_core.models.graph.model_graph_query_counters import (
        ModelGraphQueryCounters,
    )
    from omnibase_core.models.graph.model_graph_query_result import (
        ModelGraphQueryResult,
    )
    from omnibase_core.models.graph.model_graph_query_summary import (
        ModelGraphQuerySummary,
    )
    from omnibase_core.models.graph.model_graph_relationship import (
        ModelGraphRelationship,
    )
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


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelGraphBatchResult": (
        "omnibase_core.models.graph.model_graph_batch_result",
        "ModelGraphBatchResult",
    ),
    "ModelGraphConnectionConfig": (
        "omnibase_core.models.graph.model_graph_connection_config",
        "ModelGraphConnectionConfig",
    ),
    "ModelGraphDatabaseNode": (
        "omnibase_core.models.graph.model_graph_database_node",
        "ModelGraphDatabaseNode",
    ),
    "ModelGraphDeleteResult": (
        "omnibase_core.models.graph.model_graph_delete_result",
        "ModelGraphDeleteResult",
    ),
    "ModelGraphEdge": ("omnibase_core.models.graph.model_graph_edge", "ModelGraphEdge"),
    "ModelGraphHandlerMetadata": (
        "omnibase_core.models.graph.model_graph_handler_metadata",
        "ModelGraphHandlerMetadata",
    ),
    "ModelGraphHealthStatus": (
        "omnibase_core.models.graph.model_graph_health_status",
        "ModelGraphHealthStatus",
    ),
    "ModelGraphNode": ("omnibase_core.models.graph.model_graph_node", "ModelGraphNode"),
    "ModelGraphQueryCounters": (
        "omnibase_core.models.graph.model_graph_query_counters",
        "ModelGraphQueryCounters",
    ),
    "ModelGraphQueryResult": (
        "omnibase_core.models.graph.model_graph_query_result",
        "ModelGraphQueryResult",
    ),
    "ModelGraphQuerySummary": (
        "omnibase_core.models.graph.model_graph_query_summary",
        "ModelGraphQuerySummary",
    ),
    "ModelGraphRelationship": (
        "omnibase_core.models.graph.model_graph_relationship",
        "ModelGraphRelationship",
    ),
    "ModelGraphTraversalFilters": (
        "omnibase_core.models.graph.model_graph_traversal_filters",
        "ModelGraphTraversalFilters",
    ),
    "ModelGraphTraversalResult": (
        "omnibase_core.models.graph.model_graph_traversal_result",
        "ModelGraphTraversalResult",
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
