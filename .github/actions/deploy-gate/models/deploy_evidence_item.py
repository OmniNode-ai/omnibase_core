# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One DoD evidence row in the deploy-gate ticket projection."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from models.deploy_evidence_check import (
    ModelDeployEvidenceCheck,
)


class ModelDeployEvidenceItem(BaseModel):
    """Typed row fields consumed by deploy-evidence detection."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    description: str
    source: str
    checks: list[ModelDeployEvidenceCheck]


__all__ = ["ModelDeployEvidenceItem"]
