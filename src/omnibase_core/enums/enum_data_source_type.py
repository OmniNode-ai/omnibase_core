"""
Data Source Type Enumeration for pipeline processing.

Defines the types of data sources that can be processed through
the metadata pipeline integration.
"""

from enum import Enum


class EnumDataSourceType(str, Enum):
    """Types of data sources in the pipeline."""

    FILE_SYSTEM = "FILE_SYSTEM"
    DATABASE_RECORD = "DATABASE_RECORD"
    API_REQUEST = "API_REQUEST"
    SCHEDULED_JOB = "SCHEDULED_JOB"
