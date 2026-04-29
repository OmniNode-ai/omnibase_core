# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Evidence Kind Enum.

Types of evidence required for ticket contracts.
"""

from enum import Enum, unique


@unique
class EnumEvidenceKind(str, Enum):
    """Types of evidence required for ticket contract validation.

    Evidence kinds specify what type of proof is required:
    - tests: Automated test coverage
    - docs: Documentation updates
    - ci: CI/CD pipeline changes
    - benchmark: Performance benchmarks
    - manual: Manual verification steps
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
