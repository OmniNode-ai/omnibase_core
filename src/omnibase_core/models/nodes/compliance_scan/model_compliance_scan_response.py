# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Definition-B response model for the compliance-scan COMPUTE node (OMN-14629).

Wraps the legacy ``list[ModelScanCheckResult]`` return value of
``NodeComplianceScanCompute.scan()`` in a single typed BaseModel so the
runtime bus adapter publishes one aggregate scan-completed event rather than
treating the list as a def-B fan-out sequence (OMN-14403 Sec6ii) — a
directory scan is one logical result, not N independent events.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.compliance_scan.model_scan_check_result import (
    ModelScanCheckResult,
)

__all__ = ["ModelComplianceScanResponse"]


class ModelComplianceScanResponse(BaseModel):
    """Aggregate result of a compliance-scan run over a directory tree."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    results: list[ModelScanCheckResult] = Field(default_factory=list)
