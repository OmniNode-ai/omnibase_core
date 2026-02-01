"""
Internal dependency graph type for ExecutionResolver.

This module contains a private data structure used internally by the
ExecutionResolver. This is not part of the public API.

.. versionadded:: 0.4.1
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class _DependencyGraph:
    """Internal dependency graph structure."""

    # handler_ref -> set of handler_refs it depends on (must run AFTER these)
    edges: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    # handler_ref -> set of handler_refs that depend on it (must run BEFORE these)
    reverse_edges: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    # All handler refs in the graph
    nodes: set[str] = field(default_factory=set)


__all__ = [
    "_DependencyGraph",
]
