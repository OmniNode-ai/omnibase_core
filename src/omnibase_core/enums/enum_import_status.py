# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Status enum for module import validation results.

Provides enumeration of possible import validation outcomes for circular
import detection and module dependency analysis.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumImportStatus(UtilStrValueHelper, str, Enum):
    """Status of a module import attempt."""

    SUCCESS = "success"
    CIRCULAR_IMPORT = "circular_import"
    IMPORT_ERROR = "import_error"
    UNEXPECTED_ERROR = "unexpected_error"
    SKIPPED = "skipped"


__all__ = ["EnumImportStatus"]
