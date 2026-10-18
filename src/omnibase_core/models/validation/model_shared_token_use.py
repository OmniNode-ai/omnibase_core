# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One shared-secret expression at an exact workflow location."""

from pydantic import BaseModel, ConfigDict, Field


class ModelSharedTokenUse(BaseModel):
    """A location is a JSON pointer, so adjacent steps cannot share approval."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    workflow: str
    location: str
    reference: str
    count: int = Field(default=1, ge=1)
