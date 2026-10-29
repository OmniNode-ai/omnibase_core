# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Inputs to the pure node-home ratchet (OMN-20702)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.validation.model_canonical_file_shape_text import (
    ModelCanonicalFileShapeText,
)


class ModelNodeHomeRatchetRequest(BaseModel):
    """Indexed node inputs, base inventory, baselines and entry-point names."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tracked_paths: frozenset[str] = Field(description="Repo-relative POSIX file paths")
    node_class_paths: frozenset[str] = Field(
        description="Files defining a top-level class named Node<Upper>..."
    )
    node_contract_texts: tuple[ModelCanonicalFileShapeText, ...] = Field(
        default_factory=tuple,
        description="contract.yaml text of each head node directory that has one",
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
    renamed_paths: tuple[tuple[str, str], ...] = Field(
        default_factory=tuple,
        description="(old, new) file paths git detects as renamed from base to head",
    )


__all__ = ["ModelNodeHomeRatchetRequest"]
