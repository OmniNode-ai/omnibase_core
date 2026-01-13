# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0

"""
Service Resolution Status Enum.

Defines status values for service resolution operations in DI containers.
"""

from enum import Enum

__all__ = ["EnumServiceResolutionStatus"]


class EnumServiceResolutionStatus(str, Enum):
    """Service resolution status values.

    Indicates the outcome of attempting to resolve a service
    from the dependency injection container.

    Values:
        RESOLVED: Service was successfully resolved.
        FAILED: Service resolution failed for an unspecified reason.
        CIRCULAR_DEPENDENCY: Resolution failed due to circular dependency.
        MISSING_DEPENDENCY: Resolution failed due to missing dependency.
        TYPE_MISMATCH: Resolution failed due to type incompatibility.
    """

    RESOLVED = "resolved"
    """Service was successfully resolved."""

    FAILED = "failed"
    """Service resolution failed for an unspecified reason."""

    CIRCULAR_DEPENDENCY = "circular_dependency"
    """Resolution failed due to circular dependency."""

    MISSING_DEPENDENCY = "missing_dependency"
    """Resolution failed due to missing dependency."""

    TYPE_MISMATCH = "type_mismatch"
    """Resolution failed due to type incompatibility."""
