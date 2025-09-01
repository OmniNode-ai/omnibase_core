"""
Dependency Resolution Utilities for Work Ticket Coordination.

This module provides utility functions for resolving dependencies,
performing topological sorting, and managing work ticket ordering
based on mathematical graph algorithms.
"""

import logging
from collections import defaultdict, deque

from omnibase_core.model.dependencies.model_dependency_graph import (
    ModelDependencyGraph,
    ModelTopologicalSort,
)


class CircularDependencyError(Exception):
    """Exception raised when circular dependency is detected."""


class DependencyResolutionError(Exception):
    """Exception raised when dependency resolution fails."""


class TopologicalSortError(Exception):
    """Exception raised when topological sort fails."""


class UtilityDependencyResolver:
    """Utility class for dependency resolution and graph algorithms."""

    def __init__(self):
        """Initialize the dependency resolver."""
        self.logger = logging.getLogger(__name__)

    def perform_topological_sort(
        self,
        graph: ModelDependencyGraph,
    ) -> ModelTopologicalSort:
        """
        Perform topological sorting using Kahn's algorithm.

        Args:
            graph: Dependency graph to sort

        Returns:
            Topological sort result with ordered nodes and metadata

        Raises:
            TopologicalSortError: If sort fails due to cycles
        """
        try:
            # Create working copies of data structures
            in_degree = dict(graph.in_degree)
            adjacency_list = {
                node_id: list(neighbors)
                for node_id, neighbors in graph.adjacency_list.items()
            }

            # Initialize queue with nodes having no dependencies
            queue = deque(
                [node_id for node_id, degree in in_degree.items() if degree == 0],
            )
            sorted_nodes = []
            levels = []
            current_level = []

            while queue:
                # Process all nodes at current level
                level_size = len(queue)
                current_level = []

                for _ in range(level_size):
                    node_id = queue.popleft()
                    sorted_nodes.append(node_id)
                    current_level.append(node_id)

                    # Remove edges from this node and update in-degrees
                    for neighbor in adjacency_list.get(node_id, []):
                        in_degree[neighbor] -= 1
                        if in_degree[neighbor] == 0:
                            queue.append(neighbor)

                if current_level:
                    levels.append(current_level[:])

            # Check for cycles
            cycles = []
            if len(sorted_nodes) != len(graph.nodes):
                # Find remaining nodes (part of cycles)
                remaining_nodes = set(graph.nodes.keys()) - set(sorted_nodes)
                cycles = self._detect_cycles_in_subgraph(graph, remaining_nodes)

            # Calculate parallel groups (nodes that can run simultaneously)
            parallel_groups = self._calculate_parallel_groups(graph, levels)

            # Calculate critical path
            critical_path = self._calculate_critical_path(graph, sorted_nodes)

            result = ModelTopologicalSort(
                sorted_nodes=sorted_nodes,
                cycles=cycles,
                levels=levels,
                critical_path=critical_path,
                parallel_groups=parallel_groups,
                algorithm_used="kahn",
            )

            # Update graph with sort result
            graph.last_sort = result

            return result

        except Exception as e:
            self.logger.exception(f"Topological sort failed: {e}")
            msg = f"Failed to perform topological sort: {e}"
            raise TopologicalSortError(msg)

    def detect_circular_dependencies(
        self,
        graph: ModelDependencyGraph,
    ) -> list[list[str]]:
        """
        Detect circular dependencies using DFS.

        Args:
            graph: Dependency graph to analyze

        Returns:
            List of cycles, where each cycle is a list of node IDs
        """
        try:
            white = set(graph.nodes.keys())  # Unvisited nodes
            gray = set()  # Currently being processed
            black = set()  # Completed processing
            cycles = []

            def dfs_visit(node_id: str, path: list[str]) -> None:
                if node_id in gray:
                    # Found back edge - cycle detected
                    try:
                        cycle_start = path.index(node_id)
                        cycle = path[cycle_start:] + [node_id]
                        cycles.append(cycle)
                    except ValueError:
                        # Node not in current path, add as potential cycle
                        cycles.append([*path, node_id])
                    return

                if node_id in black:
                    return

                white.discard(node_id)
                gray.add(node_id)

                # Visit all neighbors
                for neighbor in graph.adjacency_list.get(node_id, []):
                    dfs_visit(neighbor, [*path, node_id])

                gray.discard(node_id)
                black.add(node_id)

            # Process all unvisited nodes
            while white:
                start_node = next(iter(white))
                dfs_visit(start_node, [])

            return cycles

        except Exception as e:
            self.logger.exception(f"Cycle detection failed: {e}")
            return []

    def resolve_dependencies_for_node(
        self,
        graph: ModelDependencyGraph,
        node_id: str,
    ) -> list[str]:
        """
        Get resolved dependency order for a specific node.

        Args:
            graph: Dependency graph
            node_id: Target node to resolve dependencies for

        Returns:
            List of node IDs in dependency resolution order

        Raises:
            DependencyResolutionError: If resolution fails
        """
        try:
            if node_id not in graph.nodes:
                msg = f"Node {node_id} not found in graph"
                raise DependencyResolutionError(msg)

            resolved_order = []
            visited = set()
            temp_visited = set()

            def resolve_recursive(current_node: str) -> None:
                if current_node in temp_visited:
                    msg = f"Circular dependency detected involving {current_node}"
                    raise CircularDependencyError(
                        msg,
                    )

                if current_node in visited:
                    return

                temp_visited.add(current_node)

                # Resolve all dependencies first
                for dep_node in graph.get_node_dependencies(current_node):
                    if dep_node in graph.nodes:
                        resolve_recursive(dep_node)

                temp_visited.remove(current_node)
                visited.add(current_node)
                resolved_order.append(current_node)

            resolve_recursive(node_id)

            return resolved_order

        except CircularDependencyError:
            raise
        except Exception as e:
            self.logger.exception(
                f"Dependency resolution failed for node {node_id}: {e}",
            )
            msg = f"Failed to resolve dependencies: {e}"
            raise DependencyResolutionError(msg)

    def get_ready_work_items(self, graph: ModelDependencyGraph) -> list[str]:
        """
        Get work items that are ready for execution (all dependencies satisfied).

        Args:
            graph: Dependency graph to analyze

        Returns:
            List of node IDs ready for execution
        """
        try:
            ready_items = []

            for node_id, node in graph.nodes.items():
                if node.is_completed or node.is_in_progress:
                    continue

                # Check if all dependencies are satisfied
                dependencies = graph.get_node_dependencies(node_id)
                all_satisfied = True

                for dep_id in dependencies:
                    if dep_id in graph.nodes:
                        dep_node = graph.nodes[dep_id]
                        if not dep_node.is_completed:
                            all_satisfied = False
                            break
                    else:
                        # Dependency node not found - treat as unsatisfied
                        all_satisfied = False
                        break

                if all_satisfied:
                    ready_items.append(node_id)

            # Sort by priority if available
            ready_items.sort(key=lambda x: graph.nodes[x].priority, reverse=True)

            return ready_items

        except Exception as e:
            self.logger.exception(f"Failed to get ready work items: {e}")
            return []

    def calculate_work_levels(
        self,
        graph: ModelDependencyGraph,
    ) -> dict[int, list[str]]:
        """
        Calculate work levels for parallel execution planning.

        Args:
            graph: Dependency graph to analyze

        Returns:
            Dictionary mapping level number to list of node IDs
        """
        try:
            levels = {}
            node_levels = {}

            def calculate_level(node_id: str, visited: set[str]) -> int:
                if node_id in visited:
                    return 0  # Cycle detected - assign level 0

                if node_id in node_levels:
                    return node_levels[node_id]

                visited.add(node_id)

                dependencies = graph.get_node_dependencies(node_id)
                if not dependencies:
                    level = 0
                else:
                    max_dep_level = max(
                        calculate_level(dep_id, visited)
                        for dep_id in dependencies
                        if dep_id in graph.nodes
                    )
                    level = max_dep_level + 1

                visited.remove(node_id)
                node_levels[node_id] = level

                if level not in levels:
                    levels[level] = []
                levels[level].append(node_id)

                return level

            # Calculate levels for all nodes
            for node_id in graph.nodes:
                calculate_level(node_id, set())

            return levels

        except Exception as e:
            self.logger.exception(f"Failed to calculate work levels: {e}")
            return {}

    def optimize_work_assignment(
        self,
        graph: ModelDependencyGraph,
        agent_count: int,
    ) -> list[list[str]]:
        """
        Optimize work assignment for multiple agents.

        Args:
            graph: Dependency graph
            agent_count: Number of available agents

        Returns:
            List of work assignments, one per agent
        """
        try:
            # Get work levels for parallel execution
            levels = self.calculate_work_levels(graph)

            # Initialize agent assignments
            agent_assignments = [[] for _ in range(agent_count)]
            agent_loads = [0.0] * agent_count

            # Assign work level by level
            for level in sorted(levels.keys()):
                level_nodes = levels[level]

                # Sort nodes by priority and estimated duration
                level_nodes.sort(
                    key=lambda x: (
                        -graph.nodes[x].priority,  # Higher priority first
                        -(
                            graph.nodes[x].estimated_duration or 1.0
                        ),  # Longer tasks first
                    ),
                )

                # Assign nodes to least loaded agents
                for node_id in level_nodes:
                    node = graph.nodes[node_id]

                    # Skip completed or in-progress nodes
                    if node.is_completed or node.is_in_progress:
                        continue

                    # Find least loaded agent
                    min_load_agent = min(
                        range(agent_count),
                        key=lambda i: agent_loads[i],
                    )

                    # Assign to agent
                    agent_assignments[min_load_agent].append(node_id)
                    agent_loads[min_load_agent] += node.estimated_duration or 1.0

            return agent_assignments

        except Exception as e:
            self.logger.exception(f"Failed to optimize work assignment: {e}")
            return [[] for _ in range(agent_count)]

    def validate_dependency_consistency(
        self,
        graph: ModelDependencyGraph,
    ) -> dict[str, list[str]]:
        """
        Validate dependency graph for consistency issues.

        Args:
            graph: Dependency graph to validate

        Returns:
            Dictionary of validation issues by category
        """
        try:
            issues = {
                "missing_nodes": [],
                "orphaned_edges": [],
                "inconsistent_adjacency": [],
                "invalid_in_degrees": [],
                "self_dependencies": [],
            }

            # Check for missing nodes referenced in edges
            for edge_id, edge in graph.edges.items():
                if edge.source_id not in graph.nodes:
                    issues["missing_nodes"].append(
                        f"Edge {edge_id} references missing source node {edge.source_id}",
                    )
                if edge.target_id not in graph.nodes:
                    issues["missing_nodes"].append(
                        f"Edge {edge_id} references missing target node {edge.target_id}",
                    )

            # Check for orphaned edges in node references
            for node_id, node in graph.nodes.items():
                for edge_id in node.dependencies_in + node.dependencies_out:
                    if edge_id not in graph.edges:
                        issues["orphaned_edges"].append(
                            f"Node {node_id} references missing edge {edge_id}",
                        )

            # Check adjacency list consistency
            for node_id, neighbors in graph.adjacency_list.items():
                if node_id not in graph.nodes:
                    issues["inconsistent_adjacency"].append(
                        f"Adjacency list contains missing node {node_id}",
                    )

                for neighbor in neighbors:
                    if neighbor not in graph.nodes:
                        issues["inconsistent_adjacency"].append(
                            f"Node {node_id} has missing neighbor {neighbor}",
                        )

            # Check in-degree consistency
            calculated_in_degrees = defaultdict(int)
            for node_id, neighbors in graph.adjacency_list.items():
                for neighbor in neighbors:
                    calculated_in_degrees[neighbor] += 1

            for node_id in graph.nodes:
                expected_degree = calculated_in_degrees.get(node_id, 0)
                actual_degree = graph.in_degree.get(node_id, 0)
                if expected_degree != actual_degree:
                    issues["invalid_in_degrees"].append(
                        f"Node {node_id} in-degree mismatch: expected {expected_degree}, got {actual_degree}",
                    )

            # Check for self-dependencies
            for edge_id, edge in graph.edges.items():
                if edge.source_id == edge.target_id:
                    issues["self_dependencies"].append(
                        f"Edge {edge_id} creates self-dependency for node {edge.source_id}",
                    )

            return issues

        except Exception as e:
            self.logger.exception(f"Dependency validation failed: {e}")
            return {"validation_error": [str(e)]}

    # Private helper methods

    def _detect_cycles_in_subgraph(
        self,
        graph: ModelDependencyGraph,
        nodes: set[str],
    ) -> list[list[str]]:
        """Detect cycles in a subgraph of nodes."""
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs_cycle(node_id: str, path: list[str]) -> None:
            if node_id in rec_stack:
                # Cycle found
                try:
                    cycle_start = path.index(node_id)
                    cycle = path[cycle_start:]
                    cycles.append(cycle)
                except ValueError:
                    cycles.append([node_id])
                return

            if node_id in visited:
                return

            visited.add(node_id)
            rec_stack.add(node_id)

            for neighbor in graph.adjacency_list.get(node_id, []):
                if neighbor in nodes:
                    dfs_cycle(neighbor, [*path, node_id])

            rec_stack.remove(node_id)

        for node_id in nodes:
            if node_id not in visited:
                dfs_cycle(node_id, [])

        return cycles

    def _calculate_parallel_groups(
        self,
        graph: ModelDependencyGraph,
        levels: list[list[str]],
    ) -> list[list[str]]:
        """Calculate groups of nodes that can be executed in parallel."""
        parallel_groups = []

        for level in levels:
            if len(level) > 1:
                # Group nodes that have no dependencies on each other
                independent_groups = []
                remaining_nodes = set(level)

                while remaining_nodes:
                    current_group = []
                    nodes_to_process = list(remaining_nodes)

                    for node_id in nodes_to_process:
                        # Check if this node conflicts with any in current group
                        conflicts = False
                        for group_node in current_group:
                            if node_id in graph.get_node_dependencies(
                                group_node,
                            ) or group_node in graph.get_node_dependencies(node_id):
                                conflicts = True
                                break

                        if not conflicts:
                            current_group.append(node_id)
                            remaining_nodes.remove(node_id)

                    if current_group:
                        independent_groups.append(current_group)
                    # Fallback: add remaining nodes individually
                    elif remaining_nodes:
                        node = remaining_nodes.pop()
                        independent_groups.append([node])

                parallel_groups.extend(independent_groups)
            else:
                parallel_groups.append(level)

        return parallel_groups

    def _calculate_critical_path(
        self,
        graph: ModelDependencyGraph,
        sorted_nodes: list[str],
    ) -> list[str]:
        """Calculate the critical path through the dependency graph."""
        # Calculate earliest and latest start times
        earliest_start = {}
        latest_start = {}

        # Forward pass - earliest start times
        for node_id in sorted_nodes:
            node = graph.nodes[node_id]
            dependencies = graph.get_node_dependencies(node_id)

            if not dependencies:
                earliest_start[node_id] = 0
            else:
                max_finish_time = max(
                    earliest_start.get(dep_id, 0)
                    + (graph.nodes[dep_id].estimated_duration or 1.0)
                    for dep_id in dependencies
                    if dep_id in graph.nodes
                )
                earliest_start[node_id] = max_finish_time

        # Backward pass - latest start times
        project_duration = max(
            earliest_start.get(node_id, 0)
            + (graph.nodes[node_id].estimated_duration or 1.0)
            for node_id in sorted_nodes
        )

        for node_id in reversed(sorted_nodes):
            node = graph.nodes[node_id]
            dependents = graph.get_node_dependents(node_id)

            if not dependents:
                latest_start[node_id] = project_duration - (
                    node.estimated_duration or 1.0
                )
            else:
                min_dependent_start = min(
                    latest_start.get(dep_id, project_duration)
                    for dep_id in dependents
                    if dep_id in graph.nodes
                )
                latest_start[node_id] = min_dependent_start - (
                    node.estimated_duration or 1.0
                )

        # Find critical path (nodes with zero slack)
        critical_path = []
        for node_id in sorted_nodes:
            earliest = earliest_start.get(node_id, 0)
            latest = latest_start.get(node_id, 0)
            if abs(earliest - latest) < 0.01:  # Consider floating point precision
                critical_path.append(node_id)

        return critical_path
