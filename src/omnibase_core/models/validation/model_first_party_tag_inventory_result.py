# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, ConfigDict


class ModelFirstPartyTagInventoryResult(BaseModel):
    """Sorted dev-merge tags; an empty inventory remains an explicit fact."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    repo: str
    tags: tuple[str, ...]
