# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import UtilStrValueHelper


@unique
class EnumStampValidationType(UtilStrValueHelper, str, Enum):
    """Types of stamp validation operations."""

    CONTENT_INTEGRITY = "CONTENT_INTEGRITY"
    TIMESTAMP_VALIDATION = "TIMESTAMP_VALIDATION"
    FORMAT_VALIDATION = "FORMAT_VALIDATION"
    SIGNATURE_VERIFICATION = "SIGNATURE_VERIFICATION"
