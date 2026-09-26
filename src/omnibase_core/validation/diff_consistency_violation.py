# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed receipt attestation violation for diff-consistency checks."""

from dataclasses import dataclass, field
from pathlib import Path

from omnibase_core.enums.ticket.enum_diff_attestation import EnumDiffAttestation


@dataclass(frozen=True)
class DiffConsistencyViolation:
    """One receipt attestation contradicted by a pull-request diff."""

    attestation: EnumDiffAttestation
    detail: str
    receipt_path: Path = field(default_factory=Path)


__all__ = ["DiffConsistencyViolation"]
