# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Application-database schema domain classification."""

from enum import StrEnum, unique

__all__ = ["EnumDatabaseSchemaDomain"]


@unique
class EnumDatabaseSchemaDomain(StrEnum):
    """Authoritative security and tenancy domain for a database schema."""

    TENANT = "TENANT"
    OMNINODE_INTERNAL = "OMNINODE_INTERNAL"
    PLATFORM_CATALOG = "PLATFORM_CATALOG"
