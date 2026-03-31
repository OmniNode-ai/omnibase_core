# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Compliance scan models."""

from omnibase_core.models.nodes.compliance_scan.model_check_result import (
    ModelCheckResult,
)
from omnibase_core.models.nodes.compliance_scan.model_scan_check_result import (
    ModelScanCheckResult,
)

__all__ = [
    "ModelCheckResult",
    "ModelScanCheckResult",
]
