# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Per-node compliance check detail model.

.. versionadded:: OMN-7071
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.nodes.compliance_evidence.model_compliance_check_entry import (
    ModelComplianceCheckEntry,
)


class ModelComplianceCheckDetail(BaseModel):
    """Per-node compliance check result."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    node_id: str
    passed: bool
    checks: list[ModelComplianceCheckEntry]
