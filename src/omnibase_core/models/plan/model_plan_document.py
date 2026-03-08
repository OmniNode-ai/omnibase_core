# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import re

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

        # Phase 3: Circular dependency detection via DFS topological sort
        # Build adjacency list of internal deps only
        adj: dict[str, list[str]] = {}
        for entry in self.entries:
            adj[entry.id] = [d for d in entry.dependencies if d in internal_ids]

        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = dict.fromkeys(internal_ids, WHITE)
        path: list[str] = []

        def dfs(node: str) -> None:
            color[node] = GRAY
            path.append(node)
            for dep in adj.get(node, []):
                if color[dep] == GRAY:
                    cycle_start = path.index(dep)
                    cycle = path[cycle_start:] + [dep]
                    raise ValueError(  # error-ok: Pydantic model_validator requires ValueError
                        f"Circular dependency detected: {' -> '.join(cycle)}"
                    )
                if color[dep] == WHITE:
                    dfs(dep)
            path.pop()
            color[node] = BLACK

        for eid in internal_ids:
            if color[eid] == WHITE:
                dfs(eid)

        return self

    @property
    def is_canonical_format(self) -> bool:
        """True if plan uses ## Task N: format (preferred by design-to-plan)."""
        return self.structure_type.is_canonical

    @property
    def has_valid_dependency_graph(self) -> bool:
        """True if no circular dependencies exist.

        Always True after construction -- the model_validator rejects cycles at
        construction time, so a live instance always has a valid graph.
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
