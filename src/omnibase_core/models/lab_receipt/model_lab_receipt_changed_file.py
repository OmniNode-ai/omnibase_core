# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One path changed by a pull request (OMN-21823)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelLabReceiptChangedFile(BaseModel):
    """A changed path and the first letter of its git name-status code."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(description="Repository-relative path of the changed file")
    status: str = Field(
        description="First letter of git's name-status code (A, M, D, R, C, T)"
    )
    comment_only: bool = Field(
        default=False,
        description="True when the diff of this file changes only comments and directive lines; set by the fact-gathering node; absent means counted",
    )
