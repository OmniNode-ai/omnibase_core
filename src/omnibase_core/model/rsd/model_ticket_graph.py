#!/usr/bin/env python3
"""
Ticket graph model - ONEX Standards Compliant.

Model for the complete ticket dependency graph.
"""

from datetime import datetime
from typing import Dict, List, Optional, Set

from pydantic import BaseModel, Field

from .model_ticket_cluster import ModelTicketCluster
from .model_ticket_edge import ModelTicketEdge
from .model_ticket_node import ModelTicketNode


class ModelTicketGraph(BaseModel):
    """
    Model for the complete ticket dependency graph.

    Represents all tickets and their relationships as a directed graph.
    """

    nodes: Dict[str, ModelTicketNode] = Field(
        default_factory=dict, description="Map of ticket ID to node"
    )

    edges: List[ModelTicketEdge] = Field(
        default_factory=list, description="All edges in the graph"
    )

    clusters: Dict[str, ModelTicketCluster] = Field(
        default_factory=dict, description="Map of cluster ID to cluster"
    )

    critical_paths: List[List[str]] = Field(
        default_factory=list, description="List of critical paths (ticket ID sequences)"
    )

    bottleneck_nodes: List[str] = Field(
        default_factory=list, description="Ticket IDs that are bottlenecks"
    )

    cycle_nodes: Set[str] = Field(
        default_factory=set, description="Ticket IDs involved in cycles"
    )

    last_updated: datetime = Field(
        default_factory=datetime.now, description="When graph was last updated"
    )

    graph_metrics: Dict[str, float] = Field(
        default_factory=dict,
        description="Graph-level metrics (complexity, density, etc)",
    )

    class Config:
        """Pydantic model configuration."""

        validate_assignment = True

    def add_node(self, node: ModelTicketNode) -> None:
        """Add a node to the graph."""
        self.nodes[node.ticket_id] = node
        self.last_updated = datetime.now()

    def add_edge(self, edge: ModelTicketEdge) -> None:
        """Add an edge to the graph."""
        self.edges.append(edge)

        # Update node relationships
        if edge.source_ticket_id in self.nodes:
            self.nodes[edge.source_ticket_id].outgoing_edges.append(
                edge.target_ticket_id
            )

        if edge.target_ticket_id in self.nodes:
            self.nodes[edge.target_ticket_id].incoming_edges.append(
                edge.source_ticket_id
            )

        self.last_updated = datetime.now()

    def remove_node(self, ticket_id: str) -> None:
        """Remove a node and all its edges."""
        if ticket_id not in self.nodes:
            return

        # Remove from nodes
        del self.nodes[ticket_id]

        # Remove all edges involving this node
        self.edges = [
            edge
            for edge in self.edges
            if edge.source_ticket_id != ticket_id and edge.target_ticket_id != ticket_id
        ]

        # Update other nodes' edge lists
        for node in self.nodes.values():
            node.incoming_edges = [
                edge_id for edge_id in node.incoming_edges if edge_id != ticket_id
            ]
            node.outgoing_edges = [
                edge_id for edge_id in node.outgoing_edges if edge_id != ticket_id
            ]

        # Remove from clusters
        for cluster in self.clusters.values():
            if ticket_id in cluster.ticket_ids:
                cluster.ticket_ids.remove(ticket_id)

        # Remove from special lists
        self.bottleneck_nodes = [
            node_id for node_id in self.bottleneck_nodes if node_id != ticket_id
        ]
        self.cycle_nodes.discard(ticket_id)

        self.last_updated = datetime.now()

    def get_neighbors(self, ticket_id: str, direction: str = "both") -> List[str]:
        """
        Get neighboring nodes.

        Args:
            ticket_id: Node to get neighbors for
            direction: 'in', 'out', or 'both'

        Returns:
            List of neighbor ticket IDs
        """
        if ticket_id not in self.nodes:
            return []

        node = self.nodes[ticket_id]

        if direction == "in":
            return node.incoming_edges
        elif direction == "out":
            return node.outgoing_edges
        else:
            return list(set(node.incoming_edges + node.outgoing_edges))

    def get_subgraph(self, ticket_ids: List[str]) -> "ModelTicketGraph":
        """
        Extract a subgraph containing only specified tickets.

        Args:
            ticket_ids: Tickets to include

        Returns:
            New graph with subset of nodes/edges
        """
        subgraph = ModelTicketGraph()

        # Add nodes
        for ticket_id in ticket_ids:
            if ticket_id in self.nodes:
                subgraph.add_node(self.nodes[ticket_id])

        # Add edges between included nodes
        for edge in self.edges:
            if (
                edge.source_ticket_id in ticket_ids
                and edge.target_ticket_id in ticket_ids
            ):
                subgraph.add_edge(edge)

        return subgraph

    def calculate_metrics(self) -> None:
        """Calculate graph-level metrics."""
        node_count = len(self.nodes)
        edge_count = len(self.edges)

        # Basic metrics
        self.graph_metrics["node_count"] = float(node_count)
        self.graph_metrics["edge_count"] = float(edge_count)

        # Density (0-1)
        if node_count > 1:
            max_edges = node_count * (node_count - 1)
            self.graph_metrics["density"] = (
                edge_count / max_edges if max_edges > 0 else 0.0
            )
        else:
            self.graph_metrics["density"] = 0.0

        # Clustering coefficient (simplified)
        cluster_count = len(self.clusters)
        self.graph_metrics["clustering"] = (
            cluster_count / node_count if node_count > 0 else 0.0
        )

        # Bottleneck ratio
        bottleneck_count = len(self.bottleneck_nodes)
        self.graph_metrics["bottleneck_ratio"] = (
            bottleneck_count / node_count if node_count > 0 else 0.0
        )

        # Cycle complexity
        cycle_count = len(self.cycle_nodes)
        self.graph_metrics["cycle_ratio"] = (
            cycle_count / node_count if node_count > 0 else 0.0
        )

        self.last_updated = datetime.now()

    def find_path(
        self, start_id: str, end_id: str, max_depth: int = 10
    ) -> Optional[List[str]]:
        """
        Find a path between two tickets using BFS.

        Args:
            start_id: Starting ticket
            end_id: Target ticket
            max_depth: Maximum search depth

        Returns:
            Path as list of ticket IDs, or None if no path
        """
        if start_id not in self.nodes or end_id not in self.nodes:
            return None

        if start_id == end_id:
            return [start_id]

        # BFS
        visited = {start_id}
        queue = [(start_id, [start_id])]
        depth = 0

        while queue and depth < max_depth:
            next_queue = []

            for current_id, path in queue:
                # Check outgoing edges
                for neighbor_id in self.nodes[current_id].outgoing_edges:
                    if neighbor_id == end_id:
                        return path + [end_id]

                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        next_queue.append((neighbor_id, path + [neighbor_id]))

            queue = next_queue
            depth += 1

        return None

    def get_dependency_distance(self, ticket_id: str, target_id: str) -> int:
        """
        Get minimum dependency distance between tickets.

        Args:
            ticket_id: Source ticket
            target_id: Target ticket

        Returns:
            Minimum distance, or -1 if no path
        """
        path = self.find_path(ticket_id, target_id)
        if path:
            return len(path) - 1
        return -1
