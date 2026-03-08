#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Mixin Dependency Graph Generator (OMN-1115).

Generates a dependency graph from mixin_capability_mapping.yaml and validates
that the graph is acyclic (no circular dependencies). Outputs DOT format for
visualization and a topological ordering for migration planning.

Usage:
    python scripts/mixin_dependency_graph.py
    python scripts/mixin_dependency_graph.py --format dot > mixins.dot
    python scripts/mixin_dependency_graph.py --format text
    python scripts/mixin_dependency_graph.py --validate-only
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict, deque
from pathlib import Path

import yaml


def load_capability_mapping(path: Path) -> list[dict[str, object]]:
    """Load mixin capability mapping from YAML."""
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(
            f"Expected a YAML mapping at top level, got {type(data).__name__}: {path}"
        )
    mixins_raw = data.get("mixins", [])
    if not isinstance(mixins_raw, list):
        raise ValueError(
            f"Expected 'mixins' to be a list, got {type(mixins_raw).__name__}: {path}"
        )
    mixins: list[dict[str, object]] = mixins_raw
    return mixins


def build_adjacency_list(
    mixins: list[dict[str, object]],
) -> dict[str, list[str]]:
    """Build adjacency list from ordering_constraints.

    Returns a dict mapping each mixin to the list of mixins that depend on it
    (i.e., edges go from dependency to dependent).
    """
    graph: dict[str, list[str]] = defaultdict(list)
    all_names: set[str] = set()

    declared_names: set[str] = set()
    for mixin in mixins:
        declared_names.add(str(mixin["mixin_name"]))

    for mixin in mixins:
        name = str(mixin["mixin_name"])
        all_names.add(name)
        constraints = mixin.get("ordering_constraints", [])
        if isinstance(constraints, list):
            for dep in constraints:
                dep_str = str(dep)
                if dep_str not in declared_names:
                    raise ValueError(
                        f"Mixin '{name}' has ordering constraint on undeclared "
                        f"mixin '{dep_str}'. Check for typos in ordering_constraints."
                    )
                graph[dep_str].append(name)
                all_names.add(dep_str)

    # Ensure all nodes appear in the graph
    for name in all_names:
        if name not in graph:
            graph[name] = []

    return dict(graph)


def detect_cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    """Detect cycles using DFS. Returns list of cycles found."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = dict.fromkeys(graph, WHITE)
    parent: dict[str, str | None] = dict.fromkeys(graph, None)
    cycles: list[list[str]] = []

    def dfs(u: str) -> None:
        color[u] = GRAY
        for v in graph.get(u, []):
            if v not in color:
                color[v] = WHITE
            if color[v] == GRAY:
                # Found a cycle - reconstruct it
                cycle = [v, u]
                node = parent.get(u)
                while node and node != v:
                    cycle.append(node)
                    node = parent.get(node)
                cycle.reverse()
                cycles.append(cycle)
            elif color[v] == WHITE:
                parent[v] = u
                dfs(v)
        color[u] = BLACK

    for node in graph:
        if color[node] == WHITE:
            dfs(node)

    return cycles


def topological_sort(graph: dict[str, list[str]]) -> list[str]:
    """Kahn's algorithm for topological sort."""
    in_degree: dict[str, int] = defaultdict(int)
    all_nodes: set[str] = set(graph.keys())

    for node, deps in graph.items():
        for dep in deps:
            in_degree[dep] += 1
            all_nodes.add(dep)

    queue: deque[str] = deque()
    for node in sorted(all_nodes):
        if in_degree[node] == 0:
            queue.append(node)

    result: list[str] = []
    while queue:
        node = queue.popleft()
        result.append(node)
        for neighbor in sorted(graph.get(node, [])):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return result


def format_dot(mixins: list[dict[str, object]], graph: dict[str, list[str]]) -> str:
    """Generate DOT format output."""
    lines = ["digraph mixin_dependencies {", "  rankdir=TB;", "  node [shape=box];", ""]

    # Color nodes by phase
    phase_colors = {
        1: "#c6efce",  # green - pure compute
        2: "#ffffcc",  # yellow - stateful
        3: "#fce4d6",  # orange - I/O
        4: "#f8cbad",  # red-orange - orchestration
    }

    mixin_phases: dict[str, int] = {}
    for mixin in mixins:
        name = str(mixin["mixin_name"])
        phase = int(mixin.get("phase", 0))
        mixin_phases[name] = phase

    for name, phase in sorted(mixin_phases.items()):
        color = phase_colors.get(phase, "#ffffff")
        label = f"{name}\\n(Phase {phase})"
        lines.append(
            f'  "{name}" [label="{label}", style=filled, fillcolor="{color}"];'
        )

    lines.append("")

    for src, dests in sorted(graph.items()):
        for dest in sorted(dests):
            lines.append(f'  "{src}" -> "{dest}";')

    lines.append("}")
    return "\n".join(lines)


def format_text(
    mixins: list[dict[str, object]],
    topo_order: list[str],
) -> str:
    """Generate text format output with migration order."""
    lines = ["ONEX Mixin Dependency Graph - Migration Order", "=" * 50, ""]

    mixin_data: dict[str, dict[str, object]] = {}
    for mixin in mixins:
        mixin_data[str(mixin["mixin_name"])] = mixin

    current_phase = 0
    for i, name in enumerate(topo_order, 1):
        data = mixin_data.get(name, {})
        phase = int(data.get("phase", 0))
        priority = int(data.get("migration_priority", 0))
        category = str(data.get("handler_type_category", "unknown"))
        constraints = data.get("ordering_constraints", [])

        if phase != current_phase:
            current_phase = phase
            phase_names = {
                1: "Pure Compute",
                2: "Stateful",
                3: "I/O",
                4: "Orchestration",
            }
            lines.append(
                f"\n--- Phase {phase}: {phase_names.get(phase, 'Unknown')} ---\n"
            )

        deps = (
            f" (after: {', '.join(str(c) for c in constraints)})" if constraints else ""
        )
        lines.append(f"  {i:2d}. {name} [{category}, priority={priority}]{deps}")

    lines.append(f"\nTotal mixins: {len(topo_order)}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Mixin Dependency Graph Generator")
    parser.add_argument(
        "--format",
        choices=["dot", "text"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate the graph (check for cycles)",
    )
    parser.add_argument(
        "--mapping-path",
        type=Path,
        default=None,
        help="Path to mixin_capability_mapping.yaml",
    )
    args = parser.parse_args()

    # Resolve mapping path
    if args.mapping_path:
        mapping_path = args.mapping_path
    else:
        # Default: relative to script location
        script_dir = Path(__file__).parent.parent
        mapping_path = (
            script_dir
            / "src"
            / "omnibase_core"
            / "mixins"
            / "mixin_capability_mapping.yaml"
        )

    if not mapping_path.exists():
        print(f"ERROR: Mapping file not found: {mapping_path}", file=sys.stderr)
        return 1

    mixins = load_capability_mapping(mapping_path)
    graph = build_adjacency_list(mixins)

    # Validate: check for cycles
    cycles = detect_cycles(graph)
    if cycles:
        print("ERROR: Circular dependencies detected!", file=sys.stderr)
        for cycle in cycles:
            print(f"  Cycle: {' -> '.join(cycle)}", file=sys.stderr)
        return 1

    if args.validate_only:
        print(f"OK: No cycles detected in {len(mixins)} mixins.")
        return 0

    # Generate topological order
    topo_order = topological_sort(graph)

    if args.format == "dot":
        print(format_dot(mixins, graph))
    else:
        print(format_text(mixins, topo_order))

    return 0


if __name__ == "__main__":
    sys.exit(main())
