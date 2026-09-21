# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Per-receipt aggregation of diff-consistency violations."""

from dataclasses import dataclass
from pathlib import Path

from omnibase_core.validation.diff_consistency_violation import (
    DiffConsistencyViolation,
)


@dataclass(frozen=True)
class ReceiptDiffFinding:
    """All diff-consistency violations found for one receipt file on disk."""

    receipt_path: Path
    violations: list[DiffConsistencyViolation]
