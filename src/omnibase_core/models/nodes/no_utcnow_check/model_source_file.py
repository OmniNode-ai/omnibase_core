# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A single (path, source) pair fed into the no_utcnow_check COMPUTE node."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelSourceFile"]


class ModelSourceFile(BaseModel):
    """An explicit (path, source) pair.

    Content arrives inline so the COMPUTE handler never touches the
    filesystem — all reads happen at the paired EFFECT boundary
    (``node_source_file_gather_effect``).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # string-path-ok: source label for findings/locations, not a UUID
    path: str
    source: str
