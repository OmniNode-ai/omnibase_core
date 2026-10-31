# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One lab receipt found for a pull request (OMN-21823)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelLabReceiptRecord(BaseModel):
    """What a receipt names. An empty string means the carrier did not name it."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    head_sha: str = Field(description="Full sha of the PR head the receipt proves")
    host: str = Field(default="", description="Lab host the revision was installed on")
    installer: str = Field(
        default="", description="Declared installer that put the revision there"
    )
    installed_revision: str = Field(
        default="", description="Revision installed on the host (a prefix of the head)"
    )
    observation: str = Field(
        default="", description="What was observed running at that revision"
    )
    carrier: str = Field(
        default="", description="Where the record was read from; reports print it only"
    )
