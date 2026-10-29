# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, ConfigDict


class ModelFirstPartyReference(BaseModel):
    """A reference occurrence; paths are labels, never read by the checker."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    path: str
    line: int
    value: str
    kind: str
    source_key: str = ""
