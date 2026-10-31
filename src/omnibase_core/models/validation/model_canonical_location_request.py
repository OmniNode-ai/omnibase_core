# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelCanonicalLocationRequest -- what the location rules are asked about one path (OMN-21536)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelCanonicalLocationRequest(BaseModel):
    """One question for ``HandlerCanonicalLocationRules.handle``.

    ``tracked_files`` are the tracked paths the workspace roots are derived from.
    ``path`` is the path to judge, ``head_bytes`` the leading bytes of that file
    (``None`` when unread) and ``workspace_roots`` the roots a previous answer
    returned, so a caller judging many paths derives the roots once.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str | None = None
    head_bytes: bytes | None = None
    tracked_files: tuple[str, ...] = Field(default_factory=tuple)
    workspace_roots: frozenset[str] = Field(default_factory=frozenset)
