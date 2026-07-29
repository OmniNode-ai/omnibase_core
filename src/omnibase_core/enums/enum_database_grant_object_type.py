# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""PostgreSQL object types supported by explicit topology grants."""

from enum import StrEnum, unique

__all__ = ["EnumDatabaseGrantObjectType"]


@unique
class EnumDatabaseGrantObjectType(StrEnum):
    """Object scope for one explicit workload-principal grant."""

    DATABASE = "DATABASE"
    SCHEMA = "SCHEMA"
    TABLE = "TABLE"
    SEQUENCE = "SEQUENCE"
    FUNCTION = "FUNCTION"
    TYPE = "TYPE"
