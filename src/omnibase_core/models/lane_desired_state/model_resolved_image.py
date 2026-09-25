# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelResolvedImage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repository: str = Field(..., description="Container image repository", min_length=1)
    reference: str = Field(
        ...,
        description="Immutable digest (sha256: + 64 lowercase hex) or a tag such as 'latest'",
        min_length=1,
    )

    def is_mutable_tag(self) -> bool:
        return not (self.reference.startswith("sha256:") and len(self.reference) == 71)


__all__ = ["ModelResolvedImage"]
