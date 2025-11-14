from __future__ import annotations

from typing import Any

"""
Data models for protocol duplication reports.
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
class ModelDuplicationReport:
    """Report of protocol duplications between repositories."""

    success: bool
    source_repository: str
    target_repository: str
    exact_duplicates: list[ModelDuplicationInfo]
    name_conflicts: list[ModelDuplicationInfo]
    migration_candidates: list[ModelProtocolInfo]
    recommendations: list[str]
