# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Per-receipt aggregate emitted by the diff-consistency scanner."""

from dataclasses import dataclass
from pathlib import Path

from omnibase_core.validation.diff_consistency_violation import (
    DiffConsistencyViolation,
)


@dataclass(frozen=True)
class ReceiptDiffFinding:
    """All diff-consistency violations found for one receipt file."""

    receipt_path: Path
    violations: list[DiffConsistencyViolation]


__all__ = ["ReceiptDiffFinding"]
