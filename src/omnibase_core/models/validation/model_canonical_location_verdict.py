# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelCanonicalLocationVerdict -- the location rules' answer for one request (OMN-21536)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelCanonicalLocationVerdict(BaseModel):
    """What ``HandlerCanonicalLocationRules.handle`` found.

    ``workspace_roots`` are the workspace directories among the request's tracked
    files. ``is_shell_script`` and ``is_typescript_canonical_location`` answer for
    the request's ``path`` and are ``False`` when the request names no path.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    workspace_roots: frozenset[str] = Field(default_factory=frozenset)
    is_shell_script: bool = False
    is_typescript_canonical_location: bool = False
