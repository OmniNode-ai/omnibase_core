# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Provenance record for the pinned MSK IAM consumer-group pattern mirror.

Split out of ``model_consumer_group_iam_patterns`` to satisfy the one-class-per-file
rule (``onex-single-class-per-file``).

.. versionadded:: OMN-15639
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelConsumerGroupIamSource(BaseModel):
    """Provenance of the mirrored terraform variable.

    Recorded so a reviewer can re-derive the mirror from the authoritative source
    without guessing which file or commit it came from.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str = Field(..., min_length=1, description="Source repository name.")
    path: str = Field(..., min_length=1, description="Path within the source repo.")
    variable: str = Field(..., min_length=1, description="Terraform variable name.")
    consumed_by: str = Field(
        ..., min_length=1, description="Terraform resource that consumes the variable."
    )
    file_sha256: str = Field(
        ..., min_length=64, max_length=64, description="sha256 of the source file."
    )
    last_touch_commit: str = Field(
        ..., min_length=7, description="Commit that last modified the source file."
    )
    verified_at: str = Field(
        ..., min_length=1, description="Date the pin was verified against the source."
    )
    ticket: str = Field(..., min_length=1, description="Owning ticket.")


__all__ = ["ModelConsumerGroupIamSource"]
