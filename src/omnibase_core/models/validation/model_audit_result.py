from __future__ import annotations

from typing import Any

"""
Data models for protocol audit operations.
"""


import logging
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from omnibase_core.errors.exceptions import (
    ExceptionConfiguration,
    ExceptionInputValidation,
)
from omnibase_core.validation.validation_utils import (
    ModelDuplicationInfo,
    ModelProtocolInfo,
    determine_repository_name,
    extract_protocols_from_directory,
    validate_directory_path,
)

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
