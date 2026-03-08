# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import re
from collections import deque

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_plan_structure_type import EnumPlanStructureType
from omnibase_core.models.plan.model_plan_entry import ModelPlanEntry

__all__ = ["ModelPlanDocument", "PlanDocument"]

_INTERNAL_DEP_PATTERN = re.compile(r"^P[0-9]")


class ModelPlanDocument(BaseModel):
    """A fully parsed plan markdown file.

    Produced by plan-to-tickets' detect_structure() + extract_epic_title().
    Replaces the ad-hoc ``(structure_type, entries)`` tuple.

    Validates:
    - At least one entry (enforced by Field min_length=1)
    - No duplicate entry IDs
    - No dangling internal dependencies (P# that doesn't exist in the document)
    - No circular dependencies (internal refs only)

    External dependencies (OMN-*) are passed through -- they are validated
    elsewhere by architecture checks.

    Frozen: parsed plans are immutable.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    title: str = Field(..., min_length=1, description="Plan title from # heading.")
    structure_type: EnumPlanStructureType
    entries: list[ModelPlanEntry] = Field(..., min_length=1)
    source_path: str | None = Field(
        default=None,
        description="Path to the source markdown file, if known.",
    )
    goal: str | None = Field(
        default=None, description="One-sentence goal from plan header."
    )
    architecture: str | None = Field(
        default=None, description="Architecture summary from plan header."
    )

    @model_validator(mode="after")
    def _validate_entries(self) -> ModelPlanDocument:
        """Validate entry IDs, dangling deps, and circular deps."""
        # Phase 1: Check for duplicate IDs, collect known IDs
        seen: dict[str, str] = {}
        for entry in self.entries:
            if entry.id in seen:
                raise ValueError(  # error-ok: Pydantic model_validator requires ValueError
                    f"Duplicate entry ID '{entry.id}': "
                    f"'{seen[entry.id]}' and '{entry.title}'"
                )
            seen[entry.id] = entry.title

        internal_ids = set(seen.keys())

        # Phase 2: Check for dangling internal dependencies
        # Any dep matching ^P[0-9] is an internal ref and must exist in the document
        for entry in self.entries:
            for dep in entry.dependencies:
                if _INTERNAL_DEP_PATTERN.match(dep) and dep not in internal_ids:
                    raise ValueError(  # error-ok: Pydantic model_validator requires ValueError
                        f"Dangling internal dependency '{dep}' in entry '{entry.id}': "
                        f"'{dep}' does not exist in document entries"
                    )

        # Phase 3: Circular dependency detection via iterative DFS topological sort.
        # Iterative (not recursive) to avoid RecursionError on large plans.
        # Build adjacency list of internal deps only.
        adj: dict[str, list[str]] = {}
        for entry in self.entries:
            adj[entry.id] = [d for d in entry.dependencies if d in internal_ids]

        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = dict.fromkeys(internal_ids, WHITE)

        for start in internal_ids:
            if color[start] != WHITE:
                continue
            # Each stack frame: (node, iterator_over_neighbors, path_so_far)
            path_set: set[str] = set()
            path_list: list[str] = []
            stack: deque[tuple[str, int]] = deque()
            stack.append((start, 0))

            while stack:
                node, idx = stack[-1]
                neighbors = adj.get(node, [])

                if idx == 0:
                    # First visit
                    color[node] = GRAY
                    path_list.append(node)
                    path_set.add(node)

                if idx < len(neighbors):
                    dep = neighbors[idx]
                    stack[-1] = (node, idx + 1)
                    if color[dep] == GRAY:
                        # Cycle detected: reconstruct cycle path
                        cycle_start = path_list.index(dep)
                        cycle = path_list[cycle_start:] + [dep]
                        raise ValueError(  # error-ok: Pydantic model_validator requires ValueError
                            f"Circular dependency detected: {' -> '.join(cycle)}"
                        )
                    if color[dep] == WHITE:
                        stack.append((dep, 0))
                else:
                    # All neighbors visited
                    stack.pop()
                    path_list.pop()
                    path_set.discard(node)
                    color[node] = BLACK

        return self

    @property
    def is_canonical_format(self) -> bool:
        """True if plan uses ## Task N: format (preferred by design-to-plan)."""
        return self.structure_type.is_canonical

    @property
    def has_valid_dependency_graph(self) -> bool:
        """Structural invariant: always True for any constructed instance.

        ``_validate_entries`` rejects circular and dangling dependencies at
        construction time, so this property is an invariant assertion, not a
        recheck. Do NOT call this expecting a live revalidation -- it will
        always return True. Use it as a readable assertion in calling code
        (e.g., ``assert doc.has_valid_dependency_graph``).
        """
        return True

    def entry_by_id(self, entry_id: str) -> ModelPlanEntry | None:
        """Look up entry by ID. Returns None if not found.

        Linear scan is acceptable: plan documents have 5-30 entries.
        Premature optimization via a cached index is deferred.
        """
        for entry in self.entries:
            if entry.id == entry_id:
                return entry
        return None


PlanDocument = ModelPlanDocument
