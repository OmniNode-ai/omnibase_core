# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Definition-B request model for the compliance-scan COMPUTE node (OMN-14629).

Wraps the legacy ``NodeComplianceScanCompute.scan(repo_root, *, source_only)``
positional/keyword pair into a single typed request so the handler's
``handle(request) -> response`` entry-point has exactly one adaptable
parameter, per the canonical handler-shape gate (OMN-14355).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelComplianceScanRequest"]


class ModelComplianceScanRequest(BaseModel):
    """Request to scan a directory tree for contract.yaml structural compliance."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo_root: str
    source_only: bool = False
