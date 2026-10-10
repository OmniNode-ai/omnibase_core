# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Request of the allowlist shrink-only ratchet."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelAllowlistRatchetInput"]


class ModelAllowlistRatchetInput(BaseModel):
    """The allowlist text at the merge base and at the head, with no I/O behind it."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    base_text: str | None = Field(
        description="Allowlist text at the merge base, or None when the file is absent there.",
    )
    head_text: str | None = Field(
        description="Allowlist text at the head, or None when the file is absent there.",
    )
