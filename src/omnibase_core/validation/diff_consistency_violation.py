# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed detail for one receipt claim contradicted by its PR diff."""

from dataclasses import dataclass, field
from pathlib import Path

from omnibase_core.enums.ticket.enum_diff_attestation import EnumDiffAttestation


@dataclass(frozen=True)
class DiffConsistencyViolation:
    """One attestation contradicted by the PR diff.

    Attributes:
        attestation: The diff-falsifiable claim that was contradicted.
        detail: Human-readable explanation naming the offending diff entries.
        receipt_path: Path to the receipt on disk (empty when checked in-memory).
    """

    attestation: EnumDiffAttestation
    detail: str
    receipt_path: Path = field(default_factory=Path)
