"""
Schema Operation Enums.

Enumerations for schema operations and status.
"""

from enum import Enum


class EnumSchemaOperationType(str, Enum):
    """Types of schema operations."""

    validation = "validation"
    generation = "generation"
    evolution = "evolution"
    migration = "migration"
    analysis = "analysis"


class EnumSchemaStatus(str, Enum):
    """Status of schema operations."""

    success = "success"
    warning = "warning"
    error = "error"
    partial = "partial"
