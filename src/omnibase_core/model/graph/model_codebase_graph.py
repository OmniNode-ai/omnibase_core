"""
Main codebase graph model for OmniMemory Codebase Graph Integration.

This model represents the complete codebase knowledge graph with nodes and edges,
and provides methods for graph operations and queries.
"""

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field

from .model_graph_edge import GraphEdge
from .model_graph_node import GraphNode, ModelFileNode, ModelSymbolNode


class ModelChangeMetadata(BaseModel):
    """Metadata for graph change events."""

    file_size_bytes: int | None = Field(
        None,
        description="Size of the changed file in bytes",
    )
    modification_type: str | None = Field(
        None,
        description="Type of modification: content/permissions/metadata",
    )
    line_count_delta: int | None = Field(None, description="Change in line count")
    symbol_count_delta: int | None = Field(
        None,
        description="Change in symbol count",
    )
    checksum_before: str | None = Field(
        None,
        description="File checksum before change",
    )
    checksum_after: str | None = Field(
        None,
        description="File checksum after change",
    )
    user_agent: str | None = Field(
        None,
        description="User agent that triggered the change",
    )
    commit_hash: str | None = Field(
        None,
        description="Git commit hash if applicable",
    )


class ModelCodebaseGraphMetrics(BaseModel):
    """Metrics about the codebase graph."""

    total_nodes: int = Field(0, description="Total number of nodes")
    total_edges: int = Field(0, description="Total number of edges")
    file_nodes: int = Field(0, description="Number of file nodes")
    symbol_nodes: int = Field(0, description="Number of symbol nodes")
    documentation_nodes: int = Field(0, description="Number of documentation nodes")

    # Edge type counts
    import_edges: int = Field(0, description="Number of import edges")
    definition_edges: int = Field(0, description="Number of definition edges")
    usage_edges: int = Field(0, description="Number of usage edges")
    inheritance_edges: int = Field(0, description="Number of inheritance edges")
    call_edges: int = Field(0, description="Number of call edges")
    documentation_edges: int = Field(0, description="Number of documentation edges")

    # Graph properties
    connected_components: int = Field(0, description="Number of connected components")
    average_degree: float = Field(0.0, description="Average node degree")
    max_depth: int = Field(0, description="Maximum depth of dependency chains")

    last_updated: datetime = Field(default_factory=datetime.utcnow)


class ModelCodebaseGraphConfig(BaseModel):
    """Configuration for codebase graph building and maintenance."""

    # File discovery settings
    include_patterns: list[str] = Field(
        default=["**/*.py", "**/*.yaml", "**/*.yml", "**/*.md", "**/*.json"],
        description="File patterns to include in graph",
    )
    exclude_patterns: list[str] = Field(
        default=["**/__pycache__/**", "**/.git/**", "**/node_modules/**"],
        description="File patterns to exclude from graph",
    )

    # Graph building settings
    max_file_size_mb: int = Field(10, description="Maximum file size to process (MB)")
    enable_embeddings: bool = Field(True, description="Whether to generate embeddings")
    embedding_model: str = Field(
        "all-MiniLM-L6-v2",
        description="Model for generating embeddings",
    )

    # OnexTree integration
    use_onextree_validation: bool = Field(
        True,
        description="Use OnexTree for file structure validation",
    )
    enable_metadata_stamping: bool = Field(True, description="Enable metadata stamping")

    # Real-time update settings
    enable_real_time_updates: bool = Field(
        True,
        description="Enable real-time graph updates",
    )
    batch_update_interval_seconds: int = Field(30, description="Batch update interval")

    # Vector search settings
    vector_dimension: int = Field(384, description="Dimension of embedding vectors")
    similarity_threshold: float = Field(
        0.7,
        description="Similarity threshold for related nodes",
    )


class ModelCodebaseGraph(BaseModel):
    """Main codebase graph model containing all nodes and edges."""

    graph_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique graph identifier",
    )
    version: str = Field("1.0.0", description="Graph schema version")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Graph content
    nodes: dict[str, GraphNode] = Field(
        default_factory=dict,
        description="All nodes in the graph",
    )
    edges: dict[str, GraphEdge] = Field(
        default_factory=dict,
        description="All edges in the graph",
    )

    # Index structures for efficient queries
    node_type_index: dict[str, set[str]] = Field(
        default_factory=dict,
        description="Index of node IDs by type",
    )
    edge_type_index: dict[str, set[str]] = Field(
        default_factory=dict,
        description="Index of edge IDs by type",
    )
    file_path_index: dict[str, str] = Field(
        default_factory=dict,
        description="Index from file path to node ID",
    )
    symbol_name_index: dict[str, set[str]] = Field(
        default_factory=dict,
        description="Index from symbol name to node IDs",
    )

    # Graph metadata
    root_path: Path | None = Field(None, description="Root path of the codebase")
    config: ModelCodebaseGraphConfig = Field(default_factory=ModelCodebaseGraphConfig)
    metrics: ModelCodebaseGraphMetrics = Field(
        default_factory=ModelCodebaseGraphMetrics,
    )

    # OnexTree integration metadata
    onextree_last_sync: datetime | None = Field(
        None,
        description="Last sync with OnexTree",
    )
    stamper_last_sync: datetime | None = Field(
        None,
        description="Last sync with metadata stamper",
    )

    def add_node(self, node: GraphNode) -> None:
        """Add a node to the graph and update indices."""
        self.nodes[node.node_id] = node

        # Update type index
        node_type = node.node_type
        if node_type not in self.node_type_index:
            self.node_type_index[node_type] = set()
        self.node_type_index[node_type].add(node.node_id)

        # Update file path index for file nodes
        if isinstance(node, ModelFileNode):
            self.file_path_index[str(node.file_path)] = node.node_id

        # Update symbol name index for symbol nodes
        if isinstance(node, ModelSymbolNode):
            symbol_name = node.symbol_name
            if symbol_name not in self.symbol_name_index:
                self.symbol_name_index[symbol_name] = set()
            self.symbol_name_index[symbol_name].add(node.node_id)

        self.updated_at = datetime.utcnow()

    def add_edge(self, edge: GraphEdge) -> None:
        """Add an edge to the graph and update indices."""
        self.edges[edge.edge_id] = edge

        # Update type index
        edge_type = edge.edge_type
        if edge_type not in self.edge_type_index:
            self.edge_type_index[edge_type] = set()
        self.edge_type_index[edge_type].add(edge.edge_id)

        self.updated_at = datetime.utcnow()

    def get_nodes_by_type(self, node_type: str) -> list[GraphNode]:
        """Get all nodes of a specific type."""
        node_ids = self.node_type_index.get(node_type, set())
        return [self.nodes[node_id] for node_id in node_ids if node_id in self.nodes]

    def get_edges_by_type(self, edge_type: str) -> list[GraphEdge]:
        """Get all edges of a specific type."""
        edge_ids = self.edge_type_index.get(edge_type, set())
        return [self.edges[edge_id] for edge_id in edge_ids if edge_id in self.edges]

    def get_file_node(self, file_path: str | Path) -> ModelFileNode | None:
        """Get file node by path."""
        node_id = self.file_path_index.get(str(file_path))
        if node_id and node_id in self.nodes:
            node = self.nodes[node_id]
            if isinstance(node, ModelFileNode):
                return node
        return None

    def get_symbol_nodes(self, symbol_name: str) -> list[ModelSymbolNode]:
        """Get all symbol nodes with the given name."""
        node_ids = self.symbol_name_index.get(symbol_name, set())
        result = []
        for node_id in node_ids:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                if isinstance(node, ModelSymbolNode):
                    result.append(node)
        return result

    def get_connected_nodes(
        self,
        node_id: str,
        edge_types: list[str] | None = None,
    ) -> list[GraphNode]:
        """Get nodes connected to the given node, optionally filtered by edge types."""
        connected_node_ids = set()

        for edge in self.edges.values():
            if edge_types and edge.edge_type not in edge_types:
                continue

            if edge.source_node_id == node_id:
                connected_node_ids.add(edge.target_node_id)
            elif edge.target_node_id == node_id:
                connected_node_ids.add(edge.source_node_id)

        return [self.nodes[nid] for nid in connected_node_ids if nid in self.nodes]

    def update_metrics(self) -> None:
        """Update graph metrics."""
        self.metrics.total_nodes = len(self.nodes)
        self.metrics.total_edges = len(self.edges)

        # Count nodes by type
        self.metrics.file_nodes = len(self.node_type_index.get("file", set()))
        self.metrics.symbol_nodes = len(self.node_type_index.get("symbol", set()))
        self.metrics.documentation_nodes = len(
            self.node_type_index.get("documentation", set()),
        )

        # Count edges by type
        self.metrics.import_edges = len(self.edge_type_index.get("import", set()))
        self.metrics.definition_edges = len(self.edge_type_index.get("defines", set()))
        self.metrics.usage_edges = len(self.edge_type_index.get("uses", set()))
        self.metrics.inheritance_edges = len(
            self.edge_type_index.get("inherits", set()),
        )
        self.metrics.call_edges = len(self.edge_type_index.get("calls", set()))
        self.metrics.documentation_edges = len(
            self.edge_type_index.get("documents", set()),
        )

        # Calculate average degree
        if self.metrics.total_nodes > 0:
            self.metrics.average_degree = (
                self.metrics.total_edges * 2
            ) / self.metrics.total_nodes

        self.metrics.last_updated = datetime.utcnow()

    def to_networkx(self) -> "networkx.DiGraph":
        """Convert to NetworkX graph for advanced analysis."""
        try:
            import networkx as nx
        except ImportError:
            msg = "NetworkX is required for graph analysis"
            raise ImportError(msg)

        G = nx.DiGraph()

        # Add nodes
        for node_id, node in self.nodes.items():
            G.add_node(node_id, **node.dict())

        # Add edges
        for edge in self.edges.values():
            G.add_edge(edge.source_node_id, edge.target_node_id, **edge.dict())

        return G


class ModelGraphBuildResult(BaseModel):
    """Result of building the codebase graph."""

    success: bool = Field(..., description="Whether graph building succeeded")
    graph: ModelCodebaseGraph | None = Field(None, description="The built graph")

    # Build statistics
    files_processed: int = Field(0, description="Number of files processed")
    files_skipped: int = Field(0, description="Number of files skipped")
    symbols_extracted: int = Field(0, description="Number of symbols extracted")
    relationships_found: int = Field(0, description="Number of relationships found")

    # Build metadata
    build_duration_seconds: float = Field(0.0, description="Time taken to build graph")
    onextree_integration_success: bool = Field(
        False,
        description="Whether OnexTree integration succeeded",
    )
    stamper_integration_success: bool = Field(
        False,
        description="Whether stamper integration succeeded",
    )

    # Error information
    errors: list[str] = Field(
        default_factory=list,
        description="Errors encountered during build",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Warnings generated during build",
    )

    build_timestamp: datetime = Field(default_factory=datetime.utcnow)


class ModelGraphUpdateEvent(BaseModel):
    """Event representing an update to the codebase graph."""

    event_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique event identifier",
    )
    event_type: str = Field(..., description="Type of update: add/update/delete")
    node_id: str | None = Field(None, description="ID of affected node")
    edge_id: str | None = Field(None, description="ID of affected edge")

    # Change details
    file_path: Path | None = Field(
        None,
        description="File path that triggered the update",
    )
    change_type: str = Field(
        ...,
        description="Type of change: file_created/file_modified/file_deleted",
    )
    change_metadata: ModelChangeMetadata = Field(
        default_factory=ModelChangeMetadata,
        description="Additional change metadata",
    )

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processed: bool = Field(False, description="Whether the update has been processed")
