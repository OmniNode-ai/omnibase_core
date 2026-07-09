# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One structural segment of a decomposed PR body (OMN-14187).

Piece 1/5 of the canonical OCC stamp-model (parent epic OMN-14180). When a
parser (Piece 2 / OMN-14188) decomposes an existing PR body, each segment
becomes one of these. ``content`` is retained byte-identical to the source so
an idempotent re-render preserves human-authored prose verbatim instead of
clobbering the PR description. Section order is carried by position in the
containing tuple, not by a field. Pure Pydantic domain model: zero I/O.
"""

from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict, Field


class ModelPrBodySection(BaseModel):
    """A heading + raw content span of a PR body.

    ``heading`` is ``None`` for the leading, un-headed segment. ``content`` is
    preserved byte-for-byte (including embedded/trailing whitespace) so the
    round-trip is lossless. ``is_stamp_section`` is ``True`` only for the
    canonical Evidence-Source/Evidence-Ticket block the renderer owns; ``False``
    marks human-authored prose the renderer must preserve verbatim.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    heading: str | None = Field(default=None)
    content: str = Field(default="")
    is_stamp_section: bool = Field(default=False)

    def as_dict(self) -> dict[str, object]:
        return {
            "heading": self.heading,
            "content": self.content,
            "is_stamp_section": self.is_stamp_section,
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))


__all__ = ["ModelPrBodySection"]
