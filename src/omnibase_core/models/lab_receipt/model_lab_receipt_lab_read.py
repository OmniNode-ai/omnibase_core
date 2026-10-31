# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One read of a lab host's own install record (OMN-21823)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelLabReceiptLabRead(BaseModel):
    """What a lab host says is installed on it and whether it is running."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    host: str = Field(description="Lab host that was read")
    installed_revision: str = Field(description="Revision the host reports installed")
    running: bool = Field(description="Whether the host reports that revision running")
