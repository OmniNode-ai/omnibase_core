"""
Data models for protocol audit operations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

# Configure logger for this module
logger = logging.getLogger(__name__)


@dataclass
class ModelAuditResult:
    """Result of protocol audit operation."""

    success: bool
    repository: str
    protocols_found: int
    duplicates_found: int
    conflicts_found: int
    violations: list[str]
    recommendations: list[str]
    execution_time_ms: int = 0

    def has_issues(self) -> bool:
        """Check if audit found any issues."""
        return (
            self.duplicates_found > 0
            or self.conflicts_found > 0
            or len(self.violations) > 0
        )
