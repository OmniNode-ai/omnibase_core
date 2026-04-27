# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EnumEvidenceKind — types of evidence required for ticket contracts.

OMN-10064 / OMN-9582: Ported from onex_change_control.enums.enum_evidence_kind
to omnibase_core so ModelTicketContract.evidence_requirements can reference it.

OCC re-exports this enum after Task 4 lands.
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class EnumEvidenceKind(str, Enum):
    """Types of evidence required for ticket contract validation.

    Evidence kinds specify what type of proof is required:
    - TESTS: Automated test coverage
    - DOCS: Documentation updates
    - CI: CI/CD pipeline changes
    - BENCHMARK: Performance benchmarks
    - MANUAL: Manual verification steps
    """

    TESTS = "tests"
    """Automated test coverage."""

    DOCS = "docs"
    """Documentation updates."""

    CI = "ci"
    """CI/CD pipeline changes."""

    BENCHMARK = "benchmark"
    """Performance benchmarks."""

    MANUAL = "manual"
    """Manual verification steps."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value


__all__ = ["EnumEvidenceKind"]
