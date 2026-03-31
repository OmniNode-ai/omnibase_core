# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Compliance evidence output model.

.. versionadded:: OMN-7071
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelComplianceEvidenceOutput(BaseModel):
    """Output produced by the compliance evidence EFFECT handler."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    report_path: str
    latest_path: str
    total: int
    passed: int
    failed: int
