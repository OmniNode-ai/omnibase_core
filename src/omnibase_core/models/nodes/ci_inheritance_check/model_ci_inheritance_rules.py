# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Rule data of the ci-inheritance handler, read from its validation contract (OMN-21518)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelCiInheritanceRules"]


class ModelCiInheritanceRules(BaseModel):
    """Pattern and message templates of the reference check; never code.

    Loaded from the rule rows of ``contracts/ci_inheritance.validation.yaml``.
    Message templates take ``{location}``, ``{target}`` and ``{host}``; the
    remediation template takes ``{organization}`` and ``{host}``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    uses_pattern: str = Field(
        min_length=1,
        description="Regex with a named group `value` capturing a `uses:` target.",
    )
    new_reference_message: str = Field(min_length=1)
    new_reference_remediation: str = Field(min_length=1)
    existing_reference_message: str = Field(min_length=1)
