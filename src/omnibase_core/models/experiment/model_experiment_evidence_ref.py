# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed evidence reference for the Shared Experiment Result Contract (OMN-13613).

``evidence_id`` is the canonical UUID of the evidence record (e.g. an
``ModelEvidenceItem.item_id``). ``artifact_ref`` optionally carries the
content-addressed artifact-store reference (``sha256:<64 hex>``) for the raw
evidence bytes. Shared by the three Phase-3 experiment orchestrators of the
SEA→canonical migration (epic OMN-13604).

.. versionadded:: OMN-13613
"""

from __future__ import annotations

import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ["ModelExperimentEvidenceRef"]

_SHA256_ARTIFACT_REF_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class ModelExperimentEvidenceRef(BaseModel):
    """Typed reference to the durable evidence backing an experiment result."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    evidence_id: UUID = Field(
        ...,
        description="Canonical UUID of the durable evidence record.",
    )
    artifact_ref: str | None = Field(  # content-address-ok: sha256-prefixed digest
        default=None,
        description=(
            "Optional content-addressed artifact reference "
            "('sha256:<64 lowercase hex chars>') for the raw evidence bytes."
        ),
    )

    @field_validator("artifact_ref")
    @classmethod
    def _validate_artifact_ref(cls, value: str | None) -> str | None:
        if value is not None and not _SHA256_ARTIFACT_REF_RE.match(value):
            raise ValueError(
                "artifact_ref must match 'sha256:<64 lowercase hex chars>', "
                f"got: {value!r}"
            )
        return value
