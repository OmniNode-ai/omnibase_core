"""
Model for dependency graph representation and analysis.

This model provides mathematical graph structures for tracking
work ticket dependencies and enabling topological sorting
for intelligent work coordination.
"""

import json
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class DependencyType(str, Enum):
    """Types of dependencies between work items."""

    BLOCKS = "blocks"  # This item blocks the dependent item
    REQUIRES = "requires"  # This item requires the dependency to be completed
    FOLLOWS = "follows"  # This item should follow the dependency (softer constraint)
    CONFLICTS = (
        "conflicts"  # This item conflicts with the dependency (mutual exclusion)
    )
    ENHANCES = "enhances"  # This item enhances the dependency (optional)


class DependencyStatus(str, Enum):
    """Status of a dependency relationship."""

    PENDING = "pending"
    SATISFIED = "satisfied"
    VIOLATED = "violated"
    IGNORED = "ignored"


class ModelDependencyEdge(BaseModel):
    """Edge in the dependency graph representing a relationship."""

    source_id: str = Field(description="ID of the source work item")
    target_id: str = Field(
        description="ID of the target work item that depends on source",
    )
    dependency_type: DependencyType = Field(
        description="Type of dependency relationship",
    )
    status: DependencyStatus = Field(
        default=DependencyStatus.PENDING,
        description="Current status of the dependency",
    )
    weight: float = Field(
        default=1.0,
        description="Weight of the dependency (priority/importance)",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When the dependency was created",
    )
    resolved_at: datetime | None = Field(
        default=None,
        description="When the dependency was resolved",
    )
    description: str | None = Field(
        default=None,
        description="Human-readable description of the dependency",
    )
    metadata: dict[str, str] | None = Field(
        default=None,
        description="Additional metadata for the dependency",
    )

    @property
    def is_satisfied(self) -> bool:
        """Check if dependency is satisfied."""
        return self.status == DependencyStatus.SATISFIED

    @property
    def is_blocking(self) -> bool:
        """Check if this is a blocking dependency."""
        return self.dependency_type in [DependencyType.BLOCKS, DependencyType.REQUIRES]

    def satisfy(self) -> None:
        """Mark dependency as satisfied."""
        self.status = DependencyStatus.SATISFIED
        self.resolved_at = datetime.now()

    def violate(self, reason: str | None = None) -> None:
        """Mark dependency as violated."""
        self.status = DependencyStatus.VIOLATED
        if reason and self.metadata:
            self.metadata["violation_reason"] = reason


class ModelDependencyNode(BaseModel):
    """Node in the dependency graph representing a work item."""

    node_id: str = Field(description="Unique identifier for the work item")
    title: str = Field(description="Human-readable title of the work item")
    status: str = Field(description="Current status of the work item")
    priority: float = Field(
        default=1.0,
        description="Priority of the work item (higher = more important)",
    )
    estimated_duration: float | None = Field(
        default=None,
        description="Estimated duration in hours",
    )
    assigned_agent: str | None = Field(
        default=None,
        description="Agent assigned to this work item",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When the work item was created",
    )
    started_at: datetime | None = Field(
        default=None,
        description="When work on this item started",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="When the work item was completed",
    )
    dependencies_in: list[str] = Field(
        default_factory=list,
        description="List of edge IDs for incoming dependencies",
    )
    dependencies_out: list[str] = Field(
        default_factory=list,
        description="List of edge IDs for outgoing dependencies",
    )
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    metadata: dict[str, str] | None = Field(
        default=None,
        description="Additional metadata for the node",
    )

    @property
    def is_completed(self) -> bool:
        """Check if work item is completed."""
        return self.completed_at is not None

    @property
    def is_in_progress(self) -> bool:
        """Check if work item is in progress."""
        return self.started_at is not None and self.completed_at is None

    @property
    def is_assigned(self) -> bool:
        """Check if work item is assigned to an agent."""
        return self.assigned_agent is not None

    def start_work(self, agent_id: str | None = None) -> None:
        """Mark work item as started."""
        self.started_at = datetime.now()
        if agent_id:
            self.assigned_agent = agent_id

    def complete_work(self) -> None:
        """Mark work item as completed."""
        self.completed_at = datetime.now()


class ModelTopologicalSort(BaseModel):
    """Result of topological sorting operation."""

    sorted_nodes: list[str] = Field(description="Nodes in topologically sorted order")
    cycles: list[list[str]] = Field(
        default_factory=list,
        description="Any cycles detected in the graph",
    )
    levels: list[list[str]] = Field(
        default_factory=list,
        description="Nodes grouped by dependency levels",
    )
    critical_path: list[str] = Field(
        default_factory=list,
        description="Critical path through the dependency graph",
    )
    parallel_groups: list[list[str]] = Field(
        default_factory=list,
        description="Groups of nodes that can be executed in parallel",
    )
    sort_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the sort was performed",
    )
    algorithm_used: str = Field(
        default="kahn",
        description="Algorithm used for sorting",
    )

    @property
    def has_cycles(self) -> bool:
        """Check if cycles were detected."""
        return len(self.cycles) > 0

    @property
    def is_valid(self) -> bool:
        """Check if sort result is valid (no cycles)."""
        return not self.has_cycles

    @property
    def max_parallelism(self) -> int:
        """Get maximum parallelism possible."""
        return (
            max(len(group) for group in self.parallel_groups)
            if self.parallel_groups
            else 1
        )


class ModelDependencyGraph(BaseModel):
    """Complete dependency graph with nodes and edges."""

    graph_id: str = Field(description="Unique identifier for the graph")
    name: str = Field(description="Human-readable name for the graph")
    nodes: dict[str, ModelDependencyNode] = Field(
        default_factory=dict,
        description="Nodes in the graph (node_id -> node)",
    )
    edges: dict[str, ModelDependencyEdge] = Field(
        default_factory=dict,
        description="Edges in the graph (edge_id -> edge)",
    )
    adjacency_list: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Adjacency list representation (node_id -> [dependent_node_ids])",
    )
    reverse_adjacency_list: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Reverse adjacency list (node_id -> [dependency_node_ids])",
    )
    in_degree: dict[str, int] = Field(
        default_factory=dict,
        description="In-degree count for each node",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When the graph was created",
    )
    last_modified: datetime = Field(
        default_factory=datetime.now,
        description="When the graph was last modified",
    )
    last_sort: ModelTopologicalSort | None = Field(
        default=None,
        description="Result of last topological sort",
    )
    metadata: dict[str, str] | None = Field(
        default=None,
        description="Additional metadata for the graph",
    )

    @property
    def node_count(self) -> int:
        """Get number of nodes in graph."""
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        """Get number of edges in graph."""
        return len(self.edges)

    @property
    def is_empty(self) -> bool:
        """Check if graph is empty."""
        return len(self.nodes) == 0

    @property
    def has_cycles(self) -> bool:
        """Check if graph has cycles (based on last sort)."""
        return self.last_sort is not None and self.last_sort.has_cycles

    def add_node(self, node: ModelDependencyNode) -> None:
        """Add a node to the graph."""
        self.nodes[node.node_id] = node
        if node.node_id not in self.adjacency_list:
            self.adjacency_list[node.node_id] = []
        if node.node_id not in self.reverse_adjacency_list:
            self.reverse_adjacency_list[node.node_id] = []
        if node.node_id not in self.in_degree:
            self.in_degree[node.node_id] = 0
        self.last_modified = datetime.now()

    def remove_node(self, node_id: str) -> bool:
        """Remove a node and all its edges from the graph."""
        if node_id not in self.nodes:
            return False

        # Remove all edges involving this node
        edges_to_remove = []
        for edge_id, edge in self.edges.items():
            if node_id in (edge.source_id, edge.target_id):
                edges_to_remove.append(edge_id)

        for edge_id in edges_to_remove:
            self.remove_edge(edge_id)

        # Remove node
        del self.nodes[node_id]
        self.adjacency_list.pop(node_id, None)
        self.reverse_adjacency_list.pop(node_id, None)
        self.in_degree.pop(node_id, None)
        self.last_modified = datetime.now()
        return True

    def add_edge(self, edge: ModelDependencyEdge) -> str:
        """Add an edge to the graph and return edge ID."""
        edge_id = f"{edge.source_id}_{edge.target_id}_{edge.dependency_type}"
        self.edges[edge_id] = edge

        # Update adjacency lists
        if edge.source_id not in self.adjacency_list:
            self.adjacency_list[edge.source_id] = []
        if edge.target_id not in self.adjacency_list:
            self.adjacency_list[edge.target_id] = []
        if edge.source_id not in self.reverse_adjacency_list:
            self.reverse_adjacency_list[edge.source_id] = []
        if edge.target_id not in self.reverse_adjacency_list:
            self.reverse_adjacency_list[edge.target_id] = []

        # For blocking dependencies, target depends on source
        if edge.is_blocking:
            if edge.target_id not in self.adjacency_list[edge.source_id]:
                self.adjacency_list[edge.source_id].append(edge.target_id)
            if edge.source_id not in self.reverse_adjacency_list[edge.target_id]:
                self.reverse_adjacency_list[edge.target_id].append(edge.source_id)

            # Update in-degree
            self.in_degree[edge.target_id] = self.in_degree.get(edge.target_id, 0) + 1

        # Update node edge lists
        if edge.source_id in self.nodes:
            self.nodes[edge.source_id].dependencies_out.append(edge_id)
        if edge.target_id in self.nodes:
            self.nodes[edge.target_id].dependencies_in.append(edge_id)

        self.last_modified = datetime.now()
        return edge_id

    def remove_edge(self, edge_id: str) -> bool:
        """Remove an edge from the graph."""
        if edge_id not in self.edges:
            return False

        edge = self.edges[edge_id]

        # Update adjacency lists
        if edge.is_blocking:
            if edge.target_id in self.adjacency_list.get(edge.source_id, []):
                self.adjacency_list[edge.source_id].remove(edge.target_id)
            if edge.source_id in self.reverse_adjacency_list.get(edge.target_id, []):
                self.reverse_adjacency_list[edge.target_id].remove(edge.source_id)

            # Update in-degree
            self.in_degree[edge.target_id] = max(
                0,
                self.in_degree.get(edge.target_id, 0) - 1,
            )

        # Update node edge lists
        if edge.source_id in self.nodes:
            if edge_id in self.nodes[edge.source_id].dependencies_out:
                self.nodes[edge.source_id].dependencies_out.remove(edge_id)
        if edge.target_id in self.nodes:
            if edge_id in self.nodes[edge.target_id].dependencies_in:
                self.nodes[edge.target_id].dependencies_in.remove(edge_id)

        del self.edges[edge_id]
        self.last_modified = datetime.now()
        return True

    def get_node_dependencies(self, node_id: str) -> list[str]:
        """Get list of nodes that this node depends on."""
        return self.reverse_adjacency_list.get(node_id, [])

    def get_node_dependents(self, node_id: str) -> list[str]:
        """Get list of nodes that depend on this node."""
        return self.adjacency_list.get(node_id, [])

    def get_ready_nodes(self) -> list[str]:
        """Get nodes that are ready for execution (no pending dependencies)."""
        ready_nodes = []
        for node_id, node in self.nodes.items():
            if not node.is_completed and not node.is_in_progress:
                # Check if all dependencies are satisfied
                dependencies = self.get_node_dependencies(node_id)
                if all(
                    self.nodes[dep_id].is_completed
                    for dep_id in dependencies
                    if dep_id in self.nodes
                ):
                    ready_nodes.append(node_id)
        return ready_nodes

    def get_blocked_nodes(self) -> list[str]:
        """Get nodes that are blocked by pending dependencies."""
        blocked_nodes = []
        for node_id, node in self.nodes.items():
            if not node.is_completed and not node.is_in_progress:
                dependencies = self.get_node_dependencies(node_id)
                if any(
                    not self.nodes[dep_id].is_completed
                    for dep_id in dependencies
                    if dep_id in self.nodes
                ):
                    blocked_nodes.append(node_id)
        return blocked_nodes

    def mark_node_completed(self, node_id: str) -> list[str]:
        """Mark a node as completed and return newly ready nodes."""
        if node_id in self.nodes:
            self.nodes[node_id].complete_work()

            # Satisfy all outgoing edges
            for edge_id in self.nodes[node_id].dependencies_out:
                if edge_id in self.edges:
                    self.edges[edge_id].satisfy()

            self.last_modified = datetime.now()

            # Return newly ready nodes
            return self.get_ready_nodes()
        return []

    def get_critical_path(self) -> list[str]:
        """Calculate critical path through the dependency graph."""
        # Critical path calculation using topological sort
        if not self.nodes:
            return []

        # Find nodes with longest dependency chains
        max_depth = 0
        critical_nodes = []

        def calculate_depth(node_id: str, visited: set[str]) -> int:
            if node_id in visited:
                return 0  # Cycle detection

            visited.add(node_id)
            dependencies = self.get_node_dependencies(node_id)
            if not dependencies:
                visited.remove(node_id)
                return 1

            max_dep_depth = max(
                calculate_depth(dep_id, visited)
                for dep_id in dependencies
                if dep_id in self.nodes
            )
            visited.remove(node_id)
            return max_dep_depth + 1

        for node_id in self.nodes:
            depth = calculate_depth(node_id, set())
            if depth > max_depth:
                max_depth = depth
                critical_nodes = [node_id]
            elif depth == max_depth:
                critical_nodes.append(node_id)

        return critical_nodes

    def detect_cycles(self) -> list[list[str]]:
        """Detect cycles in the dependency graph using DFS."""
        white = set(self.nodes.keys())  # Unvisited
        gray = set()  # Currently visiting
        black = set()  # Completed
        cycles = []

        def dfs(node_id: str, path: list[str]) -> None:
            if node_id in gray:
                # Found a cycle
                cycle_start = path.index(node_id)
                cycle = path[cycle_start:] + [node_id]
                cycles.append(cycle)
                return

            if node_id in black:
                return

            white.discard(node_id)
            gray.add(node_id)
            path.append(node_id)

            for dependent in self.adjacency_list.get(node_id, []):
                dfs(dependent, path.copy())

            gray.discard(node_id)
            black.add(node_id)

        while white:
            start_node = next(iter(white))
            dfs(start_node, [])

        return cycles

    def to_dict(self) -> dict:
        """Convert graph to dictionary representation."""
        # Custom graph serialization using model_dump() for nodes and edges
        return {
            "graph_id": self.graph_id,
            "name": self.name,
            "nodes": {
                node_id: node.model_dump() for node_id, node in self.nodes.items()
            },
            "edges": {
                edge_id: edge.model_dump() for edge_id, edge in self.edges.items()
            },
            "adjacency_list": self.adjacency_list,
            "reverse_adjacency_list": self.reverse_adjacency_list,
            "in_degree": self.in_degree,
            "created_at": self.created_at.isoformat(),
            "last_modified": self.last_modified.isoformat(),
            "last_sort": self.last_sort.model_dump() if self.last_sort else None,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        """Convert graph to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "ModelDependencyGraph":
        """Create graph from dictionary representation."""
        # Convert node and edge data back to models
        nodes = {
            node_id: ModelDependencyNode(**node_data)
            for node_id, node_data in data.get("nodes", {}).items()
        }
        edges = {
            edge_id: ModelDependencyEdge(**edge_data)
            for edge_id, edge_data in data.get("edges", {}).items()
        }

        graph = cls(
            graph_id=data["graph_id"],
            name=data["name"],
            nodes=nodes,
            edges=edges,
            adjacency_list=data.get("adjacency_list", {}),
            reverse_adjacency_list=data.get("reverse_adjacency_list", {}),
            in_degree=data.get("in_degree", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_modified=datetime.fromisoformat(data["last_modified"]),
            metadata=data.get("metadata"),
        )

        if data.get("last_sort"):
            graph.last_sort = ModelTopologicalSort(**data["last_sort"])

        return graph

    @classmethod
    def from_json(cls, json_str: str) -> "ModelDependencyGraph":
        """Create graph from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
