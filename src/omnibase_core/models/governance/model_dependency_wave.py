# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Dependency wave model — conservative overlap-based parallel group of nodes."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelDependencyWave(BaseModel):
    """A conservative overlap-based parallel group of nodes.

    Nodes in the same wave have no detected overlap with each other.
    Waves represent non-overlapping grouping, not guaranteed safe topological ordering.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    wave_number: int
    node_refs: list[str]  # "repo/node_name" format
