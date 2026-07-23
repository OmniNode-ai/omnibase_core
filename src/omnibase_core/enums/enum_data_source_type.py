# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Data Source Type Enumeration for pipeline processing.

Defines the types of data sources that can be processed through
the metadata pipeline integration.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumDataSourceType(UtilStrValueHelper, str, Enum):
    """Types of data sources in the pipeline."""

    FILE_SYSTEM = "FILE_SYSTEM"
    DATABASE_RECORD = "DATABASE_RECORD"
    API_REQUEST = "API_REQUEST"
    SCHEDULED_JOB = "SCHEDULED_JOB"


__all__ = ["EnumDataSourceType"]
