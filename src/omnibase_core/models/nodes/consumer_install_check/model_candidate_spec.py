# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A package whose build is checked against named consumers (OMN-26670)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelCandidateSpec(BaseModel):
    """A package whose build is checked against named consumers."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    distribution: str = Field(min_length=1)
    import_roots: tuple[str, ...] = Field(
        min_length=1,
        description="Top-level import packages of the candidate; a failure that touches one is the candidate's",
    )
    consumers: tuple[str, ...] = Field(min_length=1)
