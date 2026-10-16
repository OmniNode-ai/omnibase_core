# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One field of the typed command, and the hook-input path it is drawn from (OMN-18531; relocated by OMN-21093)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelClientArgument(BaseModel):
    """A command field and its source; the source must be a `$.` path into the hook input."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(description="The typed command's field name.")
    source: str = Field(
        description="Hook-input path the value is drawn from, e.g. $.session.id."
    )
