# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Inputs to the pure node-home ratchet (OMN-20702)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelNodeHomeRatchetRequest(BaseModel):
    """Indexed node inputs, base inventory, baselines and entry-point names."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tracked_paths: frozenset[str] = Field(description="Repo-relative POSIX file paths")
    node_class_paths: frozenset[str] = Field(
        description="Files defining a top-level class named Node<Upper>..."
    )
    head_baseline_text: str | None = Field(
        description="Baseline in the tree under check"
    )
    base_baseline_text: str | None = Field(
        description="Base baseline, or None when that revision has no baseline"
    )
    base_node_directories: frozenset[str] = Field(
        description="Node directories at the base revision when it has no baseline"
    )
    head_entry_points: frozenset[str] = Field(
        description='Indexed [project.entry-points."onex.nodes"] names'
    )
    base_entry_points: frozenset[str] = Field(
        description='Base-revision [project.entry-points."onex.nodes"] names'
    )


__all__ = ["ModelNodeHomeRatchetRequest"]
