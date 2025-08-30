"""
Graph models for OmniMemory Codebase Graph Integration.

This package contains models for representing the codebase as a knowledge graph
with nodes (files, symbols, documentation) and edges (relationships between them).
"""

from .model_codebase_graph import (ModelCodebaseGraph,
                                   ModelCodebaseGraphConfig,
                                   ModelCodebaseGraphMetrics,
                                   ModelGraphBuildResult,
                                   ModelGraphUpdateEvent)
from .model_graph_edge import (GraphEdge, ModelCallEdge, ModelDefinitionEdge,
                               ModelDocumentationEdge, ModelGraphEdge,
                               ModelImportEdge, ModelInheritanceEdge,
                               ModelReferenceEdge, ModelUsageEdge)
from .model_graph_node import (GraphNode, ModelDocumentationNode,
                               ModelFileNode, ModelGraphNodeBase,
                               ModelSymbolNode)

__all__ = [
    # Node models
    "ModelGraphNodeBase",
    "ModelFileNode",
    "ModelSymbolNode",
    "ModelDocumentationNode",
    "GraphNode",
    # Edge models
    "ModelGraphEdge",
    "ModelImportEdge",
    "ModelDefinitionEdge",
    "ModelUsageEdge",
    "ModelInheritanceEdge",
    "ModelCallEdge",
    "ModelDocumentationEdge",
    "ModelReferenceEdge",
    "GraphEdge",
    # Main graph models
    "ModelCodebaseGraphMetrics",
    "ModelCodebaseGraphConfig",
    "ModelCodebaseGraph",
    "ModelGraphBuildResult",
    "ModelGraphUpdateEvent",
]
