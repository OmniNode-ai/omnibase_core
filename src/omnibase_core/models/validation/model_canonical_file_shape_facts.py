# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelCanonicalFileShapeFacts -- typed facts for the canonical-file-shape checker (OMN-21515)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.validation.model_canonical_file_shape_change import (
    ModelCanonicalFileShapeChange,
)
from omnibase_core.models.validation.model_canonical_file_shape_text import (
    ModelCanonicalFileShapeText,
)
from omnibase_core.models.validation.model_canonical_file_shape_tree import (
    ModelCanonicalFileShapeTree,
)


class ModelCanonicalFileShapeFacts(BaseModel):
    """Everything the checker reads: head tree, base facts, changes, texts.

    ``base_tree`` is present only when the head baseline holds an entry the base
    baseline lacks (the bootstrap proof needs the base revision's refused paths).
    ``commit_messages`` is None when no message is known (a pre-commit run on the
    index); the release-trailer rule is then deferred to the commit-msg stage and
    to the revision run, which both know the message.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    head_tree: ModelCanonicalFileShapeTree
    base_tree: ModelCanonicalFileShapeTree | None = None
    has_base: bool = False
    head_baseline_text: str | None = None
    base_baseline_text: str | None = None
    declared_texts: tuple[ModelCanonicalFileShapeText, ...] = Field(
        default_factory=tuple
    )
    changes: tuple[ModelCanonicalFileShapeChange, ...] = Field(default_factory=tuple)
    head_lifecycle_text: str | None = None
    base_lifecycle_text: str | None = None
    commit_messages: tuple[str, ...] | None = None
