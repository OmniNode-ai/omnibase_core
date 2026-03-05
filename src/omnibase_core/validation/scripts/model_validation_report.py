# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Data model for aggregated topic validation results."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ValidationReport:
    """Aggregated validation results."""

    violations: list[str] = field(default_factory=list)
    scanned_files: int = 0
    total_topics: int = 0

    @property
    def is_clean(self) -> bool:
        """Return True if no violations were found."""
        return len(self.violations) == 0
