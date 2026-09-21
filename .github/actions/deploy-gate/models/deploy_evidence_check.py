# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One check in the deploy-gate ticket evidence projection."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelDeployEvidenceCheck(BaseModel):
    """Typed check fields consumed by deploy-evidence detection."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    check_type: str
    check_value: str


__all__ = ["ModelDeployEvidenceCheck"]
