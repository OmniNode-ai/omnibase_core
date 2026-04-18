# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed view over the ``excludes`` block of a validator-requirements entry.

Carries the two canonical buckets (``allowed`` path-regex patterns, and
``forbidden`` path-regex patterns). Kept as a frozen Pydantic model so spec
drift surfaces as a validation error rather than silently losing a bucket.

Related ticket: OMN-9115 (consumer), OMN-9051 (spec), parent OMN-9048.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelValidatorRequirementExcludes"]


class ModelValidatorRequirementExcludes(BaseModel):
    """Allow/forbid path-regex buckets for a validator's exclusion policy."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    allowed: list[str] = Field(
        default_factory=list,
        description="Path regex patterns that this validator SKIPS by design.",
    )
    forbidden: list[str] = Field(
        default_factory=list,
        description="Path regex patterns that are NEVER allowed in 'allowed'.",
    )
