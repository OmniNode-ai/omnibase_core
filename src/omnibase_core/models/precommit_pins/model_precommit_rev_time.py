# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One resolved revision's commit time (OMN-21433)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelPrecommitRevTime"]


class ModelPrecommitRevTime(BaseModel):
    """A revision and its committed-at timestamp in integer seconds."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    rev: str = Field(min_length=1)
    committed_at: int
