# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One machine-written deployment receipt found for a repository (OMN-21926)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelMergeReceiptRecord(BaseModel):
    """What a deployment receipt names. An empty string or zero means it did not name it."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    source: str = Field(
        description="Declared receipt source that wrote it; only a source the contract "
        "names counts as machine-written"
    )
    sha: str = Field(description="Full sha of the commit the deployment was built from")
    repo: str = Field(
        default="", description="Repository the deployment was built from"
    )
    pr_number: int = Field(
        default=0, description="Pull request the receipt names, or zero"
    )
    branch: str = Field(default="", description="Branch the receipt names")
