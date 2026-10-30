# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelHandlerDiCheckInput -- what the K1 handler_di check effect is asked to read (OMN-21531)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelHandlerDiCheckInput(BaseModel):
    """Files or directories to judge, the repository root and the baseline file to hold them to."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    targets: tuple[str, ...] = Field(
        description="Files or directories; a file outside the contract's scope is not judged."
    )
    root: str = Field(
        description="Repository root that paths and the baseline resolve against."
    )
    baseline_path: str | None = Field(
        default=None,
        description="Baseline file relative to the root; None keeps the baseline_ratchet row's path.",
    )
