"""
Data models for protocol duplication reports.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from omnibase_core.validation.validator_utils import (
    ModelDuplicationInfo,
    ModelProtocolInfo,
)

# Configure logger for this module
logger = logging.getLogger(__name__)


@dataclass
class ModelDuplicationReport:
    """Report of protocol duplications between repositories."""

    success: bool
    source_repository: str
    target_repository: str
    exact_duplicates: list[ModelDuplicationInfo]
    name_conflicts: list[ModelDuplicationInfo]
    migration_candidates: list[ModelProtocolInfo]
    recommendations: list[str]
