# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Aggregated compliance report state model.

.. versionadded:: OMN-7071
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.nodes.compliance_evidence.model_evidence_check_detail import (
    ModelEvidenceCheckDetail,
)


class ModelEvidenceReportState(BaseModel):
    """Aggregated compliance report produced by the reducer."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    total: int
    passed: int
    failed: int
    results: list[ModelEvidenceCheckDetail]
    run_id: str | None = None
    repo_root: str | None = None
    scan_started_at: str | None = None
