# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""DB Boundary Enums.

Enums for DB boundary exception categories and statuses.
"""

from enum import Enum, unique


@unique
class EnumDbBoundaryReasonCategory(str, Enum):
    """Reason category for a DB boundary exception.

    Classifies why a cross-service database access is permitted:
    - READ_MODEL: Read-only access to another service's data (e.g., materialized view)
    - TEST_ONLY: Access limited to test fixtures and test helpers
    - BOOTSTRAP: One-time bootstrap or migration script
    - LEGACY_MIGRATION: Temporary access during a migration period
    """

    READ_MODEL = "READ_MODEL"
    """Read-only access to another service's data."""

    TEST_ONLY = "TEST_ONLY"
    """Access limited to test fixtures and test helpers."""

    BOOTSTRAP = "BOOTSTRAP"
    """One-time bootstrap or migration script."""

    LEGACY_MIGRATION = "LEGACY_MIGRATION"
    """Temporary access during a migration period."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value


@unique
class EnumDbBoundaryExceptionStatus(str, Enum):
    """Status of a DB boundary exception.

    Tracks the lifecycle of an approved exception:
    - APPROVED: Exception is active and valid
    - PENDING: Exception requested but not yet approved
    - EXPIRED: Review date has passed without renewal
    - REVOKED: Exception explicitly revoked
    """

    APPROVED = "APPROVED"
    """Exception is active and valid."""

    PENDING = "PENDING"
    """Exception requested but not yet approved."""

    EXPIRED = "EXPIRED"
    """Review date has passed without renewal."""

    REVOKED = "REVOKED"
    """Exception explicitly revoked."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value
