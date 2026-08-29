# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A tile's severity verdict, and the policy that produced it (OMN-16884).

The board **maps severity to presentation**; it does not compute severity. The
verdicts arrive from upstream projections — a consumer-flow classification, a
DLQ depth reading, a chain-liveness check — and a client that thresholded them
itself would be inferring authoritative system state, which the truth doctrine
forbids.

Because the verdict is authored elsewhere, it has to say where: ``policy_id``,
``policy_version``, and ``policy_digest`` make "why is this tile red?" answerable
against the exact policy revision that decided it, rather than against whatever
that policy says today.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_status_severity import EnumStatusSeverity
from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = ["ModelSeverityVerdict", "SEVERITY_POLICY_DIGEST_PATTERN"]

#: Policy digests are ``sha256:<64 lowercase hex chars>``.
SEVERITY_POLICY_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


class ModelSeverityVerdict(BaseModel):
    """An upstream severity decision, traceable to the policy that made it."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    severity: EnumStatusSeverity = Field(
        ...,
        description="Canonical semantic severity decided upstream",
    )
    status_value: str = Field(
        ...,
        description=(
            "The upstream verdict in its own vocabulary (e.g. 'STALLED', "
            "'STARVED'), preserved so the tile can show what was actually said"
        ),
        min_length=1,
    )
    policy_id: str = Field(  # string-id-ok: semantic policy label, not a UUID
        ...,
        description="Identifier of the policy that produced this verdict",
        min_length=1,
    )
    policy_version: ModelSemVer = Field(
        ...,
        description="Version of that policy",
    )
    policy_digest: str = Field(
        ...,
        description="SHA-256 of the policy revision, as 'sha256:<hex>'",
    )

    @field_validator("policy_digest")
    @classmethod
    def validate_policy_digest(cls, value: str) -> str:
        """Reject anything that is not a ``sha256:<hex>`` digest.

        Raises:
            ValueError: If ``value`` does not match the digest pattern.
        """
        if not SEVERITY_POLICY_DIGEST_PATTERN.match(value):
            # error-ok: Pydantic field_validator rejects invalid policy digests
            raise ValueError(
                f"policy_digest must match 'sha256:<64 hex chars>', got '{value}'"
            )
        return value
